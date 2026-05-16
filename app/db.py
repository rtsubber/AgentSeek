"""Agent Registry — Database layer"""
import aiosqlite
import secrets
import time
import json
import re
import hashlib
from pathlib import Path

DB_PATH = Path(__file__).parent / "agent_registry.db"


async def init_db():
    schema_path = Path(__file__).parent / "schema.sql"
    async with aiosqlite.connect(DB_PATH) as db:
        with open(schema_path) as f:
            await db.executescript(f.read())
        await db.commit()


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

async def register_agent(
    name: str, description: str, endpoint_url: str,
    owner_email: str, manifest_json: dict,
    category: str = "general", tags: str = "",
    owner_name: str = None, website_url: str = None,
    logo_url: str = None, auth_method: str = "bearer",
    pricing_model: str = "per_call", pricing_details: str = None,
) -> dict:
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        # Check for existing agent by owner + endpoint (natural unique key)
        async with db.execute(
            "SELECT id FROM agents WHERE owner_email = ? AND endpoint_url = ? AND active = 1",
            (owner_email, endpoint_url),
        ) as cursor:
            existing_row = await cursor.fetchone()

        if existing_row:
            existing_id = existing_row[0]
            await db.execute(
                """UPDATE agents
                   SET name = ?, description = ?, manifest_json = ?,
                       category = ?, tags = ?, owner_name = ?,
                       website_url = ?, logo_url = ?, auth_method = ?,
                       pricing_model = ?, pricing_details = ?, updated_at = ?
                   WHERE id = ?""",
                (
                    name, description, json.dumps(manifest_json),
                    category, tags, owner_name,
                    website_url, logo_url, auth_method,
                    pricing_model, pricing_details, now,
                    existing_id,
                ),
            )
            await db.commit()
            return {"agent_id": existing_id, "name": name, "existing": True}

        # New agent
        agent_id = f"agt_{secrets.token_hex(8)}"
        await db.execute(
            """INSERT INTO agents
               (id, name, description, endpoint_url, owner_email, manifest_json,
                category, tags, auth_method, pricing_model, pricing_details,
                owner_name, website_url, logo_url, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                agent_id, name, description, endpoint_url, owner_email,
                json.dumps(manifest_json), category, tags, auth_method,
                pricing_model, pricing_details, owner_name, website_url, logo_url, now,
            ),
        )
        await db.commit()
        return {"agent_id": agent_id, "name": name, "existing": False}


async def get_agent(agent_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM agents WHERE id = ? AND active = 1", (agent_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                d = dict(row)
                d["manifest_json"] = (
                    json.loads(d["manifest_json"])
                    if isinstance(d["manifest_json"], str)
                    else d["manifest_json"]
                )
                if d.get("pricing_details") and isinstance(d["pricing_details"], str):
                    d["pricing_details"] = json.loads(d["pricing_details"])
                return d
    return None


async def list_agents(
    category: str = None,
    verified: int = None,
    limit: int = 50,
    offset: int = 0,
) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM agents WHERE active = 1"
        params = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if verified is not None:
            query += " AND verified >= ?"
            params.append(verified)
        query += " ORDER BY trust_score DESC, total_calls DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            results = []
            for row in rows:
                d = dict(row)
                d["manifest_json"] = (
                    json.loads(d["manifest_json"])
                    if isinstance(d["manifest_json"], str)
                    else d["manifest_json"]
                )
                if d.get("pricing_details") and isinstance(d["pricing_details"], str):
                    d["pricing_details"] = json.loads(d["pricing_details"])
                results.append(d)
            return results


async def update_agent_stats(
    agent_id: str,
    calls: int = None,
    success_rate: float = None,
    trust_score: float = None,
):
    async with aiosqlite.connect(DB_PATH) as db:
        updates = []
        params = []
        if calls is not None:
            updates.append("total_calls = total_calls + ?")
            params.append(calls)
        if success_rate is not None:
            updates.append("success_rate = ?")
            params.append(success_rate)
        if trust_score is not None:
            updates.append("trust_score = ?")
            params.append(trust_score)
        if updates:
            updates.append("updated_at = ?")
            params.append(time.time())
            params.append(agent_id)
            await db.execute(
                f"UPDATE agents SET {', '.join(updates)} WHERE id = ?", params
            )
            await db.commit()


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------

async def create_api_key(email: str, agent_id: str = None, tier: str = "free") -> dict:
    key_id = f"ar_{secrets.token_hex(16)}"
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT key_id, tier FROM api_keys WHERE email = ? AND active = 1", (email,)
        ) as cursor:
            existing = await cursor.fetchone()
            if existing:
                return {"key_id": existing[0], "email": email, "tier": existing[1], "existing": True}
        await db.execute(
            "INSERT INTO api_keys (key_id, agent_id, email, tier, created_at) VALUES (?, ?, ?, ?, ?)",
            (key_id, agent_id, email, tier, now),
        )
        await db.commit()
    return {"key_id": key_id, "email": email, "tier": tier}


async def validate_key(key_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM api_keys WHERE key_id = ? AND active = 1", (key_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


# ---------------------------------------------------------------------------
# Usage Counters (tier limit tracking)
# ---------------------------------------------------------------------------

async def increment_usage(key_id: str, counter_type: str, amount: int = 1):
    """Increment a usage counter for the current month."""
    month = time.strftime("%Y-%m")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO usage_counters (key_id, counter_type, month, count)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key_id, counter_type, month) DO UPDATE SET count = count + ?
        """, (key_id, counter_type, month, amount, amount))
        await db.commit()


