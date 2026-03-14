"""
LinkedIn data layer — powered by Crustdata People & Company APIs.

Replaces fragile Playwright stealth scraping with structured API calls:
  - Company LinkedIn data → Crustdata Company Enrich / Identify
  - Decision-maker search → Crustdata People Search (Realtime) + People Enrich
  - Verified emails → People Enrichment endpoint

Falls back to DuckDuckGo + Playwright only when CRUSTDATA_API_KEY is not set.
"""

import asyncio
import os
import re
import httpx

from src.crustdata_client import (
    identify_company,
    enrich_company,
    search_people_realtime,
    search_people_db,
    enrich_person,
    get_company_linkedin_posts,
)


async def scrape_linkedin_company(company_name: str) -> dict:
    """
    Get structured LinkedIn company data via Crustdata.
    Falls back to Playwright stealth if no API key.
    """
    crustdata_key = os.getenv("CRUSTDATA_API_KEY", "")

    if crustdata_key:
        try:
            # Identify company first (FREE)
            matches = await identify_company(company_name=company_name)
            if not matches:
                return {"source": "crustdata_linkedin", "error": "Company not found", "confidence": 0}

            top = matches[0]
            company_id = top.get("company_id")
            domain = top.get("company_website_domain", "")
            linkedin_url = top.get("linkedin_profile_url", "")
            headcount = top.get("linkedin_headcount")

            # Enrich for full LinkedIn data
            enriched = {}
            try:
                if domain:
                    enriched = await enrich_company(company_domain=domain)
                elif company_id:
                    enriched = await enrich_company(company_id=str(company_id))
                if isinstance(enriched, list):
                    enriched = enriched[0] if enriched else {}
            except Exception:
                pass

            headcount_val = enriched.get("linkedin_headcount") or headcount
            headcount_signal = f"{headcount_val} employees" if headcount_val else None

            return {
                "source": "crustdata_linkedin",
                "confidence": 0.95,
                "company_id": company_id,
                "company_name": enriched.get("company_name") or top.get("company_name", company_name),
                "headcount_signal": headcount_signal,
                "headcount": headcount_val,
                "description": enriched.get("linkedin_company_description", ""),
                "hq_country": enriched.get("hq_country", ""),
                "hq_location": enriched.get("hq_street_address", ""),
                "website": enriched.get("company_website", ""),
                "domain": domain,
                "linkedin_url": linkedin_url or enriched.get("linkedin_profile_url", ""),
                "twitter_url": enriched.get("company_twitter_url", ""),
                "year_founded": enriched.get("year_founded", ""),
                "raw_text": enriched.get("linkedin_company_description", "")[:2000],
                "url": linkedin_url or f"https://www.linkedin.com/company/{company_name.lower().replace(' ', '-')}",
            }
        except Exception as e:
            return {"source": "crustdata_linkedin", "error": str(e), "confidence": 0}

    # Fallback: Playwright stealth (original behavior)
    return await _playwright_scrape_linkedin_company(company_name)


