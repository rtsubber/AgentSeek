"""Blog pages for AgentSeek

Serves markdown blog posts from the blog/ directory with SEO-friendly URLs.
Blog index at /blog, individual posts at /blog/{slug}.
"""
import os
import re
import glob
import datetime
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, Response

import markdown

router = APIRouter()

BLOG_DIR = Path(__file__).resolve().parent.parent / "blog"

# ---------------------------------------------------------------------------
# Markdown parsing
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str):
    """Parse simple YAML-like frontmatter from markdown."""
    meta = {}
    if not text.startswith("---"):
        return meta, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return meta, text

    front = parts[1].strip()
    body = parts[2].strip()

    for line in front.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            # Handle list-style tags
            if key == "tags":
                tags = re.findall(r'"([^"]+)"', val)
                if not tags:
                    tags = [t.strip().strip('"').strip("'") for t in val.split(",") if t.strip()]
                meta[key] = tags
            else:
                meta[key] = val

    return meta, body


def _load_all_posts():
    """Load all blog posts, sorted by date descending."""
    posts = []
    for filepath in glob.glob(str(BLOG_DIR / "*.md")):
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        meta, body = _parse_frontmatter(text)
        slug = meta.get("slug", Path(filepath).stem)
        posts.append({
            "title": meta.get("title", slug.replace("-", " ").title()),
            "date": meta.get("date", "2026-01-01"),
            "author": meta.get("author", "AgentSeek"),
            "slug": slug,
            "excerpt": meta.get("excerpt", ""),
            "tags": meta.get("tags", []),
            "meta_description": meta.get("meta_description", meta.get("excerpt", "")),
            "body": body,
            "filepath": filepath,
        })
    # Sort by date descending
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def _render_markdown(body: str) -> str:
    """Render markdown to HTML with extensions."""
    md = markdown.Markdown(extensions=["extra", "codehilite", "toc", "sane_lists"])
    return md.convert(body)


def _format_date(date_str: str) -> str:
    """Format ISO date as readable string."""
    try:
        dt = datetime.datetime.fromisoformat(date_str)
        return dt.strftime("%B %d, %Y")
    except (ValueError, TypeError):
        return date_str


# ---------------------------------------------------------------------------
# Shared CSS — matches AgentSeek's dark theme
# ---------------------------------------------------------------------------

