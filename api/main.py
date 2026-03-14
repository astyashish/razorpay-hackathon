import asyncio
import json
import os
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv(override=True)

from src.graph_nexus import build_nexus_graph
from src.cache_local import get_cached_result, save_to_cache, list_cached_companies, clear_cache

app = FastAPI(title="NexusAI API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Global log queues per session
log_queues: dict[str, asyncio.Queue] = {}

# In-memory cache for instant repeat lookups within same server session
_mem_cache: dict[str, dict] = {}

class RunRequest(BaseModel):
    company: str
    session_id: str = "default"
    send_email: bool = True

class BatchRequest(BaseModel):
    companies: list[str]
    session_id: str = "default"

@app.post("/run")
async def run_pipeline(req: RunRequest):
    """Main endpoint — runs full 4-agent pipeline for a company."""
    start_time = time.time()
    company_key = req.company.strip().lower()
    
    # 1. Check in-memory cache first (instant)
    if company_key in _mem_cache:
        data = _mem_cache[company_key]
        if req.session_id in log_queues:
            await log_queues[req.session_id].put({
                "message": f"⚡ Memory cache hit for '{req.company}' — loaded in {time.time()-start_time:.1f}s"
            })
        return {"status": "success", "cached": True, "data": data}
    
    # 2. Check local file cache (persistent across restarts)
    try:
        cached = get_cached_result(req.company)
        if cached:
            _mem_cache[company_key] = cached  # promote to memory
            if req.session_id in log_queues:
                await log_queues[req.session_id].put({
                    "message": f"⚡ Cache hit for '{req.company}' — loaded in {time.time()-start_time:.1f}s"
                })
            return {"status": "success", "cached": True, "data": cached}
    except Exception:
        pass
    
    # Set up log queue for this session
    log_queues[req.session_id] = asyncio.Queue()
    
    async def log_fn(msg: str):
        if req.session_id in log_queues:
            await log_queues[req.session_id].put({"message": msg})
    
    try:
        # Build and run the LangGraph pipeline
        from src.agents.scout import run_scout_agent
        from src.agents.finder import run_finder_agent
        from src.agents.writer import run_writer_agent
        from src.agents.closer import run_closer_agent
        
        profile = await run_scout_agent(req.company, log_fn)
        contact = await run_finder_agent(profile, log_fn)
        email_content = await run_writer_agent(profile, contact, log_fn)
        
        send_result = {"sent": False, "skipped": True}
        if req.send_email and contact.get("email"):
            send_result = await run_closer_agent(contact, email_content, profile, log_fn)
        
        output = {
            "profile": profile,
            "contact": contact,
            "email": email_content,
            "send_result": send_result
        }
        # Cache result in memory + local file
        _mem_cache[company_key] = output
        try:
            save_to_cache(req.company, profile, contact, email_content)
        except Exception:
            pass
        
        elapsed = time.time() - start_time
        await log_fn(f"🏁 Pipeline complete! ({elapsed:.1f}s)")
        if req.session_id in log_queues:
            await log_queues[req.session_id].put({"type": "done"})
        
        return {"status": "success", "cached": False, "data": output}
        
    except Exception as e:
        err = str(e)
        if "429" in err or "RESOURCE_EXHAUSTED" in err:
            friendly = "Gemini free-tier quota reached for today. Wait a few minutes and try again, or set GEMINI_MODEL=gemini-1.5-flash-8b in .env for a separate quota pool."
            await log_fn(f"⚠️ Rate limit: {friendly}")
            raise HTTPException(status_code=429, detail=friendly)
        await log_fn(f"❌ Pipeline error: {err}")
        raise HTTPException(status_code=500, detail=err)

@app.websocket("/ws/{session_id}")
async def websocket_log_stream(websocket: WebSocket, session_id: str):
    """Stream live logs to frontend."""
    await websocket.accept()
    
    if session_id not in log_queues:
        log_queues[session_id] = asyncio.Queue()
    
    try:
        while True:
            try:
                msg = await asyncio.wait_for(log_queues[session_id].get(), timeout=60.0)
                await websocket.send_json(msg)
                if msg.get("type") == "done":
                    break
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    finally:
        if session_id in log_queues:
            del log_queues[session_id]

@app.get("/health")
async def health():
    has_crustdata = bool(os.getenv("CRUSTDATA_API_KEY", ""))
    return {"status": "ok", "cache": "local_json", "crustdata_api": has_crustdata, "model": os.getenv("GEMINI_MODEL", "gemini-2.0-flash")}

@app.get("/credits")
async def crustdata_credits():
    """Check remaining Crustdata API credits."""
    try:
        from src.crustdata_client import get_remaining_credits
        result = await get_remaining_credits()
        return {"status": "ok", "credits": result.get("credits")}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/cache/{company}")
async def get_cache(company: str):
    """Get cached result for a company (memory → file)."""
    key = company.strip().lower()
    if key in _mem_cache:
        return _mem_cache[key]
    cached = get_cached_result(company)
    if cached:
        _mem_cache[key] = cached
        return cached
    raise HTTPException(status_code=404, detail="Not cached")

@app.get("/cache")
async def list_cache():
    """List all cached companies."""
    return list_cached_companies()

@app.delete("/cache")
async def delete_cache():
    """Clear all cache (memory + file)."""
    _mem_cache.clear()
    clear_cache()
    return {"status": "cleared"}

@app.post("/precache")
async def precache_companies(req: BatchRequest):
    """Pre-cache data for a batch of companies (runs Scout+Finder+Writer, no email send).
    Returns immediately with a session_id to track progress via WebSocket."""
    from src.agents.scout import run_scout_agent
    from src.agents.finder import run_finder_agent
    from src.agents.writer import run_writer_agent

    log_queues[req.session_id] = asyncio.Queue()

    async def log_fn(msg: str):
        if req.session_id in log_queues:
            await log_queues[req.session_id].put({"message": msg})

    results = {}
    for company in req.companies:
        key = company.strip().lower()
        # Skip if already cached
        if key in _mem_cache:
            await log_fn(f"⚡ {company} — already cached, skipping")
            results[company] = "cached"
            continue
        cached = get_cached_result(company)
        if cached:
            _mem_cache[key] = cached
            await log_fn(f"⚡ {company} — found in cache, skipping")
            results[company] = "cached"
            continue

        try:
            await log_fn(f"🔄 Pre-caching: {company}...")
            profile = await run_scout_agent(company, log_fn)
            contact = await run_finder_agent(profile, log_fn)
            email_content = await run_writer_agent(profile, contact, log_fn)
            output = {"profile": profile, "contact": contact, "email": email_content, "send_result": {"sent": False, "skipped": True}}
            _mem_cache[key] = output
            try:
                save_to_cache(company, profile, contact, email_content)
            except Exception:
                pass
            await log_fn(f"✅ {company} — pre-cached successfully!")
            results[company] = "success"
        except Exception as e:
            await log_fn(f"❌ {company} — failed: {str(e)[:100]}")
            results[company] = f"error: {str(e)[:100]}"

    if req.session_id in log_queues:
        await log_queues[req.session_id].put({"type": "done"})

    return {"status": "complete", "results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
