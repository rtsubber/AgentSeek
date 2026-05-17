## Add to: public-apis repository

### Category: Security
Or: Business (if security is full)

| Name | Description | Auth | HTTPS | CORS |
| --- | --- | --- | --- | --- |
| AgentSeek | AI agent directory with semantic discovery, A2A manifests, and trust scores | `X-API-Key` | Yes | Yes |

---

### Full PR body:

## AgentSeek

**Description:** AI agent directory with semantic discovery, A2A-compliant manifests, and trust scores.

- **Register** agents with capability manifests
- **Discover** agents by capability using semantic search (embeddings + keyword matching)
- **Trust** scores based on reviews, usage, and verification
- Free tier: 100 discoveries/month, no credit card required

**API Docs:** https://api.agentregistry.co/openapi.json
**Homepage:** https://agentregistry.co
**Open Source:** https://github.com/rtsubber/agent-registry

| Category | Auth | HTTPS | CORS |
| --- | --- | --- | --- |
| Security | `X-API-Key` | Yes | Yes |