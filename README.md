# NexusAI - Agentic Sales Intelligence Platform

> Type a company name. Get a researched profile, a verified contact, a scored A/B email, and a visual HTML pitch card in their inbox. Zero human steps.

**Built for: c0mpiled x Magicball x Razorpay Hackathon | Bangalore | March 14, 2026**

## Architecture

```
Input: "Unsiloed AI"
    |
Scout Agent -> asyncio.gather(Crustdata + NewsAPI + Crawl4AI + LinkedIn + GitHub + ProductHunt)
    | Claude fuses 6 sources -> ICP score + 5 signals + confidence %
Finder Agent -> Claude picks title -> LinkedIn RapidAPI -> Hunter.io email verify
    | { name, title, email, confidence_pct }
Writer Agent -> Claude generates Variant A + Variant B -> scores both -> picks winner
           -> Claude generates visual HTML card (SVG radar + bar charts, inline styles)
    | { best_email, best_subject, html_card, winner_reasoning }
Closer Agent -> Gmail API -> embeds HTML card in email body -> sends -> SQLite tracking
    | { sent: true, message_id }
```

## Setup (run these in order tonight)

```bash
# 1. Install Python deps
pip install -r requirements.txt

# 2. Install browsers
playwright install chromium
crawl4ai-setup

# 3. Set up environment
cp .env.example .env
# Fill in all API keys in .env

# 4. Set up Gmail OAuth
# Put credentials.json in root (from Google Cloud Console)
# Run once: python -c "from src.agents.closer import get_gmail_creds; get_gmail_creds()"

# 5. Start Redis
redis-server

# 6. PRE-CACHE DEMO TARGETS (CRITICAL - do this tonight)
python precache.py

# 7. Start backend
uvicorn api.main:app --reload --port 8000

# 8. Start frontend
cd frontend && npm install && npm run dev
```

## Demo Strategy

Type "Unsiloed AI" live -> loads from cache in 2 seconds -> email sends -> judge's phone buzzes.

## Judges

Unsiloed AI, Crustdata, Razorpay, Safedep, S2.dev, Emergent, Concierge

## Tech Stack

- **LangGraph** - 4-agent pipeline (Scout -> Finder -> Writer -> Closer)
- **Claude 3.5 Sonnet** - data fusion, email writing, HTML card generation
- **Crawl4AI + Playwright** - stealth web scraping
- **FastAPI + WebSocket** - real-time log streaming
- **Redis** - sub-2s cached demo loads
- **React + Framer Motion + Tailwind** - swipe-card UI
- **Gmail API** - send with embedded HTML cards
