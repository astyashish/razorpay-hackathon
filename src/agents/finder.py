import asyncio
import os
import json
import re
from langchain_core.messages import HumanMessage
from src.utils import invoke_llm_resilient
from src.scrapers.linkedin_stealth import find_decision_maker_linkedin
from src.crustdata_client import enrich_person

PICKER_PROMPT = """Given this company profile, who is the SINGLE BEST person to cold email for a B2B sales outreach?

Company: {company_name}
Stage: {funding_stage}
Headcount: {headcount}
Signals: {signals}

Rules:
- Startup (< 50 people): email the Founder/CEO directly
- Growth (50-200): email VP Sales or Head of GTM  
- Scale (200+): email VP Sales or Director of Sales

Return JSON:
{{
  "first_name": "...",
  "last_name": "...",
  "title": "...",
  "reasoning": "why this person"
}}"""

async def run_finder_agent(profile: dict, log_fn=None) -> dict:
    """
    Find best decision-maker using Crustdata People Search + Enrichment.
    Pipeline:
      1. LLM picks ideal title based on company stage
      2. Crustdata People Search finds real people by company + title
      3. Crustdata People Enrich verifies email, gets full profile
      4. Falls back to pattern guessing only if API returns no email
    """
    
    company_name = profile.get("company_name", "")
    if log_fn:
        await log_fn(f"🎯 Finder: Identifying best decision-maker for {company_name} (Crustdata People API)...")
    
    # Step 1: LLM picks the right title based on company stage
    picker_prompt = PICKER_PROMPT.format(
        company_name=company_name,
        funding_stage=profile.get("funding_stage", "unknown"),
        headcount=profile.get("headcount", "unknown"),
        signals=json.dumps(profile.get("signals", [])[:3])
    )
    
    response = await asyncio.to_thread(lambda: invoke_llm_resilient([HumanMessage(content=picker_prompt)], temperature=0))
    try:
        match = re.search(r'\{.*\}', response.content, re.DOTALL)
        target = json.loads(match.group()) if match else {"first_name": "", "last_name": "", "title": "CEO", "reasoning": "default"}
    except Exception:
        target = {"first_name": "", "last_name": "", "title": "CEO", "reasoning": "default"}
    
    if log_fn:
        await log_fn(f"🎯 Finder: Targeting {target['title']} — {target['reasoning']}")
    
    # Step 2: Find actual person via Crustdata People Search
    titles_to_try = [target["title"], "CEO", "Founder", "VP Sales", "Head of Growth"]
    # Remove duplicates while preserving order
    seen = set()
    unique_titles = []
    for t in titles_to_try:
        if t.lower() not in seen:
            seen.add(t.lower())
            unique_titles.append(t)

    linkedin_result = await find_decision_maker_linkedin(company_name, unique_titles)
    
    name = linkedin_result.get("name", "")
    title = linkedin_result.get("title") or target.get("title", "CEO")
    linkedin_url = linkedin_result.get("linkedin_url", "")
    crustdata_email = linkedin_result.get("email")  # May already have verified email from Crustdata

    # Reject placeholder names that the LLM sometimes returns as templates
    if not name or re.search(r'\[.*?\]', name) or len(name) > 60:
        name = ""

    # Step 3: If we have a LinkedIn URL but no email, try Crustdata Person Enrich
    if linkedin_url and not crustdata_email:
        try:
            enriched = await enrich_person(linkedin_profile_url=linkedin_url)
            if isinstance(enriched, list) and enriched:
                enriched = enriched[0]
            if isinstance(enriched, dict):
                crustdata_email = enriched.get("email")
                if not name:
                    name = enriched.get("name", "")
                if enriched.get("title"):
                    title = enriched["title"]
        except Exception:
            pass

    # Step 4: Determine email and confidence
    email = None
    confidence_pct = 0
    email_source = "none"

    if crustdata_email:
        # Crustdata verified email — high confidence
        email = crustdata_email
        confidence_pct = 90
        email_source = "crustdata_verified"
    else:
        # Fallback: pattern guessing from domain
        raw_url = profile.get("raw_sources", {}).get("website", {}).get("url", "")
        website = profile.get("website") or profile.get("domain") or raw_url
        domain = website.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
        if not domain:
            domain = company_name.lower().replace(" ", "").replace(".", "") + ".com"
        
        if domain and name:
            name_parts = name.lower().split()
            alpha_parts = [re.sub(r'[^a-z]', '', p) for p in name_parts if re.sub(r'[^a-z]', '', p)]
            if len(alpha_parts) >= 2:
                email = f"{alpha_parts[0]}.{alpha_parts[-1]}@{domain}"
                confidence_pct = 45
                email_source = "pattern_guess"
            elif alpha_parts:
                email = f"{alpha_parts[0]}@{domain}"
                confidence_pct = 30
                email_source = "pattern_guess"

    # Build domain from profile data
    raw_url = profile.get("raw_sources", {}).get("website", {}).get("url", "")
    website = profile.get("website") or profile.get("domain") or raw_url
    domain = website.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0] if website else ""
    if not domain:
        domain = company_name.lower().replace(" ", "").replace(".", "") + ".com"

    result = {
        "name": name or f"Head of Growth at {company_name}",
        "title": title,
        "email": email,
        "email_source": email_source,
        "domain": domain,
        "confidence_pct": confidence_pct,
        "linkedin_url": linkedin_url,
        "reasoning": target.get("reasoning", "Best fit for ICP"),
    }

    if log_fn:
        source_label = f"Crustdata verified ✓" if email_source == "crustdata_verified" else "pattern guess"
        await log_fn(f"✅ Finder: {result['name']} ({result['title']}) — {result['email']} ({confidence_pct}% {source_label})")

    return result
