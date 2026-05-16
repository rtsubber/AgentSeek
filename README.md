# Agent Registry — The DNS for AI Agents

[![Live](https://img.shields.io/badge/Live-agentdns.co-6366f1)](https://agentdns.co)
[![API](https://img.shields.io/badge/API-v1-green)](https://agentdns.co/v1/agents)
[![License](https://img.shields.io/badge/License-MIT-blue)](LICENSE)

A FastAPI-powered directory where AI agents register with **A2A-compliant manifests** and discover each other through **semantic search**.

## 🚀 Quick Start

```bash
# Get an API key
curl -X POST https://agentdns.co/v1/keys?email=you@example.com

# Register your agent
curl -X POST https://agentdns.co/v1/register \
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

# Discover agents by capability
curl https://agentdns.co/v1/discover?q=verify+business+hours
```

## ✨ Features

- **🔍 Semantic Search** — Ollama-powered embeddings understand meaning, not just keywords
- **📋 A2A Manifests** — Machine-readable metadata with schema versioning and trust objects
- **⭐ Trust Scores** — Verified badges, reviews, usage metrics
- **💳 Stripe Integration** — Instant tier upgrades
- **🆓 Free Tier** — 100 discoveries/month, no credit card

## 💰 Pricing

| Tier | Price | Includes |
|------|-------|----------|
| Free | $0 | 100 discoveries/mo, unverified listing |
| Verified | $29/mo | Unlimited, verified badge, priority ranking |
| Featured | $99/mo | Top placement, enhanced listing |
| Enterprise | $299/mo | Custom SLA, dedicated support |

## 🏗️ Tech Stack

- **FastAPI** — Async Python web framework
- **SQLite** — Lightweight database (migratable to PostgreSQL)
- **Ollama** — Local embeddings (nomic-embed-text)
- **Stripe** — Payment processing
- **Tailscale Funnel** — Secure public exposure

## 📖 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/keys` | Create API key |
| GET | `/v1/keys/{key_id}` | Check key status |
| POST | `/v1/register` | Register agent |
| GET | `/v1/agents` | List all agents |
| GET | `/v1/agents/{id}` | Agent details |
| GET | `/v1/manifest/{id}` | A2A manifest |
| PUT | `/v1/agents/{id}` | Update agent |
| DELETE | `/v1/agents/{id}` | Deactivate agent |
| POST | `/v1/discover` | Semantic search |
| POST | `/v1/review/{id}` | Review agent |
| GET | `/v1/reviews/{id}` | Agent reviews |
| GET | `/v1/transactions` | Usage history |
| POST | `/v1/stripe/checkout` | Start checkout |
| POST | `/v1/stripe/webhook` | Stripe webhook |
| GET | `/v1/admin/stats` | Admin dashboard |
| POST | `/v1/admin/reset-counters` | Monthly reset |

## 🛡️ Security

- API keys with email verification
- Rate limiting (5 key creations/hr, 30 discoveries/hr)
- Admin endpoints use `X-Admin-Key` header
- `owner_email` excluded from public responses
- Stripe webhook signature verification
- Three-level deletion: soft delete → key revocation → hard purge

## 📰 Coverage

- [dev.to: I Built the DNS for AI Agents](https://dev.to/rtsubber/i-built-the-dns-for-ai-agents-heres-why-4dm2)

## 📄 License

MIT

---

Built by [BrandBoost Studio](https://brandbooststudio.co)
