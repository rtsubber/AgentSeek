# Claim form and OG image generation for AgentSeek

import io
import os
import re
import time
import json
import aiosqlite
from fastapi import APIRouter, Request, HTTPException, Header, Query
from fastapi.responses import HTMLResponse, Response, JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "agent_registry.db"))

router = APIRouter()


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    return slug.strip('-')


def render_claim_form(agent_id: str, agent_name: str, agent_category: str) -> str:
    """Render the claim listing form page."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claim {agent_name} — AgentSeek</title>
    <meta name="description" content="Claim ownership of the {agent_name} listing on AgentSeek. Prove you represent this agent and take control of your listing.">
    <meta name="robots" content="noindex">
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📡</text></svg>">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0a0a0f; color: #e4e4e7; line-height: 1.6; min-height: 100vh; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
        h1 {{ font-size: 28px; font-weight: 700; color: #fff; margin-bottom: 8px; }}
        .subtitle {{ color: #818cf8; font-size: 14px; margin-bottom: 32px; }}
        .agent-badge {{ display: inline-flex; align-items: center; gap: 8px; background: #18181b; border: 1px solid #27272a; border-radius: 8px; padding: 12px 16px; margin-bottom: 32px; }}
        .agent-badge span {{ font-weight: 500; }}
        .agent-cat {{ color: #71717a; font-size: 13px; }}
        .form-group {{ margin-bottom: 20px; }}
        label {{ display: block; font-size: 14px; font-weight: 500; color: #a1a1aa; margin-bottom: 6px; }}
        label .required {{ color: #ef4444; }}
        input, textarea, select {{ width: 100%; padding: 12px 16px; background: #18181b; border: 1px solid #27272a; border-radius: 8px; color: #e4e4e7; font-size: 15px; outline: none; transition: border-color 0.2s; }}
        input:focus, textarea:focus {{ border-color: #6366f1; }}
        input::placeholder, textarea::placeholder {{ color: #52525b; }}
        textarea {{ min-height: 80px; resize: vertical; }}
        .hint {{ font-size: 12px; color: #52525b; margin-top: 4px; }}
        .submit-btn {{ width: 100%; padding: 14px; background: #6366f1; color: #fff; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; transition: background 0.2s; margin-top: 8px; }}
        .submit-btn:hover {{ background: #4f46e5; }}
        .submit-btn:disabled {{ background: #27272a; color: #52525b; cursor: not-allowed; }}
        .success {{ display: none; text-align: center; padding: 40px 20px; }}
        .success h2 {{ font-size: 24px; color: #22c55e; margin-bottom: 8px; }}
        .success p {{ color: #a1a1aa; }}
        .back-link {{ display: inline-block; margin-top: 24px; color: #818cf8; text-decoration: none; }}
        .back-link:hover {{ text-decoration: underline; }}
        .error {{ display: none; background: #450a0a; border: 1px solid #7f1d1d; border-radius: 8px; padding: 12px 16px; color: #fca5a5; margin-bottom: 20px; }}
        footer {{ margin-top: 48px; padding-top: 24px; border-top: 1px solid #27272a; font-size: 13px; color: #52525b; text-align: center; }}
        footer a {{ color: #818cf8; text-decoration: none; }}
    </style>
</head>
<body>
    <div class="container">
        <nav style="font-size:13px;color:#71717a;margin-bottom:24px;">
            <a href="/" style="color:#818cf8;text-decoration:none;">AgentSeek</a> &rsaquo;
            <a href="/agents/{slugify(agent_name)}" style="color:#818cf8;text-decoration:none;">{agent_name}</a> &rsaquo;
            Claim
        </nav>

        <div id="claim-form">
            <h1>Claim This Listing</h1>
            <p class="subtitle">Prove you own or represent this agent to take control of the listing.</p>

            <div class="agent-badge">
                <span>📋 {agent_name}</span>
                <span class="agent-cat">{agent_category.replace('_', ' ').title()}</span>
            </div>

            <div class="error" id="error-msg"></div>

            <form id="claimForm" onsubmit="submitClaim(event)">
                <input type="hidden" name="agent_id" value="{agent_id}">

                <div class="form-group">
                    <label>Your Name <span class="required">*</span></label>
                    <input type="text" name="claimer_name" required placeholder="Jane Smith">
                </div>

                <div class="form-group">
                    <label>Email <span class="required">*</span></label>
                    <input type="email" name="claimer_email" required placeholder="jane@example.com">
                    <div class="hint">We'll use this to contact you about the claim.</div>
                </div>

                <div class="form-group">
                    <label>Your Website / Agent URL</label>
                    <input type="url" name="claimer_url" placeholder="https://your-agent.com">
                    <div class="hint">Link to your agent's website or documentation.</div>
                </div>

                <div class="form-group">
                    <label>Proof of Ownership</label>
                    <input type="url" name="proof_of_ownership" placeholder="https://your-agent.com/.well-known/agentseek.txt">
                    <div class="hint">A URL showing you own this agent (e.g., a page on the agent's domain, a GitHub repo, or a DNS TXT record).</div>
                </div>

                <div class="form-group">
                    <label>Note</label>
                    <textarea name="note" placeholder="Tell us why you should own this listing..."></textarea>
                </div>

                <button type="submit" class="submit-btn" id="submitBtn">Submit Claim</button>
            </form>
        </div>

        <div class="success" id="claim-success">
            <h2>✅ Claim Submitted!</h2>
            <p>We'll review your claim within 48 hours and email you with the result.</p>
            <p style="margin-top:12px;color:#71717a;font-size:14px;">Reference: <strong id="ref-id"></strong></p>
            <a href="/agents/{slugify(agent_name)}" class="back-link">← Back to {agent_name}</a>
        </div>

        <footer>
            <p>&copy; 2025 AgentSeek — <a href="/">Find AI Agents</a> · <a href="/categories">Browse Categories</a></p>
        </footer>
    </div>

    <script>
    async function submitClaim(e) {{
        e.preventDefault();
        const form = document.getElementById('claimForm');
        const btn = document.getElementById('submitBtn');
        const errorDiv = document.getElementById('error-msg');
        const data = new FormData(form);
        const body = Object.fromEntries(data.entries());

        btn.disabled = true;
        btn.textContent = 'Submitting...';
        errorDiv.style.display = 'none';

        try {{
            const res = await fetch('/v1/claim', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(body)
            }});
            const json = await res.json();

            if (res.ok) {{
                document.getElementById('claim-form').style.display = 'none';
                document.getElementById('claim-success').style.display = 'block';
                document.getElementById('ref-id').textContent = json.agent_id;
            }} else {{
                errorDiv.textContent = json.detail || 'Something went wrong. Please try again.';
                errorDiv.style.display = 'block';
                btn.disabled = false;
                btn.textContent = 'Submit Claim';
            }}
        }} catch (err) {{
            errorDiv.textContent = 'Network error. Please check your connection and try again.';
            errorDiv.style.display = 'block';
            btn.disabled = false;
            btn.textContent = 'Submit Claim';
        }}
    }}
    </script>
</body>
</html>"""


