# XeroD

XeroD is a hackathon project that combines two systems into one outbound-sales demo stack:

- NexusAI: an agentic sales intelligence workflow that researches a company, finds the best contact, writes a personalized outbound email, embeds a visual intelligence card, and sends the email automatically.
- Snap3D: a mobile-first single-image 3D reconstruction app that turns a product photo into a downloadable 3D model using a local AI model.

Built for c0mpiled x Magicball x Razorpay Hackathon, Bangalore, March 14, 2026.

## Executive Summary

Sales teams lose time on three expensive steps: account research, contact discovery, and personalization. XeroD automates that flow end to end.

With one company name, NexusAI gathers data from multiple sources, scores the account, identifies the most relevant decision-maker, generates two outbound email variants, selects the stronger one, builds an HTML intelligence card, and sends the email with a meeting CTA.

With one product photo, Snap3D generates a 3D model locally using TripoSR and provides a mobile interface for viewing, downloading, and sharing the result.

## What Is Included In This Repository

- NexusAI backend and agent pipeline in [src](src), [api/main.py](api/main.py), and [main.py](main.py)
- NexusAI web frontend in [frontend](frontend)
- Snap3D backend, frontend, and local 3D pipeline in [Snap3D](Snap3D)
- Demo data, caches, reports, and configuration files for hackathon execution

## Core Products

### 1. NexusAI

NexusAI is an autonomous B2B outbound workflow.

Input:
- Company name

Output:
- Researched company profile
- Best-fit decision-maker with confidence score
- Two email variants with scoring
- Winning subject line and email body
- Embedded HTML intelligence card
- Sent email with tracking record

### 2. Snap3D

Snap3D is a local single-image 3D reconstruction system.

Input:
- One product or object photo

Output:
- Generated 3D model file
- Preview image
- WebSocket progress events
- Interactive mobile viewer with download/share flow

## End-to-End Workflow

### NexusAI flow

```text
User enters company name
    -> Scout agent gathers 7 sources in parallel
    -> LLM fuses results into one company profile
    -> Finder agent selects ideal title and retrieves contact
    -> Writer agent creates and scores two emails
    -> Writer builds HTML intelligence card
    -> Closer sends multipart email through Gmail SMTP
    -> SQLite logs message metadata
```

### Snap3D flow

```text
User captures or uploads image
    -> Backend stores upload
    -> Background removal and alpha cleanup
    -> TripoSR local model performs reconstruction
    -> Mesh is exported as GLB
    -> Frontend displays live progress and 3D preview
```

## Detailed NexusAI Pipeline

### 1. Scout Agent

Implemented in [src/agents/scout.py](src/agents/scout.py).

The Scout agent fires seven research sources concurrently with per-source timeout handling:

- Crustdata
- NewsAPI
- Company website scraping
- LinkedIn company scraping
- GitHub discovery
- Product Hunt lookup
- Intent signal search

The raw responses are fused by an LLM into a single structured company profile with:

- Company description
- Website and domain
- Headcount and confidence
- Funding stage and confidence
- HQ location
- Product and tech stack summary
- ICP score
- Top buying signals
- Scoring dimensions such as intent, timing, budget, reach, and signal strength

### 2. Finder Agent

Implemented in [src/agents/finder.py](src/agents/finder.py).

The Finder agent chooses the most relevant persona based on company stage and headcount. The default logic is:

- Under 50 employees: founder or CEO
- 50 to 200 employees: VP Sales or Head of GTM
- 200+ employees: VP Sales or Director of Sales

It then looks up a real person and returns:

- Name
- Title
- Email
- LinkedIn URL
- Confidence percentage
- Reasoning

If no verified email is found, the system falls back to domain-based email pattern guessing.

### 3. Writer Agent

Implemented in [src/agents/writer.py](src/agents/writer.py).

The Writer agent creates two cold outbound variants:

- Variant A: benefit-led opener
- Variant B: signal-led opener

Each variant is scored on:

- Specificity
- Relevance
- CTA strength

The winning version becomes the final outbound email.

The same step also builds an HTML intelligence card containing:

- Company name
- Score bars
- Key signals
- Visual styling for email compatibility
- A meeting CTA button

### 4. Closer Agent

Implemented in [src/agents/closer.py](src/agents/closer.py).

The Closer agent handles actual email delivery.

What it does:

- Builds a multipart email with plain-text and HTML versions
- Inserts the generated email body into the HTML message
- Embeds the visual intelligence card inline inside the email body
- Adds a footer link to book a call
- Sends the email through Gmail SMTP using an app password
- Logs the send event to SQLite in `nexusai_sent.db`

Tracked fields include:

- Company
- Contact email
- Subject
- Generated message ID
- Winning variant
- Winning score
- Send timestamp

## How The Email Is Sent

This project already implements real email sending.

The exact send path is:

1. The Writer agent generates the winning subject line and body.
2. The Writer agent builds an HTML intelligence card.
3. The Closer agent creates a MIME multipart email.
4. The plain text version is included as fallback.
5. The HTML version includes:
     - the generated email copy
     - the intelligence card inline
     - a meeting footer link
6. Gmail SMTP over SSL is used to send the message.
7. The result is written into SQLite for tracking.

Meeting flow in the email:

