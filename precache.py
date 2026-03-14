"""
Pre-cache companies for fast demo loading.
Runs the full Scout→Finder→Writer pipeline and saves results to Google Sheets.
"""
import asyncio
import json
import os
from dotenv import load_dotenv

load_dotenv()

from src.agents.scout import run_scout_agent
from src.agents.finder import run_finder_agent
from src.agents.writer import run_writer_agent
from src.cache_sheets import get_cached_result, save_to_cache

DEMO_TARGETS = [
    "Unsiloed AI",
    "Crustdata",
    "Razorpay",
    "Safedep",
    "S2.dev"
]

async def precache():
    for company in DEMO_TARGETS:
        print(f"\n{'='*50}")
        print(f"Pre-caching: {company}")
        print('='*50)
        
        # Skip if already cached
        cached = get_cached_result(company)
        if cached:
            print(f"  ⚡ Already cached — skipping")
            continue
        
        try:
            async def log(msg):
                print(f"  {msg}")
            
            profile = await run_scout_agent(company, log)
            contact = await run_finder_agent(profile, log)
            email_content = await run_writer_agent(profile, contact, log)
            
            save_to_cache(company, profile, contact, email_content)
            
            print(f"  ✅ {company} cached to Google Sheets!")
            print(f"     ICP Score: {profile.get('icp_score')}/10")
            print(f"     Contact: {contact.get('name')} ({contact.get('email')})")
            print(f"     Email winner: Variant {email_content.get('winner', '?').upper()}")
            
        except Exception as e:
            print(f"  ❌ Failed to cache {company}: {e}")
    
    print(f"\n{'='*50}")
    print("Pre-caching complete! All targets saved to Google Sheets.")

if __name__ == "__main__":
    asyncio.run(precache())
