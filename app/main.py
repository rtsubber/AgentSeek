"""AgentSeek — Find AI Talent

A registry where developers register their agents with capability manifests,
and other agents discover them via semantic search.

Endpoints:
  POST /v1/register           — Register an agent with its manifest
  PUT  /v1/agents/{id}         — Update agent details
  DELETE /v1/agents/{id}       — Deactivate agent (soft delete)
  GET  /v1/discover           — Semantic + keyword search for agents
  GET  /v1/agents              — List all agents (with filters)
  GET  /v1/agents/{id}         — Get agent details
  GET  /v1/agents/{id}/manifest — A2A-compliant agent card
  POST /v1/agents/{id}/review  — Rate an agent
  GET  /v1/agents/{id}/reviews  — Get agent reviews
  GET  /v1/agents/{id}/transactions — Get agent transaction history
  POST /v1/keys                — Create API key (email verification)
  GET  /v1/verify               — Verify email + activate key
  GET  /v1/keys/{id}/status    — Check key status + usage
  POST /v1/stripe/checkout     — Create Stripe checkout session
  POST /v1/stripe/webhook      — Stripe webhook handler
  GET  /v1/admin/stats         — Admin dashboard stats
  POST /v1/admin/reset-counters — Reset old usage counters (cron)
"""
import asyncio
import sys
import os
import json
import re
import time
import httpx
import aiosqlite
import stripe
import hashlib
import hmac
import logging as _logging
_logger = _logging.getLogger(__name__)
from collections import defaultdict
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, Response
from seo_pages import router as seo_router, slugify, CATEGORY_META, render_agent_page, render_category_page, render_categories_index, _truncate, _trust_class
from claim_and_og import router as claim_og_router
from blog_pages import router as blog_router
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field, HttpUrl, EmailStr
from typing import Optional

from db import (
    init_db, register_agent, get_agent, list_agents, count_agents, update_agent_stats,
    create_api_key, validate_key, log_transaction, get_agent_transactions,
    add_review, get_stats, DB_PATH,
    increment_usage, get_usage, reset_monthly_usage,
    upsert_capabilities, search_capabilities,
    create_verification_token, verify_email_token,
)

# ---------------------------------------------------------------------------
# Config — all secrets MUST come from environment; no hardcoded fallbacks
# ---------------------------------------------------------------------------
def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable '{name}' is not set.")
    return value

def _trust_tier(score: float) -> str:
    """Convert numeric trust score to human-readable tier."""
    if score >= 90: return "verified"
    if score >= 70: return "trusted"
    if score >= 40: return "unproven"
    return "flagged"

ADMIN_API_KEY = _require_env("ADMIN_API_KEY")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
VERIFY_URL = os.getenv("VERIFY_URL", "https://agentseek.co/v1/verify")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@agentseek.co")
# [S9 FIX] External script path — move to env var, fail gracefully if unset
SHEETS_WEBHOOK_SCRIPT = os.getenv("SHEETS_WEBHOOK_SCRIPT", "")

# [S3 FIX] Trusted proxy configuration for IP-based rate limiting.
# When behind a trusted reverse proxy (Tailscale Funnel, Cloudflare, etc.),
# set TRUSTED_PROXY=true and the proxy's real-IP header name.
# When NOT behind a proxy, use request.client.host directly.
TRUSTED_PROXY = os.getenv("TRUSTED_PROXY", "false").lower() == "true"
TRUSTED_PROXY_HEADER = os.getenv("TRUSTED_PROXY_HEADER", "x-real-ip")


def _get_client_ip(request: Request) -> str:
    """Get the real client IP, respecting trusted proxy configuration.

    When TRUSTED_PROXY=true, we trust the proxy to set the correct IP header.
    When TRUSTED_PROXY=false (default), we ignore forwarded headers to prevent
    spoofing — an attacker can set X-Forwarded-For to anything."""
    if TRUSTED_PROXY:
        # Trust the configured header (e.g., X-Real-IP from Tailscale/Cloudflare)
        real_ip = request.headers.get(TRUSTED_PROXY_HEADER, "").strip()
        if real_ip:
            return real_ip
        # Fallback: take the LAST entry in X-Forwarded-For (set by our proxy)
        forwarded = request.headers.get("x-forwarded-for", "").strip()
        if forwarded:
            return forwarded.split(",")[-1].strip()
    # No trusted proxy — use direct connection IP only
    return request.client.host if request.client else "unknown"

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

TIER_LIMITS = {
    "free": {"discoveries_per_month": -1, "can_list": True, "verified": False},
    "verified": {"discoveries_per_month": -1, "can_list": True, "verified": True},
    "featured": {"discoveries_per_month": -1, "can_list": True, "verified": True},
    "enterprise": {"discoveries_per_month": -1, "can_list": True, "verified": True},
}

# Stripe price IDs for each tier
STRIPE_PRICES = {
    "verified": os.getenv("STRIPE_PRICE_VERIFIED", "price_1TXaL0HTQdr0mtHrzb0mCJjz"),    # $29/mo
    "featured": os.getenv("STRIPE_PRICE_FEATURED", "price_1TXaL6HTQdr0mtHrfyNBex8o"),     # $99/mo
    "enterprise": os.getenv("STRIPE_PRICE_ENTERPRISE", "price_1TXaLDHTQdr0mtHrvzvmeaTH"), # $299/mo
}

# ---------------------------------------------------------------------------
# Rate limiter for key creation (IP-based, resets each hour)
# [B4 FIX] Added eviction of stale IPs to prevent unbounded memory growth.
# Note: These are per-process and reset on restart. For multi-worker
# deployments, back these with the DB or a shared store.
# ---------------------------------------------------------------------------
_key_creation_counts: dict[str, list[float]] = defaultdict(list)
KEY_CREATION_LIMIT = 5
KEY_CREATION_WINDOW = 3600
_RATE_LIMITER_MAX_IPS = 10000  # Evict oldest IPs when dict exceeds this