async def find_decision_maker_linkedin(company_name: str, titles: list = None) -> dict:
    """
    Find the best decision-maker at a company using Crustdata People Search.
    Returns: name, title, verified email, LinkedIn URL.

    Pipeline:
      1. People Search Realtime → find people by company + title
      2. People Enrich → get verified email, full profile
    """
    crustdata_key = os.getenv("CRUSTDATA_API_KEY", "")

    if not titles:
        titles = ["VP Sales", "Head of Growth", "CEO", "Founder", "CTO"]

    if crustdata_key:
        # Try to find the company domain first for better matching
        domain = ""
        try:
            matches = await identify_company(company_name=company_name)
            if matches:
                domain = matches[0].get("company_website_domain", "")
        except Exception:
            pass

        for title in titles:
            try:
                # Build filters for People Search Realtime
                filters = [
                    {"filter_type": "CURRENT_TITLE", "type": "in", "value": [title]},
                ]
                if domain:
                    filters.append({"filter_type": "CURRENT_COMPANY", "type": "in", "value": [domain]})
                else:
                    filters.append({"filter_type": "CURRENT_COMPANY", "type": "in", "value": [company_name]})

                result = await search_people_realtime(filters=filters, page=1)
                profiles = result.get("profiles", [])

                if profiles:
                    person = profiles[0]
                    person_name = person.get("name", "")
                    person_title = person.get("default_position_title") or person.get("current_title") or title
                    linkedin_url = person.get("flagship_profile_url") or person.get("linkedin_profile_url", "")
                    person_email = None

                    # Extract email from search results
                    emails = person.get("emails", [])
                    if emails:
                        person_email = emails[0]

                    # If no email from search, try enrichment
                    if not person_email and linkedin_url:
                        try:
                            enriched = await enrich_person(linkedin_profile_url=linkedin_url)
                            if isinstance(enriched, list) and enriched:
                                enriched = enriched[0]
                            person_email = enriched.get("email")
                            if not person_name:
                                person_name = enriched.get("name", "")
                            if not person_title or person_title == title:
                                person_title = enriched.get("title") or person_title
                        except Exception:
                            pass

                    return {
                        "source": "crustdata_people",
                        "name": person_name,
                        "title": person_title,
                        "email": person_email,
                        "linkedin_url": linkedin_url,
                        "confidence": 0.90 if person_email else 0.70,
                    }

            except Exception:
                continue

        # If realtime search didn't work, try PersonDB search
        try:
            for title in titles[:3]:
                db_filters = {
                    "op": "and",
                    "conditions": [
                        {"column": "current_employers.title", "type": "(.)", "value": title},
                    ],
                }
                if domain:
                    db_filters["conditions"].append(
                        {"column": "current_employers.name", "type": "(.)", "value": company_name}
                    )
                else:
                    db_filters["conditions"].append(
                        {"column": "current_employers.name", "type": "(.)", "value": company_name}
                    )

                result = await search_people_db(filters=db_filters, limit=5)
                profiles = result.get("profiles", [])

                if profiles:
                    person = profiles[0]
                    person_name = person.get("name", "")
                    linkedin_url = person.get("flagship_profile_url") or person.get("linkedin_profile_url", "")
                    person_email = None

                    emails = person.get("emails", [])
                    if emails:
                        person_email = emails[0]

                    current = person.get("current_employers", [])
                    person_title = current[0].get("employee_title", title) if current else title

                    # Try enrichment for email if missing
                    if not person_email and linkedin_url:
                        try:
                            enriched = await enrich_person(linkedin_profile_url=linkedin_url)
                            if isinstance(enriched, list) and enriched:
                                enriched = enriched[0]
                            person_email = enriched.get("email")
                        except Exception:
                            pass

                    return {
                        "source": "crustdata_persondb",
                        "name": person_name,
                        "title": person_title,
                        "email": person_email,
                        "linkedin_url": linkedin_url,
                        "confidence": 0.85 if person_email else 0.65,
                    }
        except Exception:
            pass

    # Fallback: DuckDuckGo search (original behavior)
    return await _ddg_find_decision_maker(company_name, titles)


# ── Fallback implementations (Playwright / DuckDuckGo) ────────────


async def _playwright_scrape_linkedin_company(company_name: str) -> dict:
    """Fallback: simple httpx fetch of LinkedIn public page (no Playwright)."""
    slug = company_name.lower().replace(" ", "-").replace(".", "")
    url = f"https://www.linkedin.com/company/{slug}"
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            text = r.text[:2000]
            headcount_signal = None
            match = re.search(r'([\d,]+)\s+employees', text, re.IGNORECASE)
            if match:
                headcount_signal = match.group(0)
            return {
                "source": "linkedin",
                "confidence": 0.5,
                "headcount_signal": headcount_signal,
                "raw_text": text,
                "url": url,
            }
    except Exception as e:
        return {"source": "linkedin", "error": str(e), "confidence": 0}


async def _ddg_find_decision_maker(company_name: str, titles: list) -> dict:
    """DuckDuckGo fallback for finding decision makers."""
    from ddgs import DDGS

    for title in titles:
        try:
            query = f'site:linkedin.com/in "{company_name}" "{title}"'
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))

            for r in results:
                link = r.get("href", "")
                if "linkedin.com/in/" in link:
                    # Try to extract name from the search result snippet
                    name = ""
                    snippet = r.get("title", "") + " " + r.get("body", "")
                    nm = re.search(r'^([A-Z][a-z]+(?: [A-Z][a-z]+)+)', snippet.strip())
                    if nm:
                        name = nm.group(1)

                    return {
                        "source": "linkedin_ddg",
                        "name": name,
                        "title": title,
                        "linkedin_url": link,
                        "confidence": 0.50,
                    }
        except Exception:
            continue

    return {"source": "linkedin_ddg", "error": "No decision maker found", "confidence": 0}
