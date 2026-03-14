import asyncio
import json
import os
from langchain_core.messages import HumanMessage

from src.utils import invoke_llm_resilient
from src.scrapers.crawl4ai_scraper import (
    scrape_company_website, hit_crustdata, hit_newsapi,
    hit_github_api, scrape_product_hunt, scrape_careers_page,
    search_intent_signals,
)
from src.scrapers.linkedin_stealth import scrape_linkedin_company

FUSION_PROMPT = """You are a B2B sales intelligence analyst. You have received data about "{company}" from {num_sources} different sources (including Crustdata's real-time company & people API).

SOURCE DATA:
{sources_json}

Your job:
1. Fuse all data into one clean company profile
2. Resolve conflicts by preferring: Crustdata API > most recent timestamp > official API > scraped data
3. Assign confidence % to each field (based on how many sources agree)
4. Identify the TOP 5 buying signals (e.g. "Series B funding 3 weeks ago", "Hiring 12 engineers", "CEO posted about scaling pain on LinkedIn", "Active job listings for SDRs")
5. Score ICP fit 1-10 (ideal customer: B2B SaaS, 50-500 employees, growing, needs GTM automation)

IMPORTANT:
- For headcount, trust Crustdata's linkedin_headcount over scraped estimates
- For funding, trust Crustdata's enrichment data (funding_stage, markets)
- For hiring signals, use both Crustdata job listings AND LinkedIn post intent signals
- For the "website" field, use the URL from the "crustdata" or "website" source. Never return null if a URL was found.

Return ONLY valid JSON:
{{
  "company_name": "...",
  "description": "...",
  "website": "...",
  "domain": "...",
  "linkedin_url": "...",
  "headcount": number or null,
  "headcount_confidence": 0.0-1.0,
  "funding_stage": "...",
  "funding_total": "...",
  "funding_confidence": 0.0-1.0,
  "hq_location": "...",
  "hq_country": "...",
  "year_founded": "...",
  "tech_stack": ["..."],
  "products": ["..."],
  "icp_score": 1-10,
  "icp_reasoning": "...",
  "crustdata_company_id": number or null,
  "signals": [
    {{"signal": "...", "source": "...", "urgency": "high/medium/low"}},
    ...5 signals total...
  ],
  "scores": {{
    "icp_fit": 1-10,
    "intent": 1-10,
    "budget": 1-10,
    "timing": 1-10,
    "reach": 1-10,
    "signal_strength": 1-10
  }}
}}"""

async def run_scout_agent(company_name: str, log_fn=None) -> dict:
    """Fire all 7 sources simultaneously (Crustdata + free sources) and fuse with LLM."""
    
    if log_fn:
        await log_fn(f"🔭 Scout: Firing 7 sources simultaneously for '{company_name}' (Crustdata + free sources)...")
    
    # Fire all sources at once — Crustdata sources + free sources (15s timeout per source)
    async def _with_timeout(coro, name, timeout=15):
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            return {"error": f"{name} timed out after {timeout}s", "confidence": 0}
        except Exception as e:
            return {"error": str(e), "confidence": 0}

    results = await asyncio.gather(
        _with_timeout(hit_crustdata(company_name), "crustdata"),
        _with_timeout(hit_newsapi(company_name), "newsapi"),
        _with_timeout(scrape_company_website(company_name), "website"),
        _with_timeout(scrape_linkedin_company(company_name), "linkedin"),
        _with_timeout(hit_github_api(company_name), "github"),
        _with_timeout(scrape_product_hunt(company_name), "producthunt"),
        _with_timeout(search_intent_signals(company_name), "intent_signals"),
    )
    
    source_names = ["crustdata", "newsapi", "website", "linkedin", "github", "producthunt", "intent_signals"]
    sources = {}
    for name, result in zip(source_names, results):
        if isinstance(result, dict):
            sources[name] = result
        else:
            sources[name] = {"error": str(result), "confidence": 0}
    
    if log_fn:
        live_sources = [k for k, v in sources.items() if not v.get("error")]
        crustdata_live = any(
            sources.get(s, {}).get("source", "").startswith("crustdata")
            for s in ["crustdata", "newsapi", "website", "linkedin", "intent_signals"]
            if not sources.get(s, {}).get("error")
        )
        api_label = "Crustdata API ✓" if crustdata_live else "free sources only"
        await log_fn(f"✅ Scout: {len(live_sources)}/7 sources responded ({api_label}): {', '.join(live_sources)}")
    
    # Fuse with LLM (run in thread to not block event loop)
    fusion_prompt = FUSION_PROMPT.format(
        company=company_name,
        num_sources=len([s for s in sources.values() if not s.get("error")]),
        sources_json=json.dumps(sources, indent=2, default=str)[:12000]
    )
    
    response = await asyncio.to_thread(lambda: invoke_llm_resilient([HumanMessage(content=fusion_prompt)], temperature=0.1))
    
    try:
        profile = json.loads(response.content)
        profile["raw_sources"] = sources
        if log_fn:
            await log_fn(f"🧠 Scout: ICP Score {profile.get('icp_score')}/10 | {len(profile.get('signals', []))} signals detected")
        return profile
    except json.JSONDecodeError:
        import re
        match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if match:
            profile = json.loads(match.group())
            profile["raw_sources"] = sources
            return profile
        return {"company_name": company_name, "error": "fusion_failed", "icp_score": 5, "signals": [], "raw_sources": sources}