def _check_key_creation_rate(ip: str) -> None:
    now = time.time()
    window_start = now - KEY_CREATION_WINDOW
    # [B4 FIX] Evict stale IPs periodically to prevent memory growth
    if len(_key_creation_counts) > _RATE_LIMITER_MAX_IPS:
        stale_ips = [k for k, v in _key_creation_counts.items() if not v or v[-1] < window_start]
        for k in stale_ips:
            del _key_creation_counts[k]
    calls = [t for t in _key_creation_counts[ip] if t > window_start]
    if len(calls) >= KEY_CREATION_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Too many key creation requests. Limit: {KEY_CREATION_LIMIT} per hour.",
        )
    calls.append(now)
    _key_creation_counts[ip] = calls

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class ManifestModel(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    version: str = Field(default="1.0")
    description: str = Field(..., min_length=10, max_length=2000)
    capabilities: list[str] = Field(..., min_length=1)
    endpoint_url: HttpUrl = Field(...)
    auth_method: str = Field(default="bearer")
    pricing: dict = Field(default_factory=dict)
    category: str = Field(default="general")
    tags: list[str] = Field(default_factory=list)
    owner_email: EmailStr = Field(...)
    owner_name: str | None = None
    website_url: str | None = None
    logo_url: str | None = None

class ReviewModel(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    review_text: str | None = None

class CheckoutRequest(BaseModel):
    tier: str = Field(..., pattern="^(verified|featured|enterprise)$")
    email: EmailStr = Field(...)

class AgentUpdateModel(BaseModel):
    name: str | None = None
    description: str | None = None
    endpoint_url: HttpUrl | None = None
    capabilities: list[str] | None = None
    category: str | None = None
    tags: list[str] | None = None
    owner_name: str | None = None
    website_url: str | None = None
    logo_url: str | None = None
    auth_method: str | None = None
    pricing_model: str | None = None
    pricing: dict | None = None

# IP-based rate limiter for unauthenticated discover
# [B4 FIX] Added eviction of stale IPs to prevent unbounded memory growth.
_discover_counts: dict[str, list[float]] = defaultdict(list)
DISCOVER_RATE_LIMIT = 30  # per hour for unauthenticated
DISCOVER_RATE_WINDOW = 3600

def _check_discover_rate(ip: str) -> None:
    now = time.time()
    window_start = now - DISCOVER_RATE_WINDOW
    # [B4 FIX] Evict stale IPs periodically to prevent memory growth
    if len(_discover_counts) > _RATE_LIMITER_MAX_IPS:
        stale_ips = [k for k, v in _discover_counts.items() if not v or v[-1] < window_start]
        for k in stale_ips:
            del _discover_counts[k]
    calls = [t for t in _discover_counts[ip] if t > window_start]
    if len(calls) >= DISCOVER_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Discovery rate limit reached. Sign up for a free API key for higher limits.",
        )
    calls.append(now)
    _discover_counts[ip] = calls

# ---------------------------------------------------------------------------
# Lifespan / seed
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    try:
        await seed_agents()
    except Exception as e:
        _logger.warning(f"Unexpected error: {e}")
    yield

app = FastAPI(
    title="AgentSeek",
    description="Where humans find AI talent. Register, discover, and connect AI agents with semantic search, trust scores, and verified badges.",
    version="1.0.0",
    docs_url="/docs" if os.getenv("DEBUG") else None,
    redoc_url="/redoc" if os.getenv("DEBUG") else None,
    lifespan=lifespan,
)

ALLOWED_ORIGINS = [
    "https://agentseek.co",
    "https://www.agentseek.co",
    "http://localhost:3000",
    "http://localhost:8787",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------
async def seed_agents():
    """Seed Local-Eye and BoostRank if they don't already exist."""
    seeds = [
        {
            "id": "agt_localeye_001",
            "name": "Local-Eye Business Verifier",
            "description": (
                "Verifies businesses via residential IP web fetching, GPU-rendered screenshots, "
                "and phone verification calls."
            ),
            "endpoint_url": "https://api.localeye.co/v1",
            "owner_email": "info@brandbooststudio.co",
            "category": "verification",
            "tags": "business_verification,phone_verification,web_scraping,screenshots,residential_proxy",
            "owner_name": "BrandBoost Studio",
            "website_url": "https://localeye.co",
            "logo_url": "https://localeye.co/og-image.png",
            "auth_method": "api_key",
            "pricing_model": "per_call",
            "pricing_details": json.dumps({"per_call": 0.015, "phone": 5.00, "screenshot": 0.10, "free_tier": "5/day"}),
            "manifest_json": {
                "name": "Local-Eye Business Verifier",
                "version": "1.0",
                "capabilities": [
                    "business_verification", "web_presence_verification",
                    "phone_verification", "hours_confirmation",
                    "visual_verification", "screenshot_capture",
                    "residential_ip_fetching",
                ],
                "pricing": {"per_call": 0.015, "phone_verification": 5.00, "screenshot": 0.10},
                "endpoint": "https://api.localeye.co/v1",
                "auth": "api_key",
            },
            "trust_score": 94,
            "success_rate": 0.97,
            "total_calls": 24,
        },
        {
            "id": "agt_boostrank_001",
            "name": "BoostRank SEO Analyzer",
            "description": (
                "Analyzes website SEO performance, checks meta tags, headings, schema markup, "
                "page speed, and provides actionable recommendations with scores."
            ),
            "endpoint_url": "https://boostrank.co/api/v1/audit",
            "owner_email": "info@brandbooststudio.co",
            "category": "tools",
            "tags": "seo,analysis,audit,web_performance,schema,meta_tags",
            "owner_name": "BrandBoost Studio",
            "website_url": "https://boostrank.co",
            "auth_method": "api_key",
            "pricing_model": "freemium",
            "pricing_details": json.dumps({"free": "5/month", "pro": 19, "business": 49, "agency": 99}),
            "manifest_json": {
                "name": "BoostRank SEO Analyzer",
                "version": "1.0",
                "capabilities": [
                    "seo_analysis", "meta_tag_checking", "schema_validation",
                    "heading_structure", "performance_scoring", "content_audit",
                ],
                "pricing": {"free": "5/month", "pro": "$19/mo"},
                "endpoint": "https://boostrank.co/api/v1/audit",
                "auth": "api_key",
            },
            "trust_score": 91,
            "success_rate": 0.98,
            "total_calls": 156,
        },
    ]

    for seed in seeds:
        existing = await get_agent(seed["id"])
        if existing:
            continue

        manifest = seed.pop("manifest_json")
        trust_score = seed.pop("trust_score")
        success_rate = seed.pop("success_rate")
        total_calls = seed.pop("total_calls")
        desired_id = seed.pop("id")

        result = await register_agent(manifest_json=manifest, **seed)
        new_id = result["agent_id"]

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """UPDATE agents
                   SET id = ?, verified = 1, trust_score = ?, success_rate = ?, total_calls = ?
                   WHERE id = ?""",
                (desired_id, trust_score, success_rate, total_calls, new_id),
            )
            await db.commit()

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
async def get_caller(key_id: str | None) -> dict | None:
    if not key_id:
        return None
    return await validate_key(key_id)

async def require_caller(key_id: str | None) -> dict:
    caller = await get_caller(key_id)
    if not caller:
        raise HTTPException(status_code=401, detail="Valid API key required.")
    return caller

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/v1/register")
async def register(manifest: ManifestModel, request: Request, x_api_key: str = Header(None)):
    """Register a new agent."""
    # [S1 FIX] Rate-limit unauthenticated registration to prevent key enumeration
    caller = await get_caller(x_api_key)
    if not caller:
        client_ip = _get_client_ip(request)
        _check_key_creation_rate(client_ip)

    issued_key = None
    verification_required = False
    existing_account = False

    if not caller:
        key_result = await create_api_key(email=manifest.owner_email, tier="free")

        if key_result.get("existing"):
            # [S1 FIX] Email already registered — do NOT return the existing key.
            # The caller must verify ownership via the /v1/keys endpoint.
            existing_account = True
            issued_key = None
            x_api_key = None
        else:
            x_api_key = key_result["key_id"]
            issued_key = x_api_key
            # [FIX 6] New keys from registration also require email verification
            token = await create_verification_token(key_result["key_id"], manifest.owner_email)
            verify_link = f"{VERIFY_URL}?token={token}"
            verification_required = True

    manifest_dict = manifest.model_dump()
    manifest_dict["endpoint_url"] = str(manifest.endpoint_url)

    pricing_model = (
        "per_call" if manifest.pricing.get("per_call") else
        "monthly" if manifest.pricing.get("monthly") else
        "free"
    )

    result = await register_agent(
        name=manifest.name,
        description=manifest.description,
        endpoint_url=str(manifest.endpoint_url),
        owner_email=manifest.owner_email,
        manifest_json=manifest_dict,
        category=manifest.category,
        tags=",".join(manifest.tags),
        owner_name=manifest.owner_name,
        website_url=manifest.website_url,
        logo_url=manifest.logo_url,
        auth_method=manifest.auth_method,
        pricing_model=pricing_model,
        pricing_details=json.dumps(manifest.pricing) if manifest.pricing else None,
    )

    # [B3 FIX] Only link key to agent if the key doesn't already have an agent.
    # This prevents registering a second agent from silently orphaning the first.
    if not result.get("existing") and x_api_key:
        async with aiosqlite.connect(DB_PATH) as db:
            # Check if key already has an agent linked
            async with db.execute(
                "SELECT agent_id FROM api_keys WHERE key_id = ?", (x_api_key,)
            ) as cur:
                existing_agent = await cur.fetchone()
            if existing_agent and existing_agent[0]:
                # Key already linked to an agent — don't overwrite
                # The user should use a different key or manage agents separately
                pass
            else:
                await db.execute(
                    "UPDATE api_keys SET agent_id = ? WHERE key_id = ? AND agent_id IS NULL",
                    (result["agent_id"], x_api_key),
                )
                await db.commit()

    # [FIX 7] Surface exceptions from capability indexing background task
    if manifest.capabilities:
        def _log_cap_exc(task):
            exc = task.exception()
            if exc:
                print(f"[upsert_capabilities] failed for {result['agent_id']}: {exc}")
        task = asyncio.create_task(
            upsert_capabilities(result["agent_id"], manifest.capabilities, OLLAMA_BASE_URL)
        )
        task.add_done_callback(_log_cap_exc)

    # Notify via Telegram on new registration
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": TELEGRAM_CHAT_ID,
                        "text": (
                            f"🆕 New agent registered: {manifest.name} ({result['agent_id']})\n"
                            f"Category: {manifest.category}\n"
                            f"Capabilities: {', '.join(manifest.capabilities[:5])}"
                        ),
                    },
                )
        except Exception as e:
            _logger.warning(f"Unexpected error: {e}")

    # Push to Google Sheets
    try:
        import subprocess
        # [S9 FIX] Use env-var path for sheets webhook, skip if not configured
        if SHEETS_WEBHOOK_SCRIPT:
            data = json.dumps({"email": manifest.owner_email, "key_id": x_api_key or '', "tier": "free", "ip": "", "agent_name": manifest.name})
            subprocess.Popen(
                ["python3", SHEETS_WEBHOOK_SCRIPT,
                 "agentseek_signup", data],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except Exception as e:
        print(f"[WARN] Sheets webhook failed: {e}")

    response = {
        "status": "registered",
        "agent_id": result["agent_id"],
        "name": manifest.name,
        "existing": result.get("existing", False),
        "manifest_url": f"/v1/agents/{result['agent_id']}/manifest",
    }

    # [S1 FIX] Only include api_key for NEW keys, never for existing accounts
    if issued_key:
        response["api_key"] = issued_key

    if existing_account:
        # [S1 FIX] Don't leak any key info for existing accounts
        response["message"] = "An account with this email already exists. Check your inbox for the verification link, or use /v1/keys to resend it."
    elif verification_required:
        response["verify_url"] = verify_link
        response["message"] = "Agent registered. Verify your email to activate your API key."

    return response

@app.get("/v1/discover")
async def discover(
    request: Request,
    q: str = Query(..., min_length=2),
    category: str = None,
    limit: int = Query(default=5, le=100),
    x_api_key: str = Header(None),
):
    """Semantic + keyword search for agents by capability."""

    # Enforce tier limits or rate-limit unauthenticated callers
    caller = await get_caller(x_api_key)
    if caller:
        tier = caller.get("tier", "free")
        limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
        max_discoveries = limits["discoveries_per_month"]
        if max_discoveries != -1:
            usage = await get_usage(caller["key_id"], "discoveries")
            if usage >= max_discoveries:
                raise HTTPException(
                    status_code=402,
                    detail=(
                        f"Discovery limit reached ({max_discoveries}/month for {tier} tier). "
                        "Upgrade at https://agentseek.co/pricing"
                    ),
                    headers={"X-Upgrade-URL": "https://agentseek.co/pricing"},
                )
            await increment_usage(caller["key_id"], "discoveries")
    else:
        client_ip = _get_client_ip(request)
        _check_discover_rate(client_ip)

    # Show all agents in discovery (verified ranked higher, but listed agents visible too)
    agents = await list_agents(category=category, limit=100)
    used_fallback = False

    if not agents:
        return {"query": q, "results": [], "total": 0, "fallback": False}

    agent_map = {a["id"]: a for a in agents}
    scores: dict[str, dict] = {}  # agent_id → result dict

    # --- Path 1: Semantic capability search (via Ollama embeddings) ---
    try:
        cap_results = await search_capabilities(q, limit=20)
        for cr in cap_results:
            aid = cr["agent_id"]
            if aid not in agent_map:
                continue
            a = agent_map[aid]
            if category and a.get("category") != category:
                continue
            # Normalize cosine similarity (0.0–1.0) → 0–100
            semantic_score = int(min(cr["match_score"], 1.0) * 90)
            if a.get("verified"):
                semantic_score = min(100, semantic_score + 10)
            if aid not in scores or semantic_score > scores[aid]["match_score"]:
                scores[aid] = {
                    "agent_id": aid,
                    "name": a["name"],
                    "description": a["description"][:200],
                    "match_score": semantic_score,
                    "why": f"Capability match: {cr['capability']}",
                    "endpoint_url": a["endpoint_url"],
                    "category": a["category"],
                    "trust_score": a.get("trust_score", 0),
                    "trust_tier": _trust_tier(a.get("trust_score", 0)),
                    "verified": a.get("verified", 0),
                    "auth_method": a.get("auth_method", "bearer"),
                    "last_check": a.get("last_health_check"),
                    "success_rate": a.get("success_rate", 0),
                    "total_calls": a.get("total_calls", 0),
                    "endpoint_status": "dead" if a.get("trust_score", 0) < 20 else ("degraded" if a.get("trust_score", 0) < 50 else "healthy"),
                    "manifest_url": f"/v1/agents/{aid}/manifest",
                    "match_type": "semantic",
                    "logo_url": a.get("logo_url"),
                    "website_url": a.get("website_url"),
                }
    except Exception as e:
        _logger.warning(f"Unexpected error: {e}")  # Fall through to keyword matching

    # --- Path 2: Keyword matching (always runs, fills gaps) ---
    q_lower = q.lower()
    for a in agents:
        aid = a["id"]
        caps_list = a.get("manifest_json", {}).get("capabilities", [])
        caps_text = " ".join(c.replace("_", " ") for c in caps_list).lower()
        tags_list = a.get("tags", "").split(",") if a.get("tags") else []
        searchable = (
            f"{a['name']} {a['description']} {' '.join(tags_list)} {caps_text}".lower()
        )

        kw_score = 0
        for word in q_lower.split():
            if len(word) < 3:
                continue
            if word in searchable:
                kw_score += 25
            elif any(w.startswith(word[:4]) for w in searchable.split() if len(w) >= 4):
                kw_score += 20
            if word in caps_text:
                kw_score += 15

        if a.get("verified"):
            kw_score = min(100, kw_score + 10)

        if kw_score > 0:
            # Only override semantic result if keyword score is higher
            if aid not in scores or kw_score > scores[aid]["match_score"]:
                scores[aid] = {
                    "agent_id": aid,
                    "name": a["name"],
                    "description": a["description"][:200],
                    "match_score": min(kw_score, 100),
                    "why": f"Matches: {q}",
                    "endpoint_url": a["endpoint_url"],
                    "category": a["category"],
                    "trust_score": a.get("trust_score", 0),
                    "trust_tier": _trust_tier(a.get("trust_score", 0)),
                    "verified": a.get("verified", 0),
                    "auth_method": a.get("auth_method", "bearer"),
                    "last_check": a.get("last_health_check"),
                    "success_rate": a.get("success_rate", 0),
                    "total_calls": a.get("total_calls", 0),
                    "endpoint_status": "dead" if a.get("trust_score", 0) < 20 else ("degraded" if a.get("trust_score", 0) < 50 else "healthy"),
                    "manifest_url": f"/v1/agents/{aid}/manifest",
                    "match_type": "keyword",
                    "logo_url": a.get("logo_url"),
                    "website_url": a.get("website_url"),
                }

    results = sorted(scores.values(), key=lambda x: x["match_score"], reverse=True)

    # --- Optional LLM reranking of top 5 (best-effort, 3 s timeout) ---
    if results:
        try:
            top_ids = [r["agent_id"] for r in results[:5]]
            agent_lines = []
            for aid in top_ids:
                a = agent_map[aid]
                caps = a.get("manifest_json", {}).get("capabilities", [])
                agent_lines.append(
                    f"- {a['name']} (ID: {a['id']}): {a['description']}. "
                    f"Capabilities: {', '.join(caps)}"
                )
            prompt = (
                f'An AI agent needs: "{q}". Top matches:\n'
                + "\n".join(agent_lines)
                + '\n\nReturn JSON array: [{"agent_id":"...","match_score":0-100,"why":"one sentence"}]'
            )
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": "mistral:7b",
                        "prompt": prompt,
                        "stream": False,
                        "options": {"num_predict": 300},
                    },
                )
                if resp.status_code == 200:
                    text = resp.json().get("response", "")
                    json_match = re.search(r"\[.*\]", text, re.DOTALL)
                    if json_match:
                        llm_matches = json.loads(json_match.group())
                        llm_map = {m["agent_id"]: m for m in llm_matches if m.get("why")}
                        for r in results:
                            if r["agent_id"] in llm_map:
                                r["why"] = llm_map[r["agent_id"]]["why"]
        except Exception as e:
            _logger.warning(f"Unexpected error: {e}")

    # [B7 FIX] Return the full count before slicing, not the page size
    return {
        "query": q,
        "results": results[:limit],
        "total": len(results),
        "fallback": used_fallback,
    }