- The email prompt forces a low-friction CTA that mentions 15 minutes.
- The HTML card includes a button labeled `Book 15-min Call`.
- The final footer includes a `Book a call` Calendly link.

## Important Product Accuracy Note

The current NexusAI mailer sends:

- personalized email copy
- embedded HTML intelligence card
- meeting CTA

The current Snap3D system generates the 3D model locally and exposes it through its own frontend/backend flow.

As the code stands today, the NexusAI mailer does not attach or inline the generated GLB model directly inside the outbound email. The 3D pipeline exists in the repository as a companion product workflow and can be used alongside the outbound demo.

Also note:

- Snap3D uses a local 3D reconstruction model, not a local LLM.
- NexusAI uses hosted LLM calls for reasoning and copy generation.

## Detailed Snap3D Pipeline

See [Snap3D/README.md](Snap3D/README.md) for the component-level overview.

Snap3D uses:

- FastAPI backend in [Snap3D/backend/main.py](Snap3D/backend/main.py)
- TripoSR processing pipeline in [Snap3D/backend/triposr_pipeline.py](Snap3D/backend/triposr_pipeline.py)
- React mobile frontend in [Snap3D/frontend](Snap3D/frontend)

The reconstruction path is:

1. Image upload
2. Background removal
3. Alpha cleanup
4. Local TripoSR inference
5. Mesh extraction
6. GLB export
7. Browser-based model viewing

## APIs

### NexusAI API

Defined in [api/main.py](api/main.py).

- `POST /run`: run the full pipeline for one company
- `POST /precache`: precompute results without sending email
- `GET /health`: health check and model/cache status
- `GET /credits`: check Crustdata credits
- `GET /cache`: list cached companies
- `GET /cache/{company}`: fetch cached company result
- `DELETE /cache`: clear cache
- `WS /ws/{session_id}`: real-time log stream

### Snap3D API

Defined in [Snap3D/backend/main.py](Snap3D/backend/main.py).

- `POST /upload`: upload image and trigger reconstruction
- `GET /health`: Snap3D service health
- `GET /models/list`: list generated models
- `GET /models/{filename}`: retrieve GLB model
- `GET /previews/{filename}`: retrieve preview image
- `WS /ws/{client_id}`: real-time processing progress

## Frontend Experience

### NexusAI frontend

The NexusAI frontend is a swipe-style web UI built in React. It displays:

- researched company profile
- top signals
- score bars
- decision-maker identity
- live log updates from the backend

### Snap3D frontend

The Snap3D frontend is a mobile-first PWA built for:

- camera capture
- server connection
- progress tracking
- model history
- 3D viewing and downloading

## Tech Stack

### NexusAI

- FastAPI
- LangGraph-style agent pipeline orchestration
- Pydantic
- Gmail SMTP
- SQLite
- WebSocket streaming
- React
- Framer Motion
- Tailwind CSS
- Crustdata and additional research sources

### AI and reasoning

- Hosted LLM usage through the project utilities for:
    - data fusion
    - persona selection
    - email generation
    - A/B scoring

### Snap3D

- FastAPI
- PyTorch
- TripoSR
- rembg
- trimesh
- React Three Fiber
- Drei
- Zustand
- Vite PWA

## Running The Project

## Configuration

NexusAI depends on environment variables for external data sources and outbound email.

Typical configuration includes:

- `CRUSTDATA_API_KEY`
- `NEWS_API_KEY` or equivalent news provider key
- LLM provider configuration used by the shared invocation utility
- `GMAIL_SENDER_EMAIL`
- `GMAIL_APP_PASSWORD`

Important send requirement:

- The current email sender in [src/agents/closer.py](src/agents/closer.py) uses Gmail SMTP with an app password.
- If `GMAIL_APP_PASSWORD` is not set, the pipeline still runs but email delivery is skipped or returns an explicit send error.

## Cache And Demo Behavior

The API uses two caching layers:

- in-memory cache for instant repeat requests in the same process
- local file cache for persistence across restarts

This supports the hackathon demo pattern:

- first run demonstrates the full research pipeline
- repeat run demonstrates near-instant retrieval and immediate send flow

### Root setup

```bash
pip install -r requirements.txt
```

### NexusAI backend

```bash
uvicorn api.main:app --reload --port 8000
```

### NexusAI frontend

```bash
cd frontend
npm install
npm run dev
```

### Snap3D backend

```bash
cd Snap3D/backend
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

### Snap3D frontend

```bash
cd Snap3D/frontend
npm install
npm run dev -- --host
```

## Demo Narrative

For judging, the strongest live story is:

1. Enter a company name.
2. Show research and signal extraction live.
3. Show the chosen decision-maker and confidence.
4. Show the generated winning email.
5. Send the email and confirm delivery.
6. Open the recipient inbox and show the intelligence card plus meeting CTA.
7. Show Snap3D generating the product's 3D asset locally from one photo.

## Ownership And Attribution

This workspace contains original XeroD hackathon integration work plus upstream open-source components.

- XeroD owns the hackathon-specific integration, orchestration, product workflow, and custom modifications made in this workspace.
- Snap3D includes upstream TripoSR-based components under MIT terms.
- Upstream rights remain with their original authors where applicable.

For Snap3D-specific attribution and rights notes, see [Snap3D/NOTICE.txt](Snap3D/NOTICE.txt) and [Snap3D/LICENSE](Snap3D/LICENSE).
