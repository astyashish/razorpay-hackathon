"""
Data-gathering layer — powered by Crustdata APIs with free-source fallbacks.

Primary sources (Crustdata):
  - Company Identify / Enrich / LinkedIn Posts / Job Listings
  - People Search / Enrich
  - Web Search / Web Fetch

Fallback sources (free, no key): DuckDuckGo, GitHub API, Crawl4AI.
"""

import asyncio
import json
import re
import os
import httpx
from ddgs import DDGS

from src.crustdata_client import (
    identify_company,
    enrich_company,
    get_company_linkedin_posts,
    search_linkedin_posts_by_keyword,
    get_job_listings,
    web_search,
    web_fetch,
)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")


# ── Crustdata-powered company intelligence ────────────────────────


async def hit_crustdata(company_name: str) -> dict:
    """
    Full Crustdata company pipeline:
      1. Identify company (FREE) → get company_id & domain
      2. Enrich company → firmographics, headcount, growth, funding
      3. LinkedIn posts → recent activity & engagement signals
      4. Job listings → hiring signals & budget inference
    """
    try:
        # Step 1: Identify — FREE, no credits consumed
        matches = await identify_company(company_name=company_name)
        if not matches:
            return {"source": "crustdata", "error": "Company not found", "confidence": 0}

        top = matches[0]
        company_id = top.get("company_id")
        domain = top.get("company_website_domain", "")
        linkedin_url = top.get("linkedin_profile_url", "")

        # Step 2: Enrich — full firmographic profile
        enriched = {}
        try:
            if domain:
                enriched = await enrich_company(company_domain=domain)
            elif company_id:
                enriched = await enrich_company(company_id=str(company_id))
            if isinstance(enriched, list):
                enriched = enriched[0] if enriched else {}
        except Exception:
            enriched = {}

        # Step 3: Recent LinkedIn posts (company page)
        posts = []
        try:
            if domain:
                posts_raw = await get_company_linkedin_posts(company_domain=domain, limit=5)
            elif linkedin_url:
                posts_raw = await get_company_linkedin_posts(company_linkedin_url=linkedin_url, limit=5)
            else:
                posts_raw = []
            posts = [
                {
                    "text": p.get("text", "")[:200],
                    "date": p.get("date_posted"),
                    "reactions": p.get("total_reactions", 0),
                    "comments": p.get("total_comments", 0),
                }
                for p in (posts_raw if isinstance(posts_raw, list) else [])
            ]
        except Exception:
            posts = []

        # Step 4: Job listings — hiring signals
        jobs = []
        try:
            if company_id:
                jobs_data = await get_job_listings([company_id], count=20)
                rows = jobs_data.get("rows", [])
                fields = [f.get("api_name") for f in jobs_data.get("fields", [])]
                for row in rows:
                    if row:
                        job = dict(zip(fields, row)) if fields else {}
                        title = job.get("job_title") or (row[14] if len(row) > 14 else "")
                        jobs.append(title)
        except Exception:
            jobs = []

        # Assemble
        headcount_data = enriched.get("headcount", {})
        latest_headcount = (
            headcount_data.get("linkedin_headcount")
            if isinstance(headcount_data, dict)
            else enriched.get("linkedin_headcount")
        )

        return {
            "source": "crustdata",
            "confidence": 0.95,
            "company_id": company_id,
            "company_name": enriched.get("company_name") or top.get("company_name", company_name),
            "description": enriched.get("linkedin_company_description", ""),
            "website": enriched.get("company_website", ""),
            "domain": domain,
            "linkedin_url": linkedin_url or enriched.get("linkedin_profile_url", ""),
            "hq_location": enriched.get("hq_street_address", ""),
            "hq_country": enriched.get("hq_country", ""),
            "headcount": latest_headcount,
            "year_founded": enriched.get("year_founded", ""),
            "funding_stage": enriched.get("acquisition_status", ""),
            "markets": enriched.get("markets", []),
            "taxonomy": enriched.get("taxonomy", {}),
            "recent_posts": posts,
            "active_job_titles": jobs[:10],
            "is_hiring": len(jobs) > 0,
        }

    except Exception as e:
        return {"source": "crustdata", "error": str(e), "confidence": 0}


# ── Crustdata Web Search (replaces DuckDuckGo for website finding) ───