@app.get("/v1/agents")
async def list_all_agents(category: str = None, verified: bool = None, limit: int = 50, offset: int = 0):
    v = None if verified is None else (1 if verified else 0)
    agents = await list_agents(category=category, verified=v, limit=limit, offset=offset)
    results = [
        {
            "agent_id": a["id"],
            "name": a["name"],
            "description": a["description"][:200],
            "endpoint_url": a["endpoint_url"],
            "category": a["category"],
            "trust_score": a.get("trust_score", 0),
            "trust_tier": _trust_tier(a.get("trust_score", 0)),
            "verified": a.get("verified", 0),
            "auth_method": a.get("auth_method", "bearer"),
            "last_check": a.get("last_health_check"),
            "success_rate": a.get("success_rate", 0),
            "total_calls": a.get("total_calls", 0),
            "endpoint_status": "dead" if a.get("trust_score", 0) < 20 else ("degraded" if a.get("trust_score", 0) < 50 else "healthy"),
            "manifest_url": f"/v1/agents/{a['id']}/manifest",
            "logo_url": a.get("logo_url"),
            "pricing_model": a.get("pricing_model"),
        }
        for a in agents
    ]
    # [B7 FIX] Return the total count of ALL matching agents, not just the page
    return {"agents": results, "total": await count_agents(category, verified)}

