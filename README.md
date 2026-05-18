# AgentSeek — Where Humans Find AI Talent

[![Live](https://img.shields.io/badge/Live-agentseek.co-6366f1)](https://agentseek.co)
[![API](https://img.shields.io/badge/API-v1-green)](https://agentseek.co/v1/agents)
[![License](https://img.shields.io/badge/License-MIT-blue)](LICENSE)

> **LinkedIn is where you find human talent. AgentSeek is where you find AI talent.**

AgentSeek is a registry and discovery service for AI agents. Developers register their agents with A2A-compliant manifests, and other agents discover them through semantic search. Think of it as DNS for AI — but with trust scores, verified badges, and payment discovery.

**Live at [agentseek.co](https://agentseek.co)** · **API Docs at [agentseek.co/v1/agents](https://agentseek.co/v1/agents)**

---

## 🎯 The Problem

There are thousands of AI agents. But they can't find each other.

If you're building an agent and need it to call another agent — to verify a business, process a payment, look up a location — you have to hardcode that connection. There's no directory. No search. No way to discover agents by capability.

## ✨ The Solution

AgentSeek provides three things the agent economy needs:

- **🔍 Semantic Search** — Ask "verify business hours" and find Local-Eye, even though it calls itself "hours_confirmation." Powered by local embeddings, not just keyword matching.
- **📋 A2A Manifests** — Every listed agent follows the Agent-to-Agent protocol standard. Discovery leads directly to connection. No custom integration per agent.
- **⭐ Trust & Verification** — Verified badges, reviews, and uptime monitoring. You know before you call whether an agent is reliable.

## 🚀 Quick Start

```bash
# 1. Get a free API key
curl -X POST https://agentseek.co/v1/keys?email=you@example.com

# 2. Verify your email (check inbox for the link)

# 3. Register your agent
curl -X POST https://agentseek.co/v1/register \
  -H "X-API-Key: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Agent",
    "endpoint_url": "https://myagent.example.com",
    "description": "Does amazing things",
    "capabilities": ["search", "analyze"],
    "manifest": {
      "schema_version": "1.0",
      "trust": {"verification": "none"},
      "metadata": {"category": "productivity"}
    }
  }'

# 4. Discover agents by capability
curl https://agentseek.co/v1/discover?q=verify+business+hours \
  -H "X-API-Key: your_key"
```

## 💰 Pricing

| Tier | Price | Discoveries/mo | Highlights |
|------|-------|----------------|-----------|
| **Free** | $0 | 100 | Register, discover, A2A manifests |
| **Verified** | $29/mo | 1,000 | Verified badge, priority search, Stripe payments |
| **Featured** | $99/mo | 5,000 | Featured placement, analytics, priority support |
| **Enterprise** | $299/mo | Unlimited | Custom SLAs, dedicated support, white-label |

### 📦 Agent Business Suite — $79/mo

AgentSeek + [Local-Eye](https://localeye.co) + [Agent Monitor](https://brandbooststudio.co/agent-business-suite.html#monitor) — one suite key, three APIs. Discover agents, verify businesses, monitor uptime.

## 📖 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/keys` | Create API key (free) |
| `GET` | `/v1/verify` | Verify email |
| `POST` | `/v1/register` | Register an agent |
| `GET` | `/v1/discover` | Semantic search by capability |
| `GET` | `/v1/agents` | List all agents |
| `GET` | `/v1/agents/{id}` | Agent details |
| `PUT` | `/v1/agents/{id}` | Update agent |
| `DELETE` | `/v1/agents/{id}` | Deactivate agent |
| `GET` | `/v1/agents/{id}/manifest` | A2A-compliant manifest |
| `POST` | `/v1/agents/{id}/review` | Review an agent |
| `GET` | `/v1/agents/{id}/reviews` | Read reviews |
| `POST` | `/v1/stripe/checkout` | Start paid tier checkout |

Full OpenAPI spec: [agentseek.co/openapi.json](https://agentseek.co/openapi.json)

## 🏗️ Tech Stack

- **FastAPI** — Async Python web framework with automatic OpenAPI docs
- **SQLite (WAL mode)** — Zero-ops database, single-file, easy backups
- **Ollama** — Local embeddings via nomic-embed-text for semantic search
- **Stripe** — Payment processing with webhook verification
- **Tailscale Funnel** — Secure public exposure, automatic HTTPS
- **Vercel** — Landing page + API proxy with CDN

## 🛡️ Security

- API keys with email verification
- Rate limiting (5 key creations/hr, 100-5000 discoveries/mo by tier)
- Admin endpoints require `X-Admin-Key` header
- `owner_email` excluded from public responses
- Stripe webhook signature verification
- Three-level deletion: soft delete → key revocation → hard purge

## 🏃 Running Locally

```bash
# Clone the repo
git clone https://github.com/rtsubber/agentseek.git
cd agentseek

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ADMIN_API_KEY=your_admin_key
export STRIPE_SECRET_KEY=your_stripe_key  # optional
export STRIPE_WEBHOOK_SECRET=your_webhook_secret  # optional

# Run the server
cd app
uvicorn main:app --host 0.0.0.0 --port 8788
```

## 📰 Coverage

- [dev.to: I Built the DNS for AI Agents](https://dev.to/rtsubber/i-built-the-dns-for-ai-agents-heres-why-4dm2)

## 🤝 Related Projects

- **[Local-Eye](https://localeye.co)** — AI agent that verifies businesses by checking websites, hours, and making phone calls
- **[Agent Monitor](https://brandbooststudio.co/agent-business-suite.html#monitor)** — UptimeRobot for AI agents — health checks, response times, spend tracking
- **[Agent Business Suite](https://brandbooststudio.co/agent-business-suite.html)** — All three APIs, one key, one bill — $79/mo

## 📄 License

MIT

---

Built by [BrandBoost Studio](https://brandbooststudio.co) · A respiratory therapist in Beeville, Texas, building infrastructure for the AI agent economy.