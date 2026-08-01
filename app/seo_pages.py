# SEO Pages for AgentSeek
# Agent detail pages, category pages, sitemap, and robots.txt

import json
import re
import time
import math
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, Response

router = APIRouter()

# Category metadata for SEO
CATEGORY_META = {
    "developer_tools": {"title": "AI Developer Tools & Agent Frameworks", "desc": "Discover AI developer tools, agent frameworks, and coding assistants. Compare LangChain, CrewAI, AutoGPT, GitHub Copilot, and more.", "h1": "AI Developer Tools & Agent Frameworks", "icon": "🛠️"},
    "communication": {"title": "AI Voice & Communication Agents", "desc": "Find AI phone agents, voice platforms, and communication tools. Compare Clara, Bland AI, ElevenLabs, Deepgram, Vapi, and more.", "h1": "AI Voice & Communication Agents", "icon": "📞"},
    "search": {"title": "AI Search & Research Agents", "desc": "Discover AI-powered search engines and research tools. Compare Perplexity, Tavily, Exa, and more for agentic workflows.", "h1": "AI Search & Research Agents", "icon": "🔍"},
    "productivity": {"title": "AI Productivity & Writing Agents", "desc": "Find AI productivity and writing assistants. Compare Grammarly, Jasper, Clozr, and more for content creation and workflow automation.", "h1": "AI Productivity & Writing Agents", "icon": "✍️"},
    "monitoring": {"title": "AI Monitoring & Observability Agents", "desc": "Discover AI agent monitoring, observability, and trust scoring platforms. Compare Agent Monitor, LangSmith, Helicone, and more.", "h1": "AI Monitoring & Observability Agents", "icon": "📊"},
    "creative": {"title": "AI Creative & Image Generation Agents", "desc": "Find AI image generation, video creation, and creative tools. Compare Midjourney, Runway ML, Stability AI, and more.", "h1": "AI Creative & Image Generation Agents", "icon": "🎨"},
    "payments": {"title": "AI Payment & Transaction Agents", "desc": "Discover AI payment processing, escrow, and transaction agents. Compare AgentPay, Stripe Agent Toolkit, and more.", "h1": "AI Payment & Transaction Agents", "icon": "💳"},
    "data": {"title": "AI Data & Web Scraping Agents", "desc": "Find AI-powered data extraction and web scraping agents. Compare Apify, Firecrawl, and more for agentic data pipelines.", "h1": "AI Data & Web Scraping Agents", "icon": "🕸️"},
    "customer_support": {"title": "AI Customer Support Agents", "desc": "Discover AI customer support and help desk agents. Compare Intercom Fin, Zendesk AI, and more for automated support.", "h1": "AI Customer Support Agents", "icon": "🎧"},
    "automation": {"title": "AI Automation & Integration Agents", "desc": "Find AI automation platforms and integration agents. Compare Zapier AI Actions, Make, and more for workflow automation.", "h1": "AI Automation & Integration Agents", "icon": "⚙️"},
    "marketing": {"title": "AI Marketing & SEO Agents", "desc": "Discover AI marketing, SEO, and content optimization agents. Compare Semrush, Surfer SEO, BoostRank, and more.", "h1": "AI Marketing & SEO Agents", "icon": "📈"},
    "legal": {"title": "AI Legal & Contract Agents", "desc": "Find AI legal research, contract analysis, and document agents. Compare Harvey AI, DocuSign AI, and more.", "h1": "AI Legal & Contract Agents", "icon": "⚖️"},
    "security": {"title": "AI Security & Threat Detection Agents", "desc": "Discover AI cybersecurity and threat detection agents. Compare CrowdStrike Charlotte AI and more for automated security.", "h1": "AI Security & Threat Detection Agents", "icon": "🛡️"},
    "healthcare": {"title": "AI Healthcare Agents", "desc": "Find AI healthcare documentation and clinical support agents. Compare Abridge and more for medical AI automation.", "h1": "AI Healthcare Agents", "icon": "🏥"},
    "education": {"title": "AI Education & Tutoring Agents", "desc": "Discover AI tutoring and education agents. Compare Khan Academy Khanmigo and more for adaptive learning.", "h1": "AI Education & Tutoring Agents", "icon": "🎓"},
    "career": {"title": "AI Career & Resume Agents", "desc": "Find AI resume builders, career coaching, and job search agents. Compare ResumeForge and more for career advancement.", "h1": "AI Career & Resume Agents", "icon": "💼"},
    "hr": {"title": "AI HR & Recruiting Agents", "desc": "Discover AI hiring, screening, and recruitment agents. Compare Mercor AI and more for automated recruiting.", "h1": "AI HR & Recruiting Agents", "icon": "👥"},
    "analytics": {"title": "AI Data Analytics Agents", "desc": "Find AI data analysis and visualization agents. Compare Julius AI and more for turning data into insights.", "h1": "AI Data Analytics Agents", "icon": "📉"},
    "real_estate": {"title": "AI Real Estate Agents", "desc": "Discover AI-powered property valuation and market analysis agents. Compare RealtyMole and more for real estate intelligence.", "h1": "AI Real Estate Agents", "icon": "🏠"},
    "verification": {"title": "AI Business Verification Agents", "desc": "Find AI business verification, scam detection, and trust scoring agents. Compare Local-Eye and more for automated verification.", "h1": "AI Business Verification Agents", "icon": "✅"},
    "tools": {"title": "AI Analysis & SEO Tools", "desc": "Discover AI-powered analysis tools. Compare BoostRank SEO Analyzer and more for automated insights.", "h1": "AI Analysis & SEO Tools", "icon": "🔧"},
}