@app.get("/v1/agents/{agent_id}")
async def get_agent_details(agent_id: str):
    agent = await get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {
        "agent_id": agent["id"],
        "name": agent["name"],
        "description": agent["description"],
        "endpoint_url": agent["endpoint_url"],
        "category": agent["category"],
        "tags": agent.get("tags", "").split(",") if agent.get("tags") else [],
        "trust_score": agent.get("trust_score", 0),
        "verified": agent.get("verified", 0),
        "total_calls": agent.get("total_calls", 0),
        "success_rate": agent.get("success_rate", 0),
        "auth_method": agent.get("auth_method", "bearer"),
        "pricing_model": agent.get("pricing_model", "per_call"),
        "pricing_details": agent.get("pricing_details", {}),
        "owner_name": agent.get("owner_name"),
        "website_url": agent.get("website_url"),
        "logo_url": agent.get("logo_url"),
        "created_at": agent.get("created_at"),
        "manifest_url": f"/v1/agents/{agent_id}/manifest",
    }

@app.put("/v1/agents/{agent_id}")
async def update_agent(
    agent_id: str,
    update: AgentUpdateModel,
    x_api_key: str = Header(None),
    x_admin_key: str = Header(None),
):
    """Update an existing agent. Requires owner key or X-Admin-Key."""
    # Admin can bypass API key requirement
    is_admin = hmac.compare_digest(x_admin_key or "", ADMIN_API_KEY)
    caller = await get_caller(x_api_key)
    if not caller and not is_admin:
        raise HTTPException(status_code=401, detail="Valid API key or admin key required.")

    agent = await get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if caller and caller.get("agent_id") != agent_id and not is_admin:
        raise HTTPException(status_code=403, detail="You can only update your own agent.")

    updates = {}
    if update.name is not None:
        updates["name"] = update.name
    if update.description is not None:
        updates["description"] = update.description
    if update.endpoint_url is not None:
        updates["endpoint_url"] = str(update.endpoint_url)
    if update.category is not None:
        updates["category"] = update.category
    if update.tags is not None:
        updates["tags"] = ",".join(update.tags)
    if update.owner_name is not None:
        updates["owner_name"] = update.owner_name
    if update.website_url is not None:
        updates["website_url"] = update.website_url
    if update.logo_url is not None:
        updates["logo_url"] = update.logo_url
    if update.auth_method is not None:
        updates["auth_method"] = update.auth_method
    if update.pricing_model is not None:
        updates["pricing_model"] = update.pricing_model

    # [FIX 1] Apply ALL manifest mutations first, then serialize ONCE
    manifest = agent.get("manifest_json", {})
    manifest_dirty = False
    if update.capabilities is not None:
        manifest["capabilities"] = update.capabilities
        manifest_dirty = True
    if update.pricing is not None:
        manifest["pricing"] = update.pricing
        manifest_dirty = True
    if update.name is not None:
        manifest["name"] = update.name
        manifest_dirty = True
    if update.description is not None:
        manifest["description"] = update.description
        manifest_dirty = True
    if update.endpoint_url is not None:
        manifest["endpoint"] = str(update.endpoint_url)
        manifest_dirty = True
    if manifest_dirty:
        updates["manifest_json"] = json.dumps(manifest)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates["updated_at"] = time.time()

    async with aiosqlite.connect(DB_PATH) as db:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [agent_id]
        await db.execute(f"UPDATE agents SET {set_clause} WHERE id = ?", values)
        await db.commit()

    # Re-generate capability embeddings after manifest is saved
    if update.capabilities is not None:
        def _log_exc(task):
            exc = task.exception()
            if exc:
                print(f"[upsert_capabilities] background task failed: {exc}")
        task = asyncio.create_task(
            upsert_capabilities(agent_id, update.capabilities, OLLAMA_BASE_URL)
        )
        task.add_done_callback(_log_exc)

    updated_agent = await get_agent(agent_id)
    return {
        "status": "updated",
        "agent_id": agent_id,
        "name": updated_agent["name"],
        "updated_fields": [k for k in updates if k != "updated_at"],
    }

