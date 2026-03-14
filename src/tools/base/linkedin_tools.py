import os
import asyncio
from playwright.sync_api import sync_playwright
from src.utils import invoke_llm

def extract_linkedin_url_base(search_results):
    """
    Extracts the LinkedIn URL from the search results.
    """
    for result in search_results:
        if 'linkedin.com/in' in result['link']:
            return result['link']
    return ""


def extract_linkedin_url(search_results):
    EXTRACT_LINKEDIN_URL_PROMPT = """
    **Role:**  
    You are an expert in extracting LinkedIn URLs from Google search results, specializing in finding the correct personal LinkedIn URL.

    **Objective:**  
    From the provided search results, find the LinkedIn URL of a specific person working at a specific company.

    **Instructions:**  
    1. Output **only** the correct LinkedIn URL if found, nothing else.  
    2. If no valid URL exists, output **only** an empty string.  
    3. Only consider URLs with `"/in"`. Ignore those with `"/posts"` or `"/company"`.  
    """
    
    result = invoke_llm(
        system_prompt=EXTRACT_LINKEDIN_URL_PROMPT, 
        user_message=str(search_results),
        model="gemini-2.5-flash"
    )
    return result
    
    
def scrape_linkedin(linkedin_url, is_company=False):
    """
    Scrapes LinkedIn profile data using Playwright stealth (free, no RapidAPI needed).
    Returns a dict with key 'data' containing extracted profile fields.
    """
    try:
        from playwright_stealth import stealth_sync
    except ImportError:
        stealth_sync = None

    result = {}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            if stealth_sync:
                stealth_sync(page)
            page.goto(linkedin_url, timeout=15000)
            page.wait_for_timeout(2000)
            text = page.inner_text("body")
            browser.close()

        import re
        if is_company:
            result = {
                "data": {
                    "company_name": "",
                    "description": text[:500],
                    "year_founded": "",
                    "industries": [],
                    "specialties": "",
                    "employee_count": "",
                    "follower_count": 0,
                    "locations": []
                }
            }
            m = re.search(r'([\d,]+)\s+employees', text, re.IGNORECASE)
            if m:
                result["data"]["employee_count"] = m.group(0)
        else:
            result = {
                "data": {
                    "about": text[:400],
                    "full_name": "",
                    "location": "",
                    "city": "",
                    "country": "",
                    "skills": [],
                    "company": "",
                    "educations": [],
                    "experiences": []
                }
            }
    except Exception as e:
        print(f"LinkedIn scrape failed: {e}")

    return result
