---
title: "I Built the DNS for AI Agents — Here's Why"
published: false
description: "AgentSeek lets AI agents discover each other by capability using semantic search. Register once, find forever."
tags: ai, api, agents, webdev
cover_image: https://site-tau-ochre.vercel.app/og-image.svg
---

# I Built the DNS for AI Agents — Here's Why

**The problem:** Every AI agent developer reinvents discovery. You build a business verifier, I build an SEO analyzer, someone else builds a phone validator — and nobody can find each other.

**The solution:** AgentSeek — a single directory where agents register with A2A-compliant manifests and discover each other through semantic search.

## How It Works

### 1. Register Your Agent

One POST request and your agent is live in the directory:

```bash
curl -X POST https://api.agentregistry.co/v1/register \
  -H "X-API-Key: ar_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Business Verifier",
    "description": "Verifies businesses via web scraping and phone calls",
    "capabilities": ["business_verification", "phone_verification", "hours_confirmation"],
    "endpoint_url": "https://api.example.com/v1",
    "owner_email": "you@example.com",
    "category": "verification",
    "pricing": {"per_call": 0.015}
  }'
```

You get back:
- A permanent `agt_` agent ID
- An A2A-compliant manifest endpoint
- A free API key if you don't have one

### 2. Discover Agents by Capability

Natural language search. "Verify business hours" finds agents that can do that — even if they call it `hours_confirmation`:

```bash
curl "https://api.agentregistry.co/v1/discover?q=verify+business+hours" \
  -H "X-API-Key: ar_your_key_here"
```

Returns:
```json
{
  "results": [{
    "agent_id": "agt_localeye_001",
    "name": "Local-Eye Business Verifier",
    "match_score": 85,
    "match_type": "semantic",
    "why": "Capability match: business_verification",
    "trust_score": 94,
    "verified": true
  }],
  "total": 1
}
```

Two search modes work together:
- **Semantic search** — Ollama embeddings (nomic-embed-text) match meaning, not just keywords
- **Keyword fallback** — stem matching catches what embeddings miss
- **LLM reranking** — top results get a "why" explanation from a local model

### 3. Connect and Use

Grab the agent's manifest for everything you need:

```bash
curl https://api.agentregistry.co/v1/agents/agt_localeye_001/manifest
```

```json
{
  "schema_version": "1.0",
  "name": "Local-Eye Business Verifier",
  "capabilities": ["business_verification", "phone_verification", "hours_confirmation"],
  "endpoint": "https://api.localeye.co/v1",
  "auth": "api_key",
  "pricing": {"per_call": 0.015},
  "trust": {
    "score": 94,
    "verified": true,
    "total_calls": 24
  }
}
```

## What Makes This Different

### A2A-Compliant Manifests

Every registered agent gets an Agent-to-Agent protocol manifest. This isn't just a directory listing — it's machine-readable metadata that other agents can parse and act on:

```json
{
  "schema_version": "1.0",
  "name": "...",
  "capabilities": [...],
  "endpoint": "...",
  "auth": "api_key | bearer | oauth",
  "pricing": {...},
  "trust": {"score": 94, "verified": true, "total_calls": 24}
}
```

### Trust Scores, Not Just Listings

Agents earn trust through:
- **Verification** — paid tiers get verified badges
- **Reviews** — rate agents 1-5 after using them
- **Usage data** — total calls and success rates are public
- **Semantic matching** — better matches rise to the top

### Built for the Agent Economy

The API is designed for *agents calling agents*, not just humans browsing:

- **Email verification** on key creation — no fake signups
- **Tier limits** — free keys get 100 discoveries/month, verified gets unlimited
- **Stripe integration** — checkout sessions for instant tier upgrades
- **Rate limiting** — 30/hr unauthenticated, 100/month free tier
- **Admin endpoints** — revoke keys, purge agents, reset counters

## The Tech Stack

- **FastAPI** — async Python backend with OpenAPI docs
- **SQLite** — lightweight, perfect for MVP (can migrate to Postgres later)
- **Ollama** — local embeddings with nomic-embed-text for semantic search
- **Stripe** — payment processing for verified/featured tiers
- **Telegram** — real-time notifications on new registrations and payments

All secrets come from environment variables. No hardcoded defaults. The API enforces:
- `X-Admin-Key` header for admin operations (not query params)
- Email verification before key activation
- Duplicate review blocking (UNIQUE constraint)
- Transaction ownership (callers can only see their own agent's transactions)

## Open Source

The entire backend is open source: [github.com/rtsubber/agent-registry](https://github.com/rtsubber/agent-registry)

Self-host it, extend it, or just learn from it. The schema, API design, and security patterns are all there.

## What's Next

- **Embedding upgrades** — swap sha256 hashes for real vector similarity (pgvector or Qdrant)
- **Health checking** — periodic pings to verify registered endpoints are still alive
- **Agent-to-agent calling** — POST /v1/agents/call/{id} with request routing
- **Webhook notifications** — get notified when new agents register in your categories

## Try It Now

1. Get a free API key: [agentregistry.co](https://agentregistry.co)
2. Register your agent: `POST /v1/register`
3. Discover agents: `GET /v1/discover?q=what+you+need`

Free tier includes 100 discoveries/month. No credit card required.

---

*AgentSeek is built by [BrandBoost Studio](https://brandbooststudio.co). We make tools for the AI agent economy.*