@app.delete("/v1/agents/{agent_id}")
async def deactivate_agent(
    agent_id: str,
    x_api_key: str = Header(None),
    x_admin_key: str = Header(None),
):
    """Deactivate (soft-delete) an agent. Requires owner key or X-Admin-Key."""
    # Admin can bypass API key requirement
    is_admin = hmac.compare_digest(x_admin_key or "", ADMIN_API_KEY)
    caller = await get_caller(x_api_key)
    if not caller and not is_admin:
        raise HTTPException(status_code=401, detail="Valid API key or admin key required.")

    agent = await get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if caller and caller.get("agent_id") != agent_id and not is_admin:
        raise HTTPException(status_code=403, detail="You can only deactivate your own agent.")

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE agents SET active = 0, updated_at = ? WHERE id = ?",
            (time.time(), agent_id),
        )
        await db.execute(
            "UPDATE api_keys SET active = 0 WHERE agent_id = ?",
            (agent_id,),
        )
        await db.commit()

    return {"status": "deactivated", "agent_id": agent_id}

@app.get("/v1/agents/{agent_id}/manifest")
async def get_agent_manifest(agent_id: str):
    """A2A-compliant agent card."""
    agent = await get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    manifest = agent.get("manifest_json", {})
    return {
        "schema_version": "1.0",
        "name": manifest.get("name", agent["name"]),
        "version": manifest.get("version", "1.0"),
        "description": manifest.get("description", agent["description"]),
        "capabilities": manifest.get("capabilities", []),
        "endpoint": manifest.get("endpoint", agent["endpoint_url"]),
        "auth": manifest.get("auth", agent.get("auth_method", "bearer")),
        "pricing": manifest.get("pricing", {}),
        "trust": {
            "score": agent.get("trust_score", 0),
            "total_calls": agent.get("total_calls", 0),
            "success_rate": agent.get("success_rate", 0),
            "verified": agent.get("verified", 0) >= 1,
        },
        "metadata": {
            "category": agent.get("category", "general"),
            "tags": agent.get("tags", "").split(",") if agent.get("tags") else [],
            "owner": agent.get("owner_name", ""),
            "website": agent.get("website_url", ""),
            "logo": agent.get("logo_url", ""),
        },
    }

@app.post("/v1/agents/{agent_id}/review")
async def review_agent(agent_id: str, review: ReviewModel, x_api_key: str = Header(None)):
    caller = await require_caller(x_api_key)

    agent = await get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # [S4 FIX] Prevent self-review — agent owners can't review their own agent
    if caller.get("agent_id") == agent_id:
        raise HTTPException(status_code=403, detail="You cannot review your own agent.")

    try:
        result = await add_review(
            agent_id=agent_id,
            reviewer_key_id=x_api_key,
            rating=review.rating,
            review_text=review.review_text,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return result

@app.get("/v1/agents/{agent_id}/reviews")
async def list_reviews(agent_id: str, limit: int = 20, offset: int = 0):
    """Get reviews for an agent. Public endpoint — no auth required."""
    agent = await get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, rating, review_text, created_at FROM reviews WHERE agent_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (agent_id, limit, offset),
        ) as cursor:
            rows = await cursor.fetchall()
        async with db.execute("SELECT COUNT(*) FROM reviews WHERE agent_id = ?", (agent_id,)) as cursor:
            total = (await cursor.fetchone())[0]
        async with db.execute("SELECT AVG(rating) FROM reviews WHERE agent_id = ?", (agent_id,)) as cursor:
            avg = (await cursor.fetchone())[0]

    return {
        "agent_id": agent_id,
        "reviews": [
            {
                "id": r["id"],
                "rating": r["rating"],
                "review_text": r["review_text"],
                "created_at": r["created_at"],
            }
            for r in rows
        ],
        "total": total,
        "average_rating": round(avg, 2) if avg else None,
    }

