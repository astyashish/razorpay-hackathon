"""
Crustdata API Client — async wrapper for all Crustdata endpoints.
Base URL: https://api.crustdata.com
Auth: Bearer token via CRUSTDATA_API_KEY env var.
Docs: https://docs.crustdata.com
"""

import os
import httpx
from typing import Optional

BASE_URL = "https://api.crustdata.com"
_TIMEOUT = 30


def _headers() -> dict:
    key = os.getenv("CRUSTDATA_API_KEY", "")
    if not key:
        raise RuntimeError("CRUSTDATA_API_KEY not set — add it to .env")
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


async def _get(path: str, params: dict | None = None) -> dict | list:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.get(f"{BASE_URL}{path}", headers=_headers(), params=params)
        r.raise_for_status()
        return r.json()


async def _post(path: str, body: dict | None = None, params: dict | None = None) -> dict | list:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.post(
            f"{BASE_URL}{path}", headers=_headers(), json=body or {}, params=params
        )
        r.raise_for_status()
        return r.json()


# ── Company APIs ──────────────────────────────────────────────────


async def identify_company(
    company_name: str | None = None,
    company_website: str | None = None,
    company_linkedin_url: str | None = None,
    count: int = 3,
) -> list[dict]:
    """Resolve a company to Crustdata IDs (FREE endpoint)."""
    body: dict = {"count": count}
    if company_website:
        body["query_company_website"] = company_website
    elif company_linkedin_url:
        body["query_company_linkedin_url"] = company_linkedin_url
    elif company_name:
        body["query_company_name"] = company_name
    return await _post("/screener/identify/", body)


async def enrich_company(
    company_domain: str | None = None,
    company_name: str | None = None,
    company_linkedin_url: str | None = None,
    company_id: str | None = None,
    fields: str | None = None,
) -> dict:
    """Full company enrichment — firmographics, headcount, growth signals."""
    params: dict = {}
    if company_domain:
        params["company_domain"] = company_domain
    elif company_name:
        params["company_name"] = company_name
    elif company_linkedin_url:
        params["company_linkedin_url"] = company_linkedin_url
    elif company_id:
        params["company_id"] = company_id
    if fields:
        params["fields"] = fields
    return await _get("/screener/company", params)


async def search_companies_realtime(filters: list[dict], page: int = 1) -> dict:
    """Realtime company search with filters."""
    return await _post("/screener/company/search", {"filters": filters, "page": page})


async def search_companies_db(
    filters: dict, limit: int = 50, sorts: list | None = None, cursor: str | None = None
) -> dict:
    """In-DB company search (fast, rich filters)."""
    body: dict = {"filters": filters, "limit": limit}
    if sorts:
        body["sorts"] = sorts
    if cursor:
        body["cursor"] = cursor
    return await _post("/screener/companydb/search", body)


async def get_company_linkedin_posts(
    company_domain: str | None = None,
    company_linkedin_url: str | None = None,
    company_name: str | None = None,
    company_id: str | None = None,
    page: int = 1,
    limit: int = 10,
    post_types: str = "original",
) -> list[dict]:
    """Fetch recent LinkedIn posts for a company."""
    params: dict = {"page": page, "limit": limit, "post_types": post_types}
    if company_domain:
        params["company_domain"] = company_domain
    elif company_linkedin_url:
        params["company_linkedin_url"] = company_linkedin_url
    elif company_name:
        params["company_name"] = company_name
    elif company_id:
        params["company_id"] = company_id
    return await _get("/screener/linkedin_posts", params)


async def search_linkedin_posts_by_keyword(
    keyword: str,
    date_posted: str = "past-month",
    sort_by: str = "relevance",
    page: int = 1,
    limit: int | None = None,
    exact_keyword_match: bool = False,
    filters: list | None = None,
) -> dict:
    """Search LinkedIn posts by keyword."""
    body: dict = {"keyword": keyword, "date_posted": date_posted, "sort_by": sort_by}
    if exact_keyword_match:
        body["exact_keyword_match"] = True
        body["limit"] = limit or 10
    else:
        body["page"] = page
    if filters:
        body["filters"] = filters
    return await _post("/screener/linkedin_posts/keyword_search/", body)