async def scrape_company_website(company_name: str) -> dict:
    """
    Use Crustdata Web Search to find company website, then Web Fetch for content.
    Falls back to DuckDuckGo + Crawl4AI if Crustdata key not set.
    """
    crustdata_key = os.getenv("CRUSTDATA_API_KEY", "")

    if crustdata_key:
        try:
            # Use Crustdata web search
            search_results = await web_search(f"{company_name} official website", fetch_content=True)
            results = search_results.get("results", [])
            if results:
                url = results[0].get("url", "")
                snippet = results[0].get("snippet", "")
                # If fetch_content was used, content may be in the result
                content = results[0].get("content", snippet)
                return {
                    "source": "crustdata_web",
                    "confidence": 0.9,
                    "url": url,
                    "data": json.dumps({
                        "description": content[:500] if content else snippet,
                        "products": [],
                        "customers": [],
                        "tech_stack": [],
                    }),
                    "raw": content[:3000] if content else snippet,
                }
        except Exception:
            pass

    # Fallback: DuckDuckGo + httpx
    url = _ddg_find_url(company_name)
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            raw_text = r.text[:3000]
            data = {
                "description": raw_text[:500],
                "products": [],
                "customers": [],
                "tech_stack": [],
            }
            m = re.search(r'(\d[\d,]*)\s+(?:employees?|team members?|people)', raw_text, re.IGNORECASE)
            if m:
                data["team_size_mentioned"] = m.group(0)
            m = re.search(r'(?:raised|funding|series [a-e]|seed)[^\n]{0,80}', raw_text, re.IGNORECASE)
            if m:
                data["funding_mentioned"] = m.group(0).strip()
            return {"source": "httpx", "url": url, "data": json.dumps(data), "raw": raw_text}
    except Exception as e:
        return {"source": "httpx", "error": str(e), "url": url, "confidence": 0}


def _ddg_find_url(company_name: str) -> str:
    """DuckDuckGo fallback for URL discovery."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(f"{company_name} official website", max_results=3))
        if results:
            return results[0].get("href", f"https://{company_name.lower().replace(' ', '-')}.com")
    except Exception:
        pass
    return f"https://{company_name.lower().replace(' ', '-')}.com"


# ── Crustdata Web Fetch for careers page ──────────────────────────


async def scrape_careers_page(company_name: str, base_url: str) -> dict:
    """Scrape careers page — Crustdata Web Fetch with Crawl4AI fallback."""
    careers_url = f"{base_url.rstrip('/')}/careers"
    crustdata_key = os.getenv("CRUSTDATA_API_KEY", "")

    if crustdata_key:
        try:
            pages = await web_fetch([careers_url])
            if pages and pages[0].get("success"):
                content = pages[0].get("content", "")
                return {
                    "source": "crustdata_web_fetch",
                    "raw": content[:2000],
                    "is_hiring": len(content) > 500,
                    "signal": f"Active hiring page found at {careers_url}" if len(content) > 500 else None,
                }
        except Exception:
            pass

    # Fallback: httpx
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(careers_url, headers={"User-Agent": "Mozilla/5.0"})
            text = r.text[:2000]
            return {
                "source": "httpx",
                "raw": text,
                "is_hiring": len(text) > 500,
                "signal": f"Active hiring page at {careers_url}" if len(text) > 500 else None,
            }
    except Exception as e:
        return {"source": "httpx", "error": str(e), "is_hiring": False}


# ── Crustdata LinkedIn Posts Keyword Search ───────────────────────


async def search_intent_signals(company_name: str, keywords: list[str] | None = None) -> dict:
    """
    Search LinkedIn posts for intent signals — prospects discussing pain points,
    evaluating tools, mentioning changes. Uses Crustdata LinkedIn Posts Keyword Search.
    """
    if not keywords:
        keywords = [f"{company_name} hiring", f"{company_name} scaling", f"{company_name} CRM"]

    all_posts = []
    for kw in keywords[:3]:  # Limit to 3 searches to save credits
        try:
            result = await search_linkedin_posts_by_keyword(
                keyword=kw, date_posted="past-month", sort_by="relevance", page=1
            )
            posts = result.get("posts", [])
            for p in posts[:3]:
                all_posts.append({
                    "keyword": kw,
                    "text": p.get("text", "")[:200],
                    "author": p.get("person_name", ""),
                    "author_title": p.get("person_title", ""),
                    "date": p.get("date_posted", ""),
                    "reactions": p.get("total_reactions", 0),
                })
        except Exception:
            continue

    return {
        "source": "crustdata_linkedin_keyword",
        "confidence": 0.9,
        "intent_posts": all_posts,
        "signals": [p["text"][:100] for p in all_posts[:5]],
    }


# ── News via Crustdata Web Search (primary) + GNews/DDG fallback ──


async def hit_newsapi(company_name: str) -> dict:
    """
    Get recent news: Crustdata Web Search (primary) → GNews → DuckDuckGo News.
    """
    crustdata_key = os.getenv("CRUSTDATA_API_KEY", "")

    # Primary: Crustdata Web Search
    if crustdata_key:
        try:
            search_results = await web_search(f"{company_name} news latest")
            results = search_results.get("results", [])
            if results:
                articles = [
                    {"title": r.get("title", ""), "date": "", "url": r.get("url", "")}
                    for r in results[:5]
                ]
                return {
                    "source": "crustdata_web_search",
                    "confidence": 0.9,
                    "articles": articles,
                    "signals": [a["title"] for a in articles[:3]],
                }
        except Exception:
            pass

    # Fallback 1: GNews
    if GNEWS_API_KEY:
        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(
                    "https://gnews.io/api/v4/search",
                    params={
                        "q": company_name,
                        "lang": "en",
                        "max": 5,
                        "sortby": "publishedAt",
                        "apikey": GNEWS_API_KEY,
                    },
                    timeout=10,
                )
                articles = r.json().get("articles", [])
                return {
                    "source": "gnews",
                    "confidence": 0.85,
                    "articles": [
                        {"title": a["title"], "date": a["publishedAt"], "url": a["url"]}
                        for a in articles
                    ],
                    "signals": [a["title"] for a in articles[:3]],
                }
            except Exception as e:
                return {"source": "gnews", "error": str(e), "confidence": 0}

    # Fallback 2: DuckDuckGo News
    try:
        with DDGS() as ddgs:
            raw = list(ddgs.news(company_name, max_results=5, timelimit="m"))
        return {
            "source": "ddg_news",
            "confidence": 0.75,
            "articles": [
                {"title": a["title"], "date": a.get("date", ""), "url": a.get("url", "")}
                for a in raw
            ],
            "signals": [a["title"] for a in raw[:3]],
        }
    except Exception as e:
        return {"source": "ddg_news", "error": str(e), "confidence": 0}


# ── GitHub API (unchanged — free) ─────────────────────────────────


async def hit_github_api(company_name: str) -> dict:
    """Infer tech stack from GitHub org."""
    async with httpx.AsyncClient() as client:
        try:
            org_slug = company_name.lower().replace(" ", "")
            headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
            r = await client.get(
                f"https://api.github.com/orgs/{org_slug}/repos",
                params={"per_page": 10, "sort": "updated"},
                headers=headers,
                timeout=10,
            )
            repos = r.json() if r.status_code == 200 else []
            if isinstance(repos, list):
                languages = list(set(repo.get("language") for repo in repos if repo.get("language")))
                stars = sum(repo.get("stargazers_count", 0) for repo in repos)
                return {
                    "source": "github",
                    "confidence": 0.9,
                    "languages": languages,
                    "total_stars": stars,
                    "repo_count": len(repos),
                    "is_open_source": len(repos) > 0,
                }
        except Exception as e:
            return {"source": "github", "error": str(e), "confidence": 0}
    return {}


# ── ProductHunt (unchanged — scraper) ─────────────────────────────


async def scrape_product_hunt(company_name: str) -> dict:
    """Check ProductHunt for recent launches."""
    try:
        url = f"https://www.producthunt.com/search?q={company_name.replace(' ', '+')}"
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            raw = r.text[:1000]
            has_launch = company_name.lower() in raw.lower()
            return {
                "source": "producthunt",
                "confidence": 0.75,
                "has_launch": has_launch,
                "signal": f"{company_name} found on ProductHunt" if has_launch else None,
                "raw": raw,
            }
    except Exception as e:
        return {"source": "producthunt", "error": str(e)}