@app.get("/v1/agents/{agent_id}/transactions")
async def agent_transactions(agent_id: str, x_api_key: str = Header(None), limit: int = 50):
    caller = await require_caller(x_api_key)

    agent = await get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # [S2 FIX] Only the real admin key or the agent owner can view transactions.
    # Enterprise tier is NOT admin — it's a customer tier, not a platform operator.
    caller_agent_id = caller.get("agent_id")
    is_admin = hmac.compare_digest(x_admin_key or "", ADMIN_API_KEY) if ADMIN_API_KEY else False
    if caller_agent_id != agent_id and not is_admin:
        raise HTTPException(status_code=403, detail="You may only view your own agent's transactions.")

    transactions = await get_agent_transactions(agent_id, limit=limit)
    return {"agent_id": agent_id, "transactions": transactions}

# ---------------------------------------------------------------------------
# Claim Listing — public endpoint, no auth required
# ---------------------------------------------------------------------------
# Claim listing — moved to claim_and_og.py
# ---------------------------------------------------------------------------


@app.post("/v1/keys")
async def create_key(request: Request, email: EmailStr = Query(...)):
    """Create a new API key. Key starts inactive until email is verified."""
    client_ip = _get_client_ip(request)
    _check_key_creation_rate(client_ip)
    result = await create_api_key(email=email, tier="free")

    if not result.get("existing"):
        # Key is new — create verification token (key starts inactive)
        token = await create_verification_token(result["key_id"], email)
        verify_link = f"{VERIFY_URL}?token={token}"

        # In production, send email via SMTP/SendGrid/etc.
        # For now, return the verify link directly (MVP)
        result["verify_url"] = verify_link
        result["message"] = "Key created. Click the verify link below to activate it."
    else:
        # [S1 FIX] Existing account — do NOT return key_id.
        # Tell the user to check their email or use the resend flow.
        result["message"] = "An API key already exists for this email. Check your inbox for the verification link, or contact support."
        result.pop("key_id", None)

    return result

@app.get("/v1/keys")
async def create_key_page(request: Request, email: str = Query(default="")):
    """Show API key creation page. If email provided, create key via POST."""
    html = """<!DOCTYPE html>
<html><head><title>AgentSeek — Get Your API Key</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:#0f1117; color:#e2e4ea; display:flex; align-items:center; justify-content:center; min-height:100vh; }
  .card { background:#1a1d27; border:1px solid #2a2d3a; border-radius:16px; padding:48px; max-width:480px; width:90%; text-align:center; }
  h1 { font-size:24px; margin-bottom:8px; color:#fff; }
  h1 span { color:#6366f1; }
  p { color:#8890a8; margin-bottom:24px; font-size:15px; line-height:1.5; }
  .key-box { background:#0f1117; border:1px solid #2a2d3a; border-radius:8px; padding:16px; font-family:monospace; font-size:14px; color:#22c55e; word-break:break-all; margin-bottom:16px; }
  .verify-link { color:#6366f1; word-break:break-all; }
  a { color:#6366f1; text-decoration:none; }
  a:hover { text-decoration:underline; }
  form { display:flex; gap:8px; margin-top:16px; }
  input[type=email] { flex:1; padding:12px 16px; border-radius:8px; border:1px solid #2a2d3a; background:#0f1117; color:#e2e4ea; font-size:14px; outline:none; }
  input[type=email]:focus { border-color:#6366f1; }
  button { padding:12px 24px; border-radius:8px; border:none; background:#6366f1; color:#fff; font-size:14px; font-weight:600; cursor:pointer; white-space:nowrap; }
  button:hover { background:#4f46e5; }
  button:disabled { opacity:0.5; cursor:not-allowed; }
  .back { margin-top:24px; font-size:13px; }
</style></head>
<body><div class="card">
  <h1>Agent<span>Seek</span></h1>
  <p>Get your free API key to start discovering and registering AI agents.</p>
  <form id="kf">
    <input type="email" id="em" placeholder="Enter your email" required>
    <button type="submit" id="btn">Get Key</button>
  </form>
  <div id="result"></div>
  <div class="back"><a href="https://agentseek.co">← Back to AgentSeek</a></div>
</div>
<script>
document.getElementById('kf').addEventListener('submit',async e=>{
  e.preventDefault();
  const em=document.getElementById('em').value.trim();
  if(!em)return;
  const b=document.getElementById('btn');
  b.textContent='Creating...';b.disabled=true;
  try{
    const r=await fetch('/v1/keys?email='+encodeURIComponent(em),{method:'POST'});
    const d=await r.json();
    document.getElementById('result').innerHTML=r.ok&&d.key_id?
      '<p style="color:#22c55e;margin-bottom:16px">✅ Key created! Copy it below:</p><div class="key-box">'+d.key_id+'</div>'+(d.verify_url?'<p style="margin-top:16px"><a href="'+d.verify_url+'" class="verify-link" style="font-size:16px;padding:8px 16px;border:1px solid #6366f1;border-radius:8px;display:inline-block">👉 Click here to verify your key</a></p>':''):
      '<p style="color:#ef4444">'+(d.detail||d.message||'Error creating key')+'</p>';
    b.textContent='✅ Key Created!';b.style.background='#22c55e';
  }catch(err){b.textContent='Error — try again';b.disabled=false;}
});
</script></body></html>"""
    return HTMLResponse(content=html)

@app.get("/v1/verify")
async def verify_email(token: str = Query(...)):
    """Verify an email address and activate the associated API key."""
    result = await verify_email_token(token)
    if not result:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    return {
        "status": "verified",
        "email": result["email"],
        "key_id": result["key_id"],
        "message": "Your API key is now active. You can start using the API.",
    }

@app.get("/v1/keys/{key_id}/status")
async def key_status(key_id: str):
    caller = await get_caller(key_id)
    if not caller:
        raise HTTPException(status_code=404, detail="Invalid API key")

    # Include monthly usage for the caller's tier
    tier = caller.get("tier", "free")
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    discoveries = await get_usage(key_id, "discoveries")

    return {
        "key_id": caller["key_id"],
        "email": caller["email"],
        "tier": tier,
        "agent_id": caller.get("agent_id"),
        "active": caller.get("active", 1),
        "usage": {
            "discoveries_this_month": discoveries,
            "discoveries_limit": limits["discoveries_per_month"],
        },
    }