@router.get("/claim")
async def claim_form_page(agent_id: str = Query(..., description="Agent ID to claim")):
    """Render the claim listing form page."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT id, name, category FROM agents WHERE id = ? AND active = 1", (agent_id,))
        row = await cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")

    html = render_claim_form(row["id"], row["name"], row["category"])
    return HTMLResponse(content=html)


@router.get("/og-image/{slug}")
async def og_image(slug: str):
    """Generate a dynamic OG image for an agent using SVG."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM agents WHERE active = 1")
        all_agents = [dict(r) async for r in cursor]

    agent = None
    for a in all_agents:
        if slugify(a["name"]) == slug or a["id"] == slug:
            agent = a
            break

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    name = agent.get("name", "Unknown")
    desc = (agent.get("description", "") or "")[:100]
    category = agent.get("category", "").replace("_", " ").title()
    trust = agent.get("trust_score", 0)
    verified = agent.get("verified", 0)
    badge = "✓ Verified" if verified else "📋 Listed"
    badge_color = "#22c55e" if verified else "#818cf8"

    # SVG OG image (1200x630 for Twitter/Facebook)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0a0a0f"/>
      <stop offset="100%" style="stop-color:#1a1a2e"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="630" fill="url(#bg)"/>
  <rect x="60" y="60" width="1080" height="510" rx="16" fill="#18181b" stroke="#27272a" stroke-width="1"/>

  <!-- Badge -->
  <rect x="100" y="90" width="120" height="32" rx="6" fill="{badge_color}22"/>
  <text x="160" y="112" font-family="-apple-system,system-ui,sans-serif" font-size="14" fill="{badge_color}" text-anchor="middle">{badge}</text>

  <!-- Category -->
  <text x="240" y="112" font-family="-apple-system,system-ui,sans-serif" font-size="14" fill="#71717a">{category}</text>

  <!-- Trust Score -->
  <rect x="1000" y="90" width="100" height="32" rx="6" fill="#18181b"/>
  <text x="1050" y="112" font-family="-apple-system,system-ui,sans-serif" font-size="14" fill="#a1a1aa" text-anchor="middle">Trust: {trust}/100</text>

  <!-- Agent Name -->
  <text x="100" y="200" font-family="-apple-system,system-ui,sans-serif" font-size="48" font-weight="700" fill="#ffffff">{name}</text>

  <!-- Description -->
  <text x="100" y="280" font-family="-apple-system,system-ui,sans-serif" font-size="22" fill="#a1a1aa">{desc}</text>

  <!-- Bottom bar -->
  <rect x="60" y="510" width="1080" height="60" rx="0 0 16 16" fill="#0a0a0f"/>
  <text x="100" y="550" font-family="-apple-system,system-ui,sans-serif" font-size="20" font-weight="600" fill="#6366f1">📡 AgentSeek</text>
  <text x="340" y="550" font-family="-apple-system,system-ui,sans-serif" font-size="18" fill="#71717a">Find AI Agents · agentseek.co</text>