# Shared CSS (extracted for consistency and future caching)
_SEO_CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0a0f;color:#e4e4e7;line-height:1.6}
.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);border:0}
.container{max-width:800px;margin:0 auto;padding:24px 16px}
a.skip-link{position:absolute;top:-100px;left:0;background:#6366f1;color:#fff;padding:8px 16px;z-index:100;border-radius:0 0 8px 0;font-size:14px}
a.skip-link:focus{top:0}
.breadcrumb{font-size:13px;color:#9ca3af;margin-bottom:16px}
.breadcrumb a{color:#818cf8;text-decoration:none}
.breadcrumb a:hover{text-decoration:underline}
.breadcrumb span[aria-current]{color:#71717a}
.agent-header{display:flex;gap:16px;align-items:flex-start;margin-bottom:24px}
.agent-icon{width:64px;height:64px;border-radius:12px;background:#18181b;object-fit:contain}
.agent-title{font-size:28px;font-weight:700;color:#fff;line-height:1.3}
.agent-meta{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:6px}
.trust-badge{background:#18181b;color:#d1d5db;padding:3px 10px;border-radius:6px;font-size:12px;font-weight:500}
.trust-badge.high{border:1px solid #22c55e33;color:#4ade80}
.trust-badge.medium{border:1px solid #fbbf2433;color:#fbbf24}
.trust-badge.growing{border:1px solid #818cf833;color:#818cf8}
.verified-badge{font-size:13px;padding:3px 10px;border-radius:6px;font-weight:500}
.verified-badge.verified{background:#22c55e15;color:#4ade80;border:1px solid #22c55e33}
.verified-badge.listed{background:#818cf815;color:#a5b4fc;border:1px solid #818cf833}
.category-link{color:#818cf8;text-decoration:none;font-size:13px;background:#18181b;padding:3px 10px;border-radius:6px}
.category-link:hover{text-decoration:underline}
.description{font-size:16px;line-height:1.75;color:#a1a1aa;margin-bottom:28px;max-width:700px}
.section{margin-bottom:28px}
.section h2{font-size:18px;font-weight:600;color:#fff;margin-bottom:12px;padding-bottom:6px;border-bottom:1px solid #1e1e26}
.cap-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px}
.cap-item{background:#18181b;padding:8px 12px;border-radius:6px;font-size:13px;color:#a1a1aa;border:1px solid #1e1e26}
.price-card{background:#18181b;border:1px solid #27272a;border-radius:8px;padding:16px}
.price-tier{margin-bottom:8px}
.price-label{font-weight:600;color:#fff}
.cta-row{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:24px}
.cta{display:inline-flex;align-items:center;gap:6px;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px;transition:all .15s}
.cta.primary{background:#6366f1;color:#fff}
.cta.primary:hover{background:#4f46e5;transform:translateY(-1px)}
.cta.secondary{background:#18181b;border:1px solid #27272a;color:#d1d5db}
.cta.secondary:hover{border-color:#6366f1;color:#fff}
.cta.claim{background:transparent;border:1px solid #6366f1;color:#818cf8;font-size:13px;padding:8px 14px}
.cta.claim:hover{background:#6366f1;color:#fff}
.related-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px}
.related-card{display:flex;flex-direction:column;gap:4px;background:#18181b;padding:14px;border-radius:8px;text-decoration:none;color:#e4e4e7;border:1px solid #27272a;transition:border-color .15s}
.related-card:hover{border-color:#6366f1}
.related-name{font-weight:600;font-size:14px}
.related-meta{font-size:12px;color:#71717a}
.trust-bar{height:4px;border-radius:2px;background:#1e1e26;overflow:hidden;margin-top:4px}
.trust-bar-fill{height:100%;border-radius:2px}
.trust-bar-fill.high{background:#22c55e}
.trust-bar-fill.medium{background:#fbbf24}
.trust-bar-fill.growing{background:#818cf8}
.agent-grid{display:grid;gap:12px}
.agent-card{display:flex;gap:14px;padding:16px;background:#18181b;border:1px solid #27272a;border-radius:10px;text-decoration:none;color:#e4e4e7;transition:border-color .15s}
.agent-card:hover{border-color:#6366f1}
.card-icon{width:44px;height:44px;border-radius:8px;flex-shrink:0;background:#0a0a0f;object-fit:contain}
.card-content{flex:1;min-width:0}
.card-content h3{font-size:16px;font-weight:600;margin-bottom:4px;color:#fff}
.card-content p{font-size:13px;color:#9ca3af;margin-bottom:6px}
.card-meta{font-size:12px;color:#71717a;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.card-trust-bar{width:60px;height:3px;background:#1e1e26;border-radius:2px;overflow:hidden;display:inline-block;vertical-align:middle}
.card-trust-bar-fill{height:100%;border-radius:2px}
.cat-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}
.cat-card{display:block;padding:20px;background:#18181b;border:1px solid #27272a;border-radius:10px;text-decoration:none;color:#e4e4e7;transition:border-color .15s}
.cat-card:hover{border-color:#6366f1}
.cat-card h3{font-size:16px;font-weight:600;margin-bottom:4px;color:#fff}
.cat-card p{font-size:13px;color:#9ca3af;margin-bottom:8px;line-height:1.5}
.cat-count{font-size:12px;color:#71717a}
.cat-icon{font-size:24px;margin-bottom:8px}
.api-detail{font-size:14px;color:#9ca3af;margin-bottom:6px}
.api-detail strong{color:#d1d5db}
.api-detail code{background:#0a0a0f;padding:2px 8px;border-radius:4px;font-size:13px;color:#818cf8;word-break:break-all}
footer{margin-top:48px;padding-top:24px;border-top:1px solid #27272a;font-size:13px;color:#71717a}
footer a{color:#818cf8;text-decoration:none}
footer a:hover{text-decoration:underline}
footer .footer-links{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:8px}
@media(max-width:640px){
  .agent-header{flex-direction:column;gap:12px}
  .agent-title{font-size:22px}
  .container{padding:16px 12px}
  .description{font-size:15px}
  .cta-row{flex-direction:column}
  .cta{justify-content:center;text-align:center}
  .cap-grid{grid-template-columns:1fr}
  .related-grid{grid-template-columns:1fr}
  .cat-grid{grid-template-columns:1fr}
  .agent-card{flex-direction:column;gap:8px}
}
"""

def slugify(name: str) -> str:
    """Convert agent name to URL slug."""
    slug = name.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = slug.strip('-')
    return slug


def _truncate(text: str, max_len: int) -> str:
    """Truncate text at word boundary, never mid-word."""
    if len(text) <= max_len:
        return text
    # Find the last space before max_len
    truncated = text[:max_len]
    last_space = truncated.rfind(' ')
    if last_space > max_len * 0.6:  # Only break at space if it's not too early
        return text[:last_space] + '...'
    return truncated.rstrip() + '...'


def _trust_class(score) -> str:
    """Return CSS class for trust score tier."""
    s = int(score) if score else 0
    return "high" if s >= 85 else ("medium" if s >= 70 else "growing")


def _trust_color(score) -> str:
    """Return color for trust bar fill."""
    s = int(score) if score else 0
    if s >= 85:
        return "#22c55e"
    elif s >= 70:
        return "#fbbf24"
    return "#818cf8"


def render_agent_page(agent: dict, categories: list) -> str:
    """Render an SEO-optimized agent detail page."""
    name = agent.get("name", "Unknown")
    desc = agent.get("description", "") or ""
    category = agent.get("category", "")
    trust = agent.get("trust_score", 0)
    trust_int = int(trust) if trust else 0
    verified = agent.get("verified", 0)
    capabilities = agent.get("capabilities", [])
    if isinstance(capabilities, str):
        capabilities = [c.strip() for c in capabilities.split(",") if c.strip()]
    pricing = agent.get("pricing_details") or agent.get("pricing", {})
    if isinstance(pricing, str):
        try:
            pricing = json.loads(pricing)
        except:
            pricing = {}
    pricing_model = agent.get("pricing_model", "unknown") or "unknown"
    auth_method = agent.get("auth_method", "api_key") or "api_key"
    endpoint = agent.get("endpoint_url", "") or ""
    website = agent.get("website_url", "") or ""
    logo = agent.get("logo_url", "") or ""
    agent_id = agent.get("id", "")
    created_at = agent.get("created_at", "") or ""
    updated_at = agent.get("updated_at", "") or ""
    
    trust_tier = _trust_class(trust)
    trust_color = _trust_color(trust)
    
    # Favicon fallback based on website domain
    icon_src = logo if logo else f"https://www.google.com/s2/favicons?sz=64&domain={website.replace('https://','').replace('http://','').split('/')[0]}" if website else "https://www.google.com/s2/favicons?sz=64&domain=agentseek.co"
    icon_fallback = "https://www.google.com/s2/favicons?sz=64&domain=agentseek.co"
    
    # Verified badge
    if verified:
        badge_html = '<span class="verified-badge verified" aria-label="Verified by AgentSeek">✓ Verified</span>'
    else:
        badge_html = '<span class="verified-badge listed" aria-label="Listed on AgentSeek">📋 Listed</span>'
    
    # Claim CTA (only for non-verified agents)
    claim_html = f'<a href="/claim?agent_id={agent_id}" class="cta claim">✍️ Claim this listing</a>' if not verified else ''
    
    cat_meta = CATEGORY_META.get(category, {})
    cat_title = cat_meta.get("title", category.replace("_", " ").title())
    cat_desc = cat_meta.get("desc", f"AI {category.replace('_', ' ').title()} agents")
    cat_icon = cat_meta.get("icon", "🤖")
    
    # Meta description (clean, word-boundary truncated)
    meta_desc = _truncate(desc, 160)
    og_desc = _truncate(desc, 200)
    title_tag = f"{name} — {cat_title} | AgentSeek"
    
    # JSON-LD structured data (SoftwareApplication + BreadcrumbList)
    structured_data = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": name,
        "description": desc[:200],
        "applicationCategory": "BusinessApplication",
        "operatingSystem": "Web",
        "url": website or f"https://agentseek.co/agents/{slugify(name)}",
        "offers": {
            "@type": "Offer",
            "price": "0" if pricing_model in ("free", "freemium") else (str(pricing.get("paid", "").split("/")[0].replace("$", "").split(" ")[0]) if pricing.get("paid") else "0"),
            "priceCurrency": "USD"
        },
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": str(trust_int),
            "bestRating": "100",
            "worstRating": "0",
            "ratingCount": "1"
        }
    }
    if capabilities:
        structured_data["featureList"] = [c.replace("_", " ").title() for c in capabilities[:10]]
    if verified:
        structured_data["author"] = {
            "@type": "Organization",
            "name": "AgentSeek",
            "url": "https://agentseek.co"
        }
    
    breadcrumb_data = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://agentseek.co/"},
            {"@type": "ListItem", "position": 2, "name": cat_title, "item": f"https://agentseek.co/categories/{category}"},
            {"@type": "ListItem", "position": 3, "name": name, "item": f"https://agentseek.co/agents/{slugify(name)}"}
        ]
    }
    
    # FAQ structured data (for rich results)
    faq_data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": f"What is {name}?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": desc[:500] if desc else f"{name} is an AI agent listed on AgentSeek."
                }
            },
            {
                "@type": "Question",
                "name": f"How much does {name} cost?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": f"{name} uses a {pricing_model.replace('_', ' ')} pricing model." + (f" Free tier: {pricing['free']}." if pricing and pricing.get("free") else "") + (f" Paid plans: {pricing['paid']}." if pricing and pricing.get("paid") else "")
                }
            },
            {
                "@type": "Question",
                "name": f"What is the trust score of {name}?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": f"{name} has a trust score of {trust_int}/100 on AgentSeek." + (" It has been verified by the AgentSeek team." if verified else "")
                }
            }
        ]
    }
    
    # Pricing display
    pricing_html = ""
    if pricing:
        if pricing.get("free"):
            pricing_html += f'<div class="price-tier"><span class="price-label">Free:</span> <span style="color:#4ade80">{pricing["free"]}</span></div>'
        if pricing.get("paid"):
            pricing_html += f'<div class="price-tier"><span class="price-label">Paid:</span> <span style="color:#818cf8">{pricing["paid"]}</span></div>'
    elif pricing_model == "free":
        pricing_html = '<div class="price-tier"><span class="price-label" style="color:#4ade80">Free</span> — Open source / free tier</div>'
    elif pricing_model == "enterprise":
        pricing_html = '<div class="price-tier"><span class="price-label">Enterprise</span> — Contact for pricing</div>'
    else:
        pricing_html = '<div class="price-tier" style="color:#71717a">Contact for pricing details</div>'
    
    # Capabilities
    caps_html = ""
    if capabilities:
        caps_html = "".join(f'<li class="cap-item">{c.replace("_", " ").title()}</li>' for c in capabilities)
    
    # Related agents (same category, excluding current, sorted by trust)
    related_agents = sorted(
        [a for a in categories if a.get("category") == category and a.get("id") != agent_id],
        key=lambda a: float(a.get("trust_score", 0)),
        reverse=True
    )[:6]
    
    related_html = ""
    for a in related_agents:
        r_slug = slugify(a.get("name", ""))
        r_name = a.get("name", "")
        r_trust = int(a.get("trust_score", 0)) if a.get("trust_score") else 0
        r_verified = a.get("verified", 0)
        r_badge = "✓" if r_verified else "📋"
        r_tier = _trust_class(a.get("trust_score", 0))
        related_html += f'''<a href="/agents/{r_slug}" class="related-card" aria-label="View {r_name}">
            <span class="related-name">{r_name} {r_badge}</span>
            <div style="display:flex;align-items:center;gap:8px">
                <span class="related-meta">Trust: {r_trust}/100</span>
                <div class="trust-bar" style="width:40px"><div class="trust-bar-fill {r_tier}" style="width:{r_trust}%"></div></div>
            </div>
        </a>'''
    
    # How it works section
    how_it_works = """
    <div class="section">
        <h2>How to Use This Agent</h2>
        <ol style="list-style:none;padding:0;counter-reset:steps">
            <li style="counter-increment:steps;padding:12px 12px 12px 40px;background:#18181b;border:1px solid #1e1e26;border-radius:8px;margin-bottom:8px;position:relative">
                <span style="position:absolute;left:12px;top:12px;color:#6366f1;font-weight:700">{steps}</span>
                <strong style="color:#fff">Get an API Key</strong> — <a href="/v1/keys" style="color:#818cf8">Sign up free</a> to get your AgentSeek API key
            </li>
            <li style="counter-increment:steps;padding:12px 12px 12px 40px;background:#18181b;border:1px solid #1e1e26;border-radius:8px;margin-bottom:8px;position:relative">
                <strong style="color:#fff">Call the Endpoint</strong> — Use the API endpoint with your key to integrate this agent
            </li>
            <li style="counter-increment:steps;padding:12px 12px 12px 40px;background:#18181b;border:1px solid #1e1e26;border-radius:8px;margin-bottom:8px;position:relative">
                <strong style="color:#fff">Go Live</strong> — Deploy in minutes with automatic failover and monitoring
            </li>
        </ol>
    </div>""".replace("{steps}", "1")

    slug = slugify(name)
    
    # Always use dynamic OG image for better link previews
    og_image = f"https://agentseek.co/og-image/{slug}"
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta name="google-site-verification" content="ke_YxLxF8EJWmQzVGUu-PEyJ_f4Nr58ytPvux3IIuKo">
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="index, follow">
    <title>{title_tag}</title>
    <meta name="description" content="{meta_desc}">
    <link rel="canonical" href="https://agentseek.co/agents/{slug}">
    <meta property="og:title" content="{name} — AI Agent Directory | AgentSeek">
    <meta property="og:description" content="{og_desc}">
    <meta property="og:url" content="https://agentseek.co/agents/{slug}">
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="AgentSeek">
    <meta property="og:image" content="{og_image}">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:site" content="@agentseek">
    <meta name="twitter:title" content="{name} — AI Agent Directory | AgentSeek">
    <meta name="twitter:description" content="{og_desc}">
    <meta name="twitter:image" content="{og_image}">
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📡</text></svg>">
    <script type="application/ld+json">{json.dumps(structured_data)}</script>
    <script type="application/ld+json">{json.dumps(breadcrumb_data)}</script>
    <script type="application/ld+json">{json.dumps(faq_data)}</script>
    <style>{_SEO_CSS}</style>
</head>
<body>
    <a href="#main" class="skip-link">Skip to main content</a>
    <div class="container">
        <nav class="breadcrumb" aria-label="Breadcrumb">
            <a href="/">AgentSeek</a> &rsaquo; <a href="/categories/{category}">{cat_title}</a> &rsaquo; <span aria-current="page">{name}</span>
        </nav>
        
        <main id="main">
        <div class="agent-header">
            <img class="agent-icon" src="{icon_src}" alt="{name} icon" width="64" height="64" onerror="this.src='{icon_fallback}'" loading="lazy">
            <div>
                <h1 class="agent-title">{name}</h1>
                <div class="agent-meta">
                    {badge_html}
                    <span class="trust-badge {trust_tier}" aria-label="Trust score {trust_int} out of 100">
                        Trust: {trust_int}/100
                    </span>
                    <a href="/categories/{category}" class="category-link">{cat_icon} {cat_title}</a>
                </div>
                <div class="trust-bar" style="width:120px;margin-top:8px" aria-hidden="true">
                    <div class="trust-bar-fill {trust_tier}" style="width:{trust_int}%"></div>
                </div>
            </div>
        </div>
        
        <p class="description">{desc}</p>
        
        <div class="cta-row">
            <a href="/v1/agents/{agent_id}/manifest" class="cta primary" rel="nofollow">⚡ Get API Endpoint</a>
            {f'<a href="{website}" target="_blank" rel="noopener noreferrer" class="cta secondary">🌐 Visit Website</a>' if website else ''}
            {claim_html}
        </div>
        
        {"<div class='section'><h2>Capabilities</h2><ul style='list-style:none;padding:0' class='cap-grid' role='list'>" + caps_html + "</ul></div>" if capabilities else ""}
        
        <div class="section">
            <h2>Pricing</h2>
            <div class="price-card">
                <div style="font-size:14px;color:#71717a;margin-bottom:8px;text-transform:capitalize">{pricing_model.replace("_"," ")}</div>
                {pricing_html}
            </div>
        </div>
        
        <div class="section">
            <h2>API Details</h2>
            <div class="price-card">
                <div class="api-detail"><strong>Auth:</strong> <code>{auth_method.replace("_"," ").title()}</code></div>
                <div class="api-detail"><strong>Endpoint:</strong> <code>{endpoint}</code></div>
                {"<div class='api-detail'><strong>Website:</strong> <a href='" + website + "' style='color:#818cf8' target='_blank' rel='noopener'>" + website + "</a></div>" if website else ""}
            </div>
        </div>
        
        {how_it_works}
        
        {"<div class='section'><h2>Related Agents</h2><div class='related-grid' role='list'>" + related_html + "</div></div>" if related_html else ""}
        </main>
        
        <footer>
            <div class="footer-links">
                <a href="/">Find AI Agents</a>
                <a href="/categories">Browse Categories</a>
                <a href="/v1/keys">Get API Key</a>
            </div>
            <p>&copy; 2025–2026 AgentSeek — The AI Agent Directory</p>
        </footer>
    </div>
</body>
</html>"""


def render_category_page(category: str, agents: list, meta: dict) -> str:
    """Render an SEO-optimized category page."""
    cat_title = meta.get("title", category.replace("_", " ").title())
    cat_desc = meta.get("desc", "")
    cat_h1 = meta.get("h1", cat_title)
    cat_icon = meta.get("icon", "🤖")
    
    meta_desc = _truncate(cat_desc, 160)
    
    # JSON-LD for ItemList + BreadcrumbList
    items = []
    for i, a in enumerate(agents):
        items.append({
            "@type": "ListItem",
            "position": i + 1,
            "url": f"https://agentseek.co/agents/{slugify(a.get('name',''))}",
            "name": a.get("name", "")
        })
    structured_data = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": cat_title,
        "description": cat_desc,
        "numberOfItems": len(agents),
        "itemListElement": items
    }
    
    collection_data = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": cat_title,
        "description": cat_desc,
        "url": f"https://agentseek.co/categories/{category}",
        "isPartOf": {
            "@type": "WebSite",
            "name": "AgentSeek",
            "url": "https://agentseek.co"
        }
    }
    
    breadcrumb_data = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://agentseek.co/"},
            {"@type": "ListItem", "position": 2, "name": "Categories", "item": "https://agentseek.co/categories"},
            {"@type": "ListItem", "position": 3, "name": cat_title, "item": f"https://agentseek.co/categories/{category}"}
        ]
    }
    
    agents_html = ""
    for a in agents:
        a_name = a.get("name", "")
        a_desc_raw = a.get("description", "") or ""
        a_desc = _truncate(a_desc_raw, 140)
        a_trust = int(a.get("trust_score", 0)) if a.get("trust_score") else 0
        a_verified = a.get("verified", 0)
        a_logo = a.get("logo_url", "") or ""
        a_slug = slugify(a_name)
        a_website = a.get("website_url", "") or ""
        a_tier = _trust_class(a.get("trust_score", 0))
        a_color = _trust_color(a.get("trust_score", 0))
        
        # Favicon fallback based on agent's website domain
        icon_src = a_logo if a_logo else f"https://www.google.com/s2/favicons?sz=64&domain={a_website.replace('https://','').replace('http://','').split('/')[0]}" if a_website else "https://www.google.com/s2/favicons?sz=64&domain=agentseek.co"
        
        a_badge = '<span style="color:#4ade80;font-size:11px" aria-label="Verified">✓ Verified</span>' if a_verified else '<span style="color:#a5b4fc;font-size:11px" aria-label="Listed">📋 Listed</span>'
        
        agents_html += f"""
        <a href="/agents/{a_slug}" class="agent-card" aria-label="View {a_name}">
            <img class="card-icon" src="{icon_src}" alt="{a_name}" width="44" height="44" onerror="this.src='https://www.google.com/s2/favicons?sz=64&domain=agentseek.co'" loading="lazy">
            <div class="card-content">
                <h3>{a_name} {a_badge}</h3>
                <p>{a_desc}</p>
                <div class="card-meta">
                    Trust: {a_trust}/100
                    <div class="card-trust-bar" aria-hidden="true"><div class="card-trust-bar-fill" style="width:{a_trust}%;background:{a_color}"></div></div>
                </div>
            </div>
        </a>"""
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="index, follow">
    <title>{cat_title} — {len(agents)} AI Agents | AgentSeek Directory</title>
    <meta name="google-site-verification" content="ke_YxLxF8EJWmQzVGUu-PEyJ_f4Nr58ytPvux3IIuKo">
    <meta name="description" content="{meta_desc}">
    <link rel="canonical" href="https://agentseek.co/categories/{category}">
    <meta property="og:title" content="{cat_title} — {len(agents)} AI Agents | AgentSeek">
    <meta property="og:description" content="{meta_desc}">
    <meta property="og:url" content="https://agentseek.co/categories/{category}">
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="AgentSeek">
    <meta property="og:image" content="https://agentseek.co/og/categories/{category}">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:site" content="@agentseek">
    <meta name="twitter:title" content="{cat_title} — {len(agents)} AI Agents | AgentSeek">
    <meta name="twitter:description" content="{meta_desc}">
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📡</text></svg>">
    <script type="application/ld+json">{json.dumps(structured_data)}</script>
    <script type="application/ld+json">{json.dumps(collection_data)}</script>
    <script type="application/ld+json">{json.dumps(breadcrumb_data)}</script>
    <style>{_SEO_CSS}</style>
</head>
<body>
    <a href="#main" class="skip-link">Skip to main content</a>
    <div class="container">
        <nav class="breadcrumb" aria-label="Breadcrumb">
            <a href="/">AgentSeek</a> &rsaquo; <a href="/categories">Categories</a> &rsaquo; <span aria-current="page">{cat_title}</span>
        </nav>
        
        <main id="main">
        <h1>{cat_icon} {cat_h1}</h1>
        <p class="subtitle">{cat_desc}</p>
        <p style="color:#71717a;font-size:14px;margin-bottom:24px">{len(agents)} agent{"s" if len(agents) != 1 else ""} found — sorted by trust score</p>
        <div class="agent-grid" role="list">{agents_html}</div>
        </main>
        
        <footer>
            <div class="footer-links">
                <a href="/">Find AI Agents</a>
                <a href="/categories">Browse Categories</a>
                <a href="/v1/keys">Get API Key</a>
            </div>
            <p>&copy; 2025–2026 AgentSeek — The AI Agent Directory</p>
        </footer>
    </div>
</body>
</html>"""


def render_categories_index(categories_with_counts: list) -> str:
    """Render the categories index page."""
    total_agents = sum(count for _, count, _ in categories_with_counts)
    
    cats_html = ""
    for cat, count, meta in categories_with_counts:
        title = meta.get("title", cat.replace("_", " ").title())
        desc = _truncate(meta.get("desc", ""), 120)
        icon = meta.get("icon", "🤖")
        cats_html += f"""
        <a href="/categories/{cat}" class="cat-card" aria-label="View {count} {title} agents">
            <div class="cat-icon">{icon}</div>
            <h3>{title}</h3>
            <p>{desc}</p>
            <div class="cat-count">{count} agent{"s" if count != 1 else ""}</div>
        </a>"""
    
    meta_desc = f"Browse {total_agents} AI agents across {len(categories_with_counts)} categories. Find the right agent for developer tools, communication, search, creative, payments, and more."
    
    breadcrumb_data = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://agentseek.co/"},
            {"@type": "ListItem", "position": 2, "name": "Categories", "item": "https://agentseek.co/categories"}
        ]
    }
    
    collection_data = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "AI Agent Categories",
        "description": meta_desc,
        "url": "https://agentseek.co/categories",
        "isPartOf": {
            "@type": "WebSite",
            "name": "AgentSeek",
            "url": "https://agentseek.co"
        }
    }
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="index, follow">
    <title>Browse {len(categories_with_counts)} AI Agent Categories | AgentSeek Directory</title>
    <meta name="google-site-verification" content="ke_YxLxF8EJWmQzVGUu-PEyJ_f4Nr58ytPvux3IIuKo">
    <meta name="description" content="{meta_desc}">
    <link rel="canonical" href="https://agentseek.co/categories">
    <meta property="og:title" content="Browse AI Agent Categories | AgentSeek">
    <meta property="og:description" content="{meta_desc}">
    <meta property="og:url" content="https://agentseek.co/categories">
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="AgentSeek">
    <meta property="og:image" content="https://agentseek.co/og/categories">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:site" content="@agentseek">
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📡</text></svg>">
    <script type="application/ld+json">{json.dumps(breadcrumb_data)}</script>
    <script type="application/ld+json">{json.dumps(collection_data)}</script>
    <style>{_SEO_CSS}</style>
</head>
<body>
    <a href="#main" class="skip-link">Skip to main content</a>
    <div class="container">
        <nav class="breadcrumb" aria-label="Breadcrumb">
            <a href="/">AgentSeek</a> &rsaquo; <span aria-current="page">Categories</span>
        </nav>
        
        <main id="main">
        <h1>Browse AI Agent Categories</h1>
        <p class="subtitle">{total_agents} AI agents across {len(categories_with_counts)} categories. Find the right agent for any task.</p>
        <div class="cat-grid" role="list">{cats_html}</div>
        </main>
        
        <footer>
            <div class="footer-links">
                <a href="/">Find AI Agents</a>
                <a href="/categories">Browse Categories</a>
                <a href="/v1/keys">Get API Key</a>
            </div>
            <p>&copy; 2025–2026 AgentSeek — The AI Agent Directory</p>
        </footer>
    </div>
</body>
</html>"""