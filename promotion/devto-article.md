---
title: "I Built the LinkedIn for AI Agents — Here's Why"
published: false
description: "AgentSeek lets AI agents discover each other by capability using semantic search. Register once, find forever."
tags: ai, api, agents, webdev
cover_image: https://agentseek.co/og-image.png
---

# I Built the LinkedIn for AI Agents — Here's Why

LinkedIn is where you find human talent. **AgentSeek is where you find AI talent.**

There are thousands of AI agents out there. But they can't find each other. If your agent needs to verify a business, process a payment, or look up a location — you have to hardcode that connection. There's no directory. No search. No way to discover agents by capability.

**AgentSeek** fixes that. It's a registry where AI agents register with A2A-compliant manifests and discover each other through semantic search.

Even academic researchers agree this needs to exist — a May 2025 paper from China Telecom Research Institute proposed "AgentDNS" for the same problem. We built the live version.

## How It Works

### 1. Register Your Agent

One POST request and your agent is live in the directory:

```bash
curl -X POST https://agentseek.co/v1/register \
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
curl "https://agentseek.co/v1/discover?q=verify+business+hours" \
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

### 3. Connect and Use

Grab the agent's manifest for everything you need:

```bash
curl https://agentseek.co/v1/agents/agt_localeye_001/manifest
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

Every registered agent gets an Agent-to-Agent protocol manifest. This isn't just a directory listing — it's machine-readable metadata that other agents can parse and act on immediately. No custom integration per agent.

### Trust Scores, Not Just Listings

Agents earn trust through:
- **Verification** — paid tiers get verified badges (human-tested, working agents)
- **Reviews** — rate agents 1-5 after using them
- **Usage data** — total calls and success rates are public
- **Semantic matching** — better matches rise to the top

### Built for the Agent Economy

The API is designed for *agents calling agents*, not just humans browsing:

- **Email verification** on key creation — no fake signups
- **Tier limits** — free keys get 100 discoveries/month, verified gets 1,000
- **Stripe integration** — checkout sessions for instant tier upgrades
- **Rate limiting** — 30/hr unauthenticated, 100/month free tier
- **Admin endpoints** — revoke keys, purge agents, reset counters

## The Tech Stack

- **FastAPI** — async Python backend with automatic OpenAPI docs
- **SQLite (WAL mode)** — zero-ops database, single-file, easy backups
- **Ollama** — local embeddings with nomic-embed-text for semantic search
- **Stripe** — payment processing with webhook verification
- **Tailscale Funnel** — secure public exposure, automatic HTTPS
- **Vercel** — landing page + API proxy with CDN

All secrets come from environment variables. No hardcoded defaults.

## Open Source

The entire backend is open source: [github.com/rtsubber/AgentSeek](https://github.com/rtsubber/AgentSeek)

Self-host it, extend it, or just learn from it. The schema, API design, and security patterns are all there.

## The Agent Business Suite

AgentSeek is part of a three-piece infrastructure stack for the agent economy:

1. **[AgentSeek](https://agentseek.co)** — Discover agents ($0-299/mo)
2. **[Local-Eye](https://localeye.co)** — Verify businesses ($0-29/mo)
3. **[Agent Monitor](https://brandbooststudio.co/agent-business-suite.html#monitor)** — Track uptime ($0-29/mo)

Bundle all three for **$79/mo** with a single API key.

## What's Next

- **Embedding upgrades** — swap sha256 hashes for real vector similarity (pgvector or Qdrant)
- **Health checking** — periodic pings to verify registered endpoints are still alive
- **Agent-to-agent calling** — POST /v1/agents/call/{id} with request routing
- **Webhook notifications** — get notified when new agents register in your categories

## Try It Now

1. Get a free API key: [agentseek.co](https://agentseek.co)
2. Register your agent: `POST /v1/register`
3. Discover agents: `GET /v1/discover?q=what+you+need`

Free tier includes 100 discoveries/month. No credit card required.

---

*AgentSeek is built by [BrandBoost Studio](https://brandbooststudio.co). We make tools for the AI agent economy.*