@app.get("/v1/admin/stats")
async def admin_stats(x_admin_key: str = Header(None)):
    """Admin stats. Requires X-Admin-Key header."""
    if not hmac.compare_digest(x_admin_key or "", ADMIN_API_KEY):
        raise HTTPException(status_code=403, detail="Invalid admin key")
    return await get_stats()

@app.post("/v1/admin/reset-counters")
async def admin_reset_counters(x_admin_key: str = Header(None)):
    """Delete usage counters older than 2 months. Call via cron on the 1st."""
    if not hmac.compare_digest(x_admin_key or "", ADMIN_API_KEY):
        raise HTTPException(status_code=403, detail="Invalid admin key")
    await reset_monthly_usage()
    return {"status": "ok", "message": "Old usage counters purged"}

@app.delete("/v1/admin/keys/{key_id}")
async def admin_revoke_key(key_id: str, x_admin_key: str = Header(None)):
    """Revoke an API key. Admin only."""
    if not hmac.compare_digest(x_admin_key or "", ADMIN_API_KEY):
        raise HTTPException(status_code=403, detail="Invalid admin key")
    caller = await validate_key(key_id)
    if not caller:
        raise HTTPException(status_code=404, detail="Key not found")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE api_keys SET active = 0 WHERE key_id = ?", (key_id,))
        # Also deactivate the associated agent if any
        if caller.get("agent_id"):
            await db.execute("UPDATE agents SET active = 0 WHERE id = ?", (caller["agent_id"],))
        await db.commit()
    return {"status": "revoked", "key_id": key_id, "agent_id": caller.get("agent_id")}

@app.delete("/v1/admin/agents/{agent_id}")
async def admin_purge_agent(agent_id: str, x_admin_key: str = Header(None)):
    """Permanently delete an agent and all associated data. Admin only."""
    if not hmac.compare_digest(x_admin_key or "", ADMIN_API_KEY):
        raise HTTPException(status_code=403, detail="Invalid admin key")
    agent = await get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM capabilities WHERE agent_id = ?", (agent_id,))
        await db.execute("DELETE FROM reviews WHERE agent_id = ?", (agent_id,))
        await db.execute("DELETE FROM transactions WHERE callee_agent_id = ? OR caller_agent_id = ?", (agent_id, agent_id))
        await db.execute("UPDATE api_keys SET active = 0 WHERE agent_id = ?", (agent_id,))
        await db.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
        await db.commit()
    return {"status": "purged", "agent_id": agent_id, "name": agent["name"]}

# ---------------------------------------------------------------------------
# Stripe integration
# ---------------------------------------------------------------------------

@app.post("/v1/stripe/checkout")
async def create_checkout(request: CheckoutRequest, x_api_key: str = Header(None)):
    """Create a Stripe Checkout session to upgrade a key's tier."""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=501, detail="Stripe is not configured on this server.")

    caller = await require_caller(x_api_key)
    price_id = STRIPE_PRICES.get(request.tier)
    if not price_id:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {request.tier}. Valid tiers: verified, featured, enterprise")

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer_email=request.email,
            line_items=[{"price": price_id, "quantity": 1}],
            metadata={
                "registry_key_id": caller["key_id"],
                "registry_tier": request.tier,
                "registry_email": request.email,
            },
            success_url="https://agentseek.co/dashboard?upgraded=true",
            cancel_url="https://agentseek.co/pricing?canceled=true",
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=502, detail=f"Stripe error: {str(e)}")

@app.post("/v1/stripe/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events for subscription upgrades/cancellations."""
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=501, detail="Webhook secret not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        key_id = session.get("metadata", {}).get("registry_key_id")
        tier = session.get("metadata", {}).get("registry_tier")
        customer_id = session.get("customer")

        if key_id and tier:
            # [B9 FIX] Enterprise tier should get highest verified level
            verified_level = {"enterprise": 3, "featured": 2, "verified": 1}.get(tier, 0)
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE api_keys SET tier = ?, stripe_customer_id = ? WHERE key_id = ?",
                    (tier, customer_id, key_id),
                )
                await db.execute(
                    "UPDATE agents SET verified = ? WHERE id = (SELECT agent_id FROM api_keys WHERE key_id = ?)",
                    (verified_level, key_id),
                )
                await db.commit()

            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                try:
                    async with httpx.AsyncClient(timeout=5) as client:
                        await client.post(
                            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                            json={
                                "chat_id": TELEGRAM_CHAT_ID,
                                "text": f"💰 Agent Registry: {tier} upgrade for key {key_id[:12]}...",
                            },
                        )
                except Exception as e:
                    _logger.warning(f"Unexpected error: {e}")

    elif event["type"] == "customer.subscription.deleted":
        # [FIX 3] Downgrade tier AND reset verified status
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE api_keys SET tier = 'free' WHERE stripe_customer_id = ?",
                (customer_id,),
            )
            # Reset verified status for agents owned by this customer's keys
            await db.execute(
                """UPDATE agents SET verified = 0
                   WHERE id IN (
                       SELECT agent_id FROM api_keys
                       WHERE stripe_customer_id = ? AND agent_id IS NOT NULL
                   )""",
                (customer_id,),
            )
            await db.commit()

        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    await client.post(
                        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                        json={
                            "chat_id": TELEGRAM_CHAT_ID,
                            "text": f"⚠️ Agent Registry: subscription cancelled for customer {customer_id}",
                        },
                    )
            except Exception as e:
                _logger.warning(f"Unexpected error: {e}")

    return {"status": "ok"}

app.include_router(seo_router)
app.include_router(claim_og_router)
app.include_router(blog_router)

# ---------------------------------------------------------------------------
# SEO Routes — Agent detail pages, category pages, sitemap
# ---------------------------------------------------------------------------