</svg>"""

    return Response(content=svg, media_type="image/svg+xml")


class ClaimModel(BaseModel):
    agent_id: str
    claimer_name: str
    claimer_email: EmailStr
    claimer_url: Optional[str] = None
    proof_of_ownership: Optional[str] = None
    note: Optional[str] = None


async def send_claim_notification(claim_data: dict, agent_name: str):
    """Send a Telegram notification when someone claims a listing."""
    import httpx
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return  # No Telegram configured, skip notification

    message = (
        f"📋 **New Agent Claim on AgentSeek**\n\n"
        f"**Agent:** {agent_name} (`{claim_data['agent_id']}`)\n"
        f"**Claimed by:** {claim_data['claimer_name']}\n"
        f"**Email:** {claim_data['claimer_email']}\n"
    )
    if claim_data.get('claimer_url'):
        message += f"**Their URL:** {claim_data['claimer_url']}\n"
    if claim_data.get('proof_of_ownership'):
        message += f"**Proof:** {claim_data['proof_of_ownership']}\n"
    if claim_data.get('note'):
        message += f"**Note:** {claim_data['note']}\n"
    message += f"\n🔗 View all claims: https://agentseek.co/v1/claims"

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"},
                timeout=10.0
            )
    except Exception:
        pass  # Don't fail the claim if Telegram is down


@router.post("/v1/claim")
async def claim_listing(claim: ClaimModel):
    """Submit a claim for an agent listing. No auth required."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Check agent exists
        cursor = await db.execute("SELECT id, name FROM agents WHERE id = ? AND active = 1", (claim.agent_id,))
        agent = await cursor.fetchone()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Check if already claimed (pending)
        cursor = await db.execute(
            "SELECT id FROM claims WHERE agent_id = ? AND status = 'pending'",
            (claim.agent_id,)
        )
        existing = await cursor.fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="A pending claim already exists for this agent.")

        now = time.time()
        await db.execute(
            """INSERT INTO claims (agent_id, claimer_name, claimer_email, claimer_url, proof_of_ownership, note, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)""",
            (claim.agent_id, claim.claimer_name, claim.claimer_email, claim.claimer_url,
             claim.proof_of_ownership, claim.note, now)
        )
        await db.commit()

    # Send Telegram notification
    await send_claim_notification(claim.dict(), agent[1])

    return {
        "status": "submitted",
        "message": "Claim submitted! We'll review it and get back to you within 48 hours.",
        "agent_id": claim.agent_id,
        "claimer_email": claim.claimer_email,
    }


@router.get("/v1/claims")
async def list_claims(x_admin_key: str = Header(None)):
    """List all claims. Admin only."""
    ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "")
    if not (ADMIN_API_KEY and hmac.compare_digest(x_admin_key or "", ADMIN_API_KEY)):
        raise HTTPException(status_code=403, detail="Admin key required")

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM claims ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return {"claims": [dict(r) for r in rows]}