_BLOG_CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0a0f;color:#e4e4e7;line-height:1.6;-webkit-font-smoothing:antialiased}
.container{max-width:800px;margin:0 auto;padding:0 24px}
a{color:#818cf8;text-decoration:none}
a:hover{text-decoration:underline}

/* Nav */
nav{padding:16px 0;border-bottom:1px solid #27272a}
nav .container{display:flex;justify-content:space-between;align-items:center}
.logo{font-size:20px;font-weight:700;background:linear-gradient(135deg,#22c55e 0%,#818cf8 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;text-decoration:none}
.logo span{color:#71717a;font-weight:400;-webkit-text-fill-color:#71717a}
.nav-links{display:flex;gap:24px;align-items:center}
.nav-links a{color:#71717a;text-decoration:none;font-size:14px;transition:color .2s}
.nav-links a:hover{color:#e4e4e7;text-decoration:none}

/* Blog header */
.blog-header{padding:48px 0 32px;text-align:center;border-bottom:1px solid #27272a;margin-bottom:40px}
.blog-header h1{font-size:36px;font-weight:700;color:#fff;margin-bottom:8px;background:linear-gradient(135deg,#22c55e 0%,#818cf8 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.blog-header p{font-size:16px;color:#71717a;max-width:600px;margin:0 auto}

/* Post list */
.post-list{list-style:none;padding:0}
.post-item{padding:28px 0;border-bottom:1px solid #1e1e26;transition:border-color .15s}
.post-item:last-child{border-bottom:none}
.post-item:hover{border-color:#6366f1}
.post-title{font-size:22px;font-weight:600;color:#fff;margin-bottom:6px}
.post-title a{color:#fff;text-decoration:none}
.post-title a:hover{color:#818cf8;text-decoration:none}
.post-meta{font-size:13px;color:#71717a;margin-bottom:10px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.post-date{color:#818cf8}
.post-tags{display:flex;gap:6px;flex-wrap:wrap}
.tag{font-size:12px;color:#a1a1aa;background:#18181b;padding:2px 8px;border-radius:4px;border:1px solid #27272a}
.post-excerpt{font-size:15px;color:#a1a1aa;line-height:1.7;max-width:700px}
.read-more{display:inline-block;margin-top:12px;font-size:14px;color:#818cf8;font-weight:500}
.read-more:hover{color:#6366f1}

/* Single post */
.article-header{padding:32px 0 24px;border-bottom:1px solid #27272a;margin-bottom:32px}
.article-title{font-size:32px;font-weight:700;color:#fff;line-height:1.3;margin-bottom:12px}
.article-meta{font-size:14px;color:#71717a;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
.article-author{color:#a1a1aa}
.article-date{color:#818cf8}
.article-tags{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}
.article-body{font-size:17px;line-height:1.8;color:#d1d5db}
.article-body h1{font-size:28px;font-weight:700;color:#fff;margin:36px 0 16px;padding-bottom:6px;border-bottom:1px solid #1e1e26}
.article-body h2{font-size:22px;font-weight:600;color:#fff;margin:32px 0 14px}
.article-body h3{font-size:18px;font-weight:600;color:#fff;margin:24px 0 10px}
.article-body p{margin-bottom:18px}
.article-body ul,.article-body ol{margin-bottom:18px;padding-left:24px}
.article-body li{margin-bottom:6px;color:#d1d5db}
.article-body strong{color:#fff;font-weight:600}
.article-body em{color:#a5b4fc}
.article-body a{color:#818cf8;text-decoration:underline;text-decoration-color:rgba(129,140,248,0.3)}
.article-body a:hover{text-decoration-color:#818cf8}
.article-body blockquote{border-left:3px solid #6366f1;padding:12px 20px;margin:20px 0;background:#18181b;border-radius:0 8px 8px 0;color:#a1a1aa;font-style:italic}
.article-body code{background:#18181b;padding:2px 6px;border-radius:4px;font-size:14px;color:#a5b4fc;font-family:'SF Mono',Monaco,Consolas,monospace}
.article-body pre{background:#18181b;padding:16px;border-radius:8px;overflow-x:auto;margin:20px 0;border:1px solid #27272a}
.article-body pre code{background:none;padding:0;color:#d1d5db}
.article-body hr{border:none;border-top:1px solid #27272a;margin:32px 0}
.article-body img{max-width:100%;border-radius:8px;margin:20px 0}

/* Back link */
.back-link{display:inline-block;margin-bottom:24px;font-size:14px;color:#71717a}
.back-link:hover{color:#818cf8}

/* CTA box */
.cta-box{margin:40px 0;padding:24px;background:linear-gradient(135deg,rgba(99,102,241,0.08),rgba(34,197,94,0.08));border:1px solid #27272a;border-radius:12px;text-align:center}
.cta-box h3{font-size:18px;font-weight:600;color:#fff;margin-bottom:8px}
.cta-box p{font-size:14px;color:#a1a1aa;margin-bottom:16px}
.cta-btn{display:inline-flex;align-items:center;gap:6px;padding:10px 24px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px;background:#6366f1;color:#fff}
.cta-btn:hover{background:#4f46e5;text-decoration:none}

/* Footer */
footer{padding:32px 0;border-top:1px solid #27272a;margin-top:48px}
footer .container{text-align:center}
footer p{font-size:13px;color:#71717a;margin-bottom:8px}
footer a{color:#71717a}
footer a:hover{color:#818cf8}

/* Responsive */
@media(max-width:640px){
  .nav-links{display:none}
  .blog-header h1{font-size:28px}
  .article-title{font-size:24px}
  .article-body{font-size:16px}
  .article-body h1{font-size:24px}
  .article-body h2{font-size:20px}
}

/* Code highlight */
.codehilite{background:#18181b;border-radius:8px;padding:16px;border:1px solid #27272a;overflow-x:auto}
.codehilite pre{margin:0;background:none;border:none;padding:0}
"""

_NAV_HTML = """
<nav>
  <div class="container">
    <a href="/" class="logo">Agent<span>Seek</span></a>
    <div class="nav-links">
      <a href="/categories">Categories</a>
      <a href="/blog">Blog</a>
      <a href="/docs">API Docs</a>
      <a href="https://github.com/rtsubber/agent-registry" target="_blank">GitHub</a>
    </div>
  </div>
</nav>
"""

_FOOTER_HTML = """
<footer>
  <div class="container">
    <p>AgentSeek — Where humans find AI talent.</p>
    <p><a href="/categories">Browse Agents</a> · <a href="/blog">Blog</a> · <a href="/docs">API Docs</a> · <a href="https://github.com/rtsubber/agent-registry">GitHub</a></p>
  </div>
</footer>
"""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/blog", response_class=HTMLResponse)
@router.get("/blog/", response_class=HTMLResponse)
async def blog_index():
    """Blog index page — lists all posts."""
    posts = _load_all_posts()

    post_cards = ""
    for p in posts:
        date_display = _format_date(p["date"])
        tags_html = "".join(f'<span class="tag">{t}</span>' for t in p.get("tags", []))
        post_cards += f"""
    <li class="post-item">
      <h2 class="post-title"><a href="/blog/{p["slug"]}">{p["title"]}</a></h2>
      <div class="post-meta">
        <span class="post-date">{date_display}</span>
        <span>·</span>
        <span>{p.get("author", "AgentSeek")}</span>
        {f'<div class="post-tags">{tags_html}</div>' if tags_html else ''}
      </div>
      <p class="post-excerpt">{p["excerpt"]}</p>
      <a href="/blog/{p["slug"]}" class="read-more">Read more →</a>
    </li>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AgentSeek Blog — AI Agent Guides, Tutorials, and Insights</title>
  <meta name="description" content="Practical guides on finding, evaluating, and deploying AI agents for your business. No hype, just what works.">
  <meta property="og:title" content="AgentSeek Blog — AI Agent Insights">
  <meta property="og:description" content="Practical guides on finding, evaluating, and deploying AI agents for your business.">
  <meta property="og:url" content="https://agentseek.co/blog">
  <meta property="og:type" content="website">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="AgentSeek Blog">
  <meta name="twitter:description" content="Practical guides on AI agents for business.">
  <link rel="canonical" href="https://agentseek.co/blog">
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📡</text></svg>">
  <style>{_BLOG_CSS}</style>
</head>
<body>
{_NAV_HTML}
  <div class="blog-header">
    <div class="container">
      <h1>AgentSeek Blog</h1>
      <p>Practical guides on finding, evaluating, and deploying AI agents. No hype — just what works.</p>
    </div>
  </div>
  <div class="container">
    <ul class="post-list">
{post_cards}
    </ul>
  </div>
{_FOOTER_HTML}
</body>
</html>"""

    return HTMLResponse(content=html, headers={"Cache-Control": "public, max-age=300, s-maxage=600"})


@router.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post(slug: str):
    """Individual blog post page."""
    posts = _load_all_posts()
    post = None
    for p in posts:
        if p["slug"] == slug:
            post = p
            break

    if not post:
        raise HTTPException(status_code=404, detail="Blog post not found")

    date_display = _format_date(post["date"])
    content_html = _render_markdown(post["body"])
    tags_html = "".join(f'<span class="tag">{t}</span>' for t in post.get("tags", []))

    # Find related posts (same tag, excluding current)
    related = []
    for p in posts:
        if p["slug"] == slug:
            continue
        if set(p.get("tags", [])) & set(post.get("tags", [])):
            related.append(p)
    related = related[:3]

    related_html = ""
    if related:
        related_items = ""
        for r in related:
            r_date = _format_date(r["date"])
            related_items += f'<li class="post-item"><h2 class="post-title" style="font-size:18px"><a href="/blog/{r["slug"]}">{r["title"]}</a></h2><div class="post-meta"><span class="post-date">{r_date}</span></div><p class="post-excerpt" style="font-size:14px">{r["excerpt"][:120]}...</p></li>'
        related_html = f"""
  <div style="margin-top:48px">
    <h2 style="font-size:18px;font-weight:600;color:#fff;margin-bottom:16px;padding-bottom:6px;border-bottom:1px solid #1e1e26">Related Posts</h2>
    <ul class="post-list">{related_items}</ul>
  </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{post["title"]} — AgentSeek Blog</title>
  <meta name="description" content="{post.get("meta_description", post["excerpt"])}">
  <meta property="og:title" content="{post["title"]}">
  <meta property="og:description" content="{post["excerpt"]}">
  <meta property="og:url" content="https://agentseek.co/blog/{slug}">
  <meta property="og:type" content="article">
  <meta property="article:published_time" content="{post["date"]}">
  <meta property="article:author" content="{post.get("author", "AgentSeek")}">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="{post["title"]}">
  <meta name="twitter:description" content="{post["excerpt"]}">
  <link rel="canonical" href="https://agentseek.co/blog/{slug}">
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📡</text></svg>">
  <style>{_BLOG_CSS}</style>
</head>
<body>
{_NAV_HTML}
  <div class="container">
    <a href="/blog" class="back-link">← Back to Blog</a>
    <div class="article-header">
      <h1 class="article-title">{post["title"]}</h1>
      <div class="article-meta">
        <span class="article-date">{date_display}</span>
        <span>·</span>
        <span class="article-author">By {post.get("author", "AgentSeek")}</span>
      </div>
      {f'<div class="article-tags">{tags_html}</div>' if tags_html else ''}
    </div>
    <div class="article-body">
{content_html}
    </div>
    <div class="cta-box">
      <h3>Find the Right AI Agent for Your Business</h3>
      <p>Browse hundreds of AI agents by category, capability, and trust score.</p>
      <a href="/categories" class="cta-btn">Browse Agent Categories →</a>
    </div>
{related_html}
  </div>
{_FOOTER_HTML}
</body>
</html>"""

    return HTMLResponse(content=html, headers={"Cache-Control": "public, max-age=300, s-maxage=600"})


@router.get("/blog/sitemap.xml")
async def blog_sitemap():
    """Blog-specific sitemap fragment."""
    posts = _load_all_posts()
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    urls = [
        f'  <url><loc>https://agentseek.co/blog</loc><lastmod>{now}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>'
    ]
    for p in posts:
        urls.append(f'  <url><loc>https://agentseek.co/blog/{p["slug"]}</loc><lastmod>{p["date"]}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>')

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>"""

    return Response(content=xml, media_type="application/xml", headers={"Cache-Control": "public, max-age=600"})