# Old seeded agent slugs that no longer exist — 301 redirect to homepage
# (These were removed when we cleaned the directory down to our 7 verified agents)
OLD_SLUGS_301 = {
    "langchain", "crewai", "autogpt", "babyagi", "microsoft-semantic-kernel",
    "bland-ai", "vapi-ai", "retell-ai",
    "perplexity-ai", "tavily-search-api", "exa-ai-search",
    "firecrawl", "bright-data", "apify",
    "notion-ai", "otterai", "gamma-ai",
    "jasper-ai", "mailchimp-ai", "hubspot-ai",
    "freshdesk-ai", "tidio-ai", "gorgias-ai", "kustomer-ai",
    "n8n", "activepieces", "bardeen-ai", "rewind-ai",
    "scrapeless", "oxylabs-ai",
    "wiz-ai-security", "snyk", "abnormal-security",
    "duolingo-ai", "coursera-ai", "quillbot-ai",
    "hired-ai", "greenhouse-ai", "pymetrics",
    "tableau-ai", "looker-ai", "mode-ai",
    "indeed-ai", "lever-ai", "pathrise",
    "redfin-ai", "zillow-ai", "housecanary",
    "trulioo", "onfido-by-entrust",
    "postman-ai", "vercel-ai", "supabase",
    "openai-realtime-api", "twilio-ai", "livekit",
    "google-gemini", "brave-search-api",
    "aida-health", "zocdoc-ai", "talkiatry-ai", "health-gorilla",
    "casetext-by-thomson-reuters", "legalrobot", "spellbook", "eve-by-cleo",
    "v0", "boltnew-by-stackblitz", "lovable-ex-gpt-engineer", "devin-by-cognition",
}

@app.get("/agents/{slug}")
async def agent_detail(slug: str, request: Request):
    """SEO-optimized agent detail page."""
    # 301 redirect old seeded agent slugs that no longer exist
    if slug in OLD_SLUGS_301:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/", status_code=301)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Try matching by slug (name-based)
        cursor = await db.execute("SELECT * FROM agents WHERE active = 1")
        all_agents = [dict(row) async for row in cursor]
    
    # Find agent by slug
    agent = None
    for a in all_agents:
        if slugify(a["name"]) == slug or a["id"] == slug:
            agent = a
            break
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Normalize trust_score to int for display
    if agent.get("trust_score"):
        agent["trust_score"] = int(float(agent["trust_score"]))
    for a in all_agents:
        if a.get("trust_score"):
            a["trust_score"] = int(float(a["trust_score"]))
    
    html = render_agent_page(agent, all_agents)
    return HTMLResponse(content=html, headers={"Cache-Control": "public, max-age=300, s-maxage=600"})


@app.get("/categories/{category}")
async def category_page(category: str):
    """SEO-optimized category page."""
    meta = CATEGORY_META.get(category)
    if not meta:
        raise HTTPException(status_code=404, detail="Category not found")
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM agents WHERE active = 1 AND category = ? ORDER BY trust_score DESC",
            (category,)
        )
        agents = [dict(row) async for row in cursor]
    
    # Normalize trust scores
    for a in agents:
        if a.get("trust_score"):
            a["trust_score"] = int(float(a["trust_score"]))
    
    # Don't 404 on empty categories - still show the page for SEO
    html = render_category_page(category, agents, meta)
    return HTMLResponse(content=html, headers={"Cache-Control": "public, max-age=300, s-maxage=600"})


@app.get("/categories")
@app.get("/categories/")
async def categories_index():
    """SEO-optimized categories listing page."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT category, COUNT(*) as count FROM agents WHERE active = 1 GROUP BY category ORDER BY count DESC"
        )
        cats = [(row["category"], row["count"]) async for row in cursor]
    
    categories_with_counts = [(cat, count, CATEGORY_META.get(cat, {"title": cat.replace("_"," ").title(), "desc": f"AI {cat.replace('_',' ').title()} agents.", "h1": f"AI {cat.replace('_',' ').title()}"})) for cat, count in cats]
    
    html = render_categories_index(categories_with_counts)
    return HTMLResponse(content=html, headers={"Cache-Control": "public, max-age=600, s-maxage=1800"})


@app.get("/sitemap.xml")
async def sitemap():
    """Generate sitemap.xml for SEO."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT id, name, category, updated_at FROM agents WHERE active = 1 ORDER BY trust_score DESC")
        agents = [dict(row) async for row in cursor]
    
    urls = []
    # Homepage
    urls.append(f"""  <url>\n    <loc>https://agentseek.co/</loc>\n    <lastmod>{now}</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>""")
    # Categories page
    urls.append(f"""  <url>\n    <loc>https://agentseek.co/categories</loc>\n    <lastmod>{now}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>0.9</priority>\n  </url>""")
    # Category pages
    for cat, meta in CATEGORY_META.items():
        urls.append(f"""  <url>\n    <loc>https://agentseek.co/categories/{cat}</loc>\n    <lastmod>{now}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>0.8</priority>\n  </url>""")
    # Agent pages
    for agent in agents:
        slug = slugify(agent["name"])
        lastmod = agent.get("updated_at", "") or now
        if lastmod and "T" in str(lastmod):
            lastmod = str(lastmod).split("T")[0]
        elif not lastmod:
            lastmod = now
        urls.append(f"""  <url>\n    <loc>https://agentseek.co/agents/{slug}</loc>\n    <lastmod>{lastmod}</lastmod>\n    <changefreq>monthly</changefreq>\n    <priority>0.7</priority>\n  </url>""")
    
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{chr(10).join(urls)}\n</urlset>"""
    return Response(content=xml, media_type="application/xml", headers={"Cache-Control": "public, max-age=3600"})


@app.get("/robots.txt")
async def robots():
    """Generate robots.txt for SEO."""
    txt = """User-agent: *
Allow: /
Allow: /agents/
Allow: /categories/
Allow: /sitemap.xml
Disallow: /v1/
Disallow: /.well-known/

Sitemap: https://agentseek.co/sitemap.xml
"""
    return Response(content=txt, media_type="text/plain")


@app.get("/agentseek2025indexkey")
async def indexnow_key():
    """IndexNow key verification file."""
    return Response(content="agentseek2025indexkey", media_type="text/plain")

@app.get("/.well-known/ai-plugin.json")
async def ai_plugin_manifest(request: Request):
    host = request.headers.get("host", os.getenv("DEFAULT_HOST", "agentseek.co"))
    scheme = "https" if "localhost" not in host else "http"
    return {
        "schema_version": "v1",
        "name_for_model": "Agent Registry",
        "name_for_human": "Agent Registry",
        "description_for_model": "Find and discover AI agents by capability. Register your own agent for others to discover.",
        "description_for_human": "The directory for AI agents. Find the right agent for any task.",
        "auth": {"type": "api_key", "key_name": "X-API-Key", "key_location": "header"},
        "api": {"type": "openapi", "url": f"{scheme}://{host}/openapi.json"},
        "logo_url": "https://agentseek.co/logo.png",
        "contact_email": "info@brandbooststudio.co",
        "legal_info_url": "https://agentseek.co/terms",
    }

# [S7 FIX] Gate openapi.json behind DEBUG — same as docs_url/redoc_url
if os.getenv("DEBUG"):
    @app.get("/openapi.json")
    async def openapi_spec():
        return app.openapi()

@app.get("/")
async def landing():
    return RedirectResponse(url="https://agentseek.co")