async def get_usage(key_id: str, counter_type: str) -> int:
    """Get current month's usage count for a counter."""
    month = time.strftime("%Y-%m")
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT count FROM usage_counters WHERE key_id = ? AND counter_type = ? AND month = ?",
            (key_id, counter_type, month)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def reset_monthly_usage():
    """Delete counters older than 2 months. Called by cron."""
    two_months_ago = time.strftime("%Y-%m", time.localtime(time.time() - 60 * 86400 * 60))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM usage_counters WHERE month < ?", (two_months_ago,))
        await db.commit()


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

async def log_transaction(
    caller_agent_id: str, callee_agent_id: str,
    caller_key_id: str, amount_cents: int,
    status: str = "completed", metadata: dict = None,
) -> str:
    txn_id = f"txn_{secrets.token_hex(8)}"
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO transactions
               (id, caller_agent_id, callee_agent_id, caller_key_id,
                amount_cents, status, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (txn_id, caller_agent_id, callee_agent_id, caller_key_id,
             amount_cents, status,
             json.dumps(metadata) if metadata else None, now),
        )
        await db.commit()
    return txn_id


async def get_agent_transactions(agent_id: str, limit: int = 50) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM transactions
               WHERE callee_agent_id = ? OR caller_agent_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (agent_id, agent_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------

async def add_review(
    agent_id: str,
    reviewer_key_id: str,
    rating: int,
    review_text: str = None,
) -> dict:
    """
    Insert a review and recompute trust score in a single connection.
    Duplicate reviews from the same key are rejected by the UNIQUE constraint
    in the schema; callers should handle IntegrityError accordingly.
    """
    review_id = f"rev_{secrets.token_hex(8)}"
    now = time.time()

    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                """INSERT INTO reviews (id, agent_id, reviewer_key_id, rating, review_text, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (review_id, agent_id, reviewer_key_id, rating, review_text, now),
            )
        except aiosqlite.IntegrityError:
            raise ValueError("You have already reviewed this agent.")

        # Recompute trust score within the same connection
        async with db.execute(
            "SELECT AVG(rating) as avg_rating, COUNT(*) as cnt FROM reviews WHERE agent_id = ?",
            (agent_id,),
        ) as cursor:
            row = await cursor.fetchone()
            avg_rating = row[0] or 0
            review_count = row[1] or 0

        trust = min(100, (avg_rating * 15) + (min(review_count, 50) * 0.4))

        await db.execute(
            "UPDATE agents SET trust_score = ?, updated_at = ? WHERE id = ?",
            (trust, now, agent_id),
        )
        await db.commit()

    return {"review_id": review_id, "rating": rating, "trust_score": trust}


# ---------------------------------------------------------------------------
# Capabilities with embeddings
# ---------------------------------------------------------------------------

async def generate_embedding(
    text: str,
    ollama_base_url: str = "http://localhost:11434",
) -> list[float] | None:
    """Generate embedding via Ollama nomic-embed-text. Returns None on failure."""
    try:
        import httpx as _httpx
        async with _httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(
                f"{ollama_base_url}/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text},
            )
            if resp.status_code == 200:
                return resp.json().get("embedding")
    except Exception:
        pass
    return None


async def upsert_capabilities(
    agent_id: str,
    capabilities: list[str],
    ollama_base_url: str = "http://localhost:11434",
):
    """Upsert capability entries for an agent with embeddings."""
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM capabilities WHERE agent_id = ?", (agent_id,))

        for cap in capabilities:
            cap_slug = re.sub(r"[^a-z0-9]+", "_", cap.lower()).strip("_")

            embedding_vec = await generate_embedding(
                f"{agent_id}: {cap}",
                ollama_base_url=ollama_base_url,
            )
            if embedding_vec:
                embedding_blob = json.dumps(embedding_vec).encode("utf-8")
            else:
                embedding_blob = hashlib.sha256(
                    f"{agent_id}:{cap_slug}".encode()
                ).digest()

            await db.execute(
                """INSERT INTO capabilities
                   (agent_id, capability, capability_slug, embedding, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (agent_id, cap, cap_slug, embedding_blob, now),
            )
        await db.commit()


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


async def search_capabilities(query: str, limit: int = 10) -> list[dict]:
    """Search capabilities by semantic similarity (Ollama embeddings) with keyword fallback."""
    query_embedding = await generate_embedding(query)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        results = []
        async with db.execute(
            "SELECT c.*, a.name as agent_name, a.trust_score, a.verified "
            "FROM capabilities c JOIN agents a ON c.agent_id = a.id WHERE a.active = 1"
        ) as cursor:
            async for row in cursor:
                d = dict(row)
                score = 0.0

                # Try cosine similarity with real embeddings
                if query_embedding and d.get("embedding"):
                    try:
                        stored = json.loads(d["embedding"])
                        if isinstance(stored, list) and len(stored) > 10:
                            score = _cosine_similarity(query_embedding, stored)
                    except (json.JSONDecodeError, TypeError, ValueError):
                        pass

                # Keyword fallback (always adds to score)
                if score == 0:
                    query_words = query.lower().split()
                    cap_lower = d["capability"].lower()
                    slug_lower = d["capability_slug"].lower()
                    kw_score = sum(1 for w in query_words if w in cap_lower or w in slug_lower)
                    score = float(kw_score)

                if score > 0:
                    d["match_score"] = round(score, 4)
                    results.append(d)

        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results[:limit]


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

async def get_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM agents WHERE active = 1") as c:
            total_agents = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM agents WHERE verified >= 1 AND active = 1") as c:
            verified_agents = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM api_keys WHERE active = 1") as c:
            total_keys = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM transactions") as c:
            total_transactions = (await c.fetchone())[0]
        async with db.execute(
            "SELECT COALESCE(SUM(amount_cents), 0) FROM transactions WHERE status = 'completed'"
        ) as c:
            total_revenue_cents = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM reviews") as c:
            total_reviews = (await c.fetchone())[0]

    return {
        "total_agents": total_agents,
        "verified_agents": verified_agents,
        "total_api_keys": total_keys,
        "total_transactions": total_transactions,
        "total_revenue_cents": total_revenue_cents,
        "total_revenue_usd": total_revenue_cents / 100,
        "total_reviews": total_reviews,
    }


# ---------------------------------------------------------------------------
# Email Verification
# ---------------------------------------------------------------------------

async def create_verification_token(key_id: str, email: str) -> str:
    """Create an email verification token. Key starts inactive until verified."""
    token = secrets.token_hex(32)
    now = time.time()
    expires_at = now + 86400  # 24 hours
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO email_verifications (token, key_id, email, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
            (token, key_id, email, now, expires_at),
        )
        # Deactivate key until verified
        await db.execute("UPDATE api_keys SET active = 0 WHERE key_id = ?", (key_id,))
        await db.commit()
    return token


async def verify_email_token(token: str) -> dict | None:
    """Verify an email token and activate the key. Returns info dict or None."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM email_verifications WHERE token = ? AND verified = 0",
            (token,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            d = dict(row)

        now = time.time()
        if d["expires_at"] < now:
            return None  # Token expired

        # Activate the key and mark token as verified
        await db.execute("UPDATE api_keys SET active = 1 WHERE key_id = ?", (d["key_id"],))
        await db.execute("UPDATE email_verifications SET verified = 1 WHERE token = ?", (token,))
        await db.commit()

    return {"key_id": d["key_id"], "email": d["email"]}