# ── People APIs ───────────────────────────────────────────────────


async def enrich_person(
    linkedin_profile_url: str | None = None,
    business_email: str | None = None,
    enrich_realtime: bool = True,
    fields: str = (
        "linkedin_profile_url,linkedin_flagship_url,name,location,email,"
        "title,last_updated,headline,summary,num_of_connections,skills,"
        "profile_picture_url,twitter_handle,languages,"
        "all_employers,past_employers,current_employers,"
        "education_background,all_titles,all_schools,all_degrees"
    ),
) -> dict:
    """Enrich a person by LinkedIn URL or email — returns verified email, history, etc."""
    params: dict = {"fields": fields, "enrich_realtime": str(enrich_realtime).lower()}
    if linkedin_profile_url:
        params["linkedin_profile_url"] = linkedin_profile_url
    if business_email:
        params["business_email"] = business_email
    return await _get("/screener/person/enrich", params)


async def search_people_realtime(filters: list[dict], page: int = 1) -> dict:
    """Search people in real-time with filters (title, company, region, etc.)."""
    return await _post("/screener/person/search", {"filters": filters, "page": page})


async def search_people_db(
    filters: dict, limit: int = 20, cursor: str | None = None
) -> dict:
    """In-DB people search (fast, rich filters)."""
    body: dict = {"filters": filters, "limit": limit}
    if cursor:
        body["cursor"] = cursor
    return await _post("/screener/persondb/search", body)


async def get_person_linkedin_posts(
    person_linkedin_url: str,
    page: int = 1,
    limit: int = 10,
) -> list[dict]:
    """Fetch recent LinkedIn posts for a person."""
    return await _get(
        "/screener/linkedin_posts",
        {"person_linkedin_url": person_linkedin_url, "page": page, "limit": limit},
    )


# ── Web APIs ──────────────────────────────────────────────────────


async def web_search(query: str, geolocation: str = "US", fetch_content: bool = False) -> dict:
    """Google-quality web search via Crustdata."""
    params = {"fetch_content": str(fetch_content).lower()} if fetch_content else {}
    return await _post("/screener/web-search", {"query": query, "geolocation": geolocation}, params)


async def web_fetch(urls: list[str]) -> list[dict]:
    """Fetch full page HTML for URLs."""
    return await _post("/screener/web-fetch", {"urls": urls})


# ── Dataset APIs ──────────────────────────────────────────────────


async def get_job_listings(
    company_ids: list[int],
    date_after: str | None = None,
    count: int = 100,
    offset: int = 0,
) -> dict:
    """Get job listings for companies by their Crustdata IDs."""
    conditions = [{"column": "company_id", "type": "in", "value": company_ids}]
    if date_after:
        conditions.append({"column": "date_updated", "type": ">", "value": date_after})
    return await _post(
        "/data_lab/job_listings/Table/",
        {
            "tickers": [],
            "dataset": {"name": "job_listings", "id": "joblisting"},
            "filters": {"op": "and", "conditions": conditions},
            "groups": [],
            "aggregations": [],
            "functions": [],
            "offset": offset,
            "count": count,
            "sorts": [],
        },
    )


# ── Watcher API ───────────────────────────────────────────────────


async def create_watch(body: dict) -> dict:
    """Create a new watcher (job change, headcount milestone, etc.)."""
    return await _post("/watcher/watches", body)


async def update_watch(watch_id: str, body: dict) -> dict:
    """Update an existing watcher status."""
    return await _post(f"/watcher/watches/{watch_id}/update", body)


# ── Auxiliary ─────────────────────────────────────────────────────


async def get_remaining_credits() -> dict:
    """Check remaining Crustdata API credits."""
    return await _get("/user/credits")
