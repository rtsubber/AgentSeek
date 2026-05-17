# AgentSeek — Promotion Checklist

## ✅ Done
- [x] Landing page built and deployed (Vercel)
- [x] API backend complete (18 endpoints)
- [x] dev.to article written

## 📝 Ready to Submit (Need Ron)

### 1. Domain Setup
- [ ] Register agentregistry.co (Porkbun ~$12/yr)
- [ ] Point to Vercel: A record → 76.76.21.21, CNAME www → cname.vercel-dns.com
- [ ] Add domain in Vercel dashboard
- [ ] Update CORS origins in main.py to include agentregistry.co
- [ ] Update VERIFY_URL env var to https://api.agentregistry.co/v1/verify

### 2. Stripe Products
- [ ] Create 3 products in Stripe dashboard:
  - Verified: $29/mo (price ID → STRIPE_PRICE_VERIFIED env var)
  - Featured: $99/mo (price ID → STRIPE_PRICE_FEATURED env var)
  - Enterprise: $299/mo (price ID → STRIPE_PRICE_ENTERPRISE env var)
- [ ] Set up webhook: POST https://api.agentregistry.co/v1/stripe/webhook
- [ ] Events: checkout.session.completed, customer.subscription.deleted

### 3. dev.to Article
- [ ] Ron confirms email on dev.to (confirmation link sent)
- [ ] Publish at https://dev.to/rtsubber (4 tags max: ai, api, agents, webdev)
- [ ] Share on Twitter/LinkedIn after publishing

### 4. Manual Submissions (Browser Required)
- [ ] **Product Hunt** — https://producthunt.com/posts/new
  - Name: AgentSeek
  - Tagline: The DNS for AI Agents
  - Description: Register AI agents with A2A-compliant manifests. Discover them by capability with semantic search.
  - URL: https://agentregistry.co
  - Topics: Developer Tools, API, AI
  
- [ ] **theresanaiforthat.com** — https://theresanaiforthat.com/submit
  - Name: AgentSeek
  - URL: https://agentregistry.co
  - Description: AI agent directory with semantic search. Register your agents, discover others by capability.
  - Category: Developer Tools, API
  
- [ ] **RapidAPI** — https://rapidapi.com/provider/register
  - Provider: AgentSeek
  - API: AgentSeek API
  - OpenAPI spec: https://api.agentregistry.co/openapi.json
  
- [ ] **GitHub PR** — public-apis repo
  - Content in: /home/ron/.openclaw/workspace/agent-registry/promotion/github-pr.md
  - Need GitHub PAT from Ron to submit

### 5. Social Media Posts
- [ ] Facebook (Epic Trends Store + BrandBoost Studio)
- [ ] Twitter/X (@EpctrendsStore)
- [ ] LinkedIn (Ron's profile)
- [ ] Reddit (r/artificial, r/API, r/SideProject)

### 6. Directory Submissions
- [ ] aivalley.ai
- [ ] apis.guru
- [ ] DevHunt (devhunt.org)

## Social Media Copy

### Twitter/X (280 char)
🚀 Launching AgentSeek — the DNS for AI Agents.

Register your agents with A2A-compliant manifests. Discover them by capability with semantic search. Free tier = 100 discoveries/mo.

Try it: https://agentregistry.co

### Facebook
🚀 We just launched AgentSeek — the DNS for AI Agents!

If you're building AI agents, you know the discovery problem. Every developer reinvents how agents find each other. Not anymore.

AgentSeek is a single directory where:
✅ Register agents with A2A-compliant manifests
✅ Discover by capability using semantic search (not just keywords)
✅ Trust scores, reviews, and verification badges
✅ Free tier with 100 discoveries/month

Built on FastAPI + SQLite + Ollama embeddings. Open source.

Try it free: https://agentregistry.co

### LinkedIn
Excited to announce AgentSeek — the DNS for AI Agents.

The agent economy has a discovery problem. Thousands of AI agents are being built, but there's no central directory where they can find each other by capability.

AgentSeek solves this with:
• A2A-compliant manifests — machine-readable metadata for every agent
• Semantic search — find agents by meaning, not just exact keyword matches
• Trust infrastructure — verified badges, reviews, usage stats
• Simple API — POST to register, GET to discover

Free tier includes 100 discoveries/month. No credit card required.

Open source: github.com/rtsubber/agent-registry
Try it: https://agentregistry.co