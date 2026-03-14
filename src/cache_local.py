"""
Local JSON file cache for NexusAI pipeline results.
No OAuth, no external services — just fast local disk I/O.
"""
import json
import os
import time
from datetime import datetime

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "pipeline_cache.json")
CACHE_TTL_SECONDS = 86400  # 24 hours


def _load_cache() -> dict:
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save_cache(data: dict):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, default=str, ensure_ascii=False)


def get_cached_result(company: str) -> dict | None:
    """Look up cached pipeline result. Returns None on miss or expired."""
    cache = _load_cache()
    key = company.strip().lower()
    entry = cache.get(key)
    if not entry:
        return None
    cached_at = entry.get("cached_at", 0)
    if time.time() - cached_at >= CACHE_TTL_SECONDS:
        return None
    return {
        "profile": entry.get("profile", {}),
        "contact": entry.get("contact", {}),
        "email": entry.get("email", {}),
    }


def save_to_cache(company: str, profile: dict, contact: dict, email: dict):
    """Save pipeline result to local JSON cache."""
    cache = _load_cache()
    key = company.strip().lower()
    cache[key] = {
        "company_name": company,
        "profile": profile,
        "contact": contact,
        "email": email,
        "cached_at": time.time(),
    }
    _save_cache(cache)


def list_cached_companies() -> list[dict]:
    """Return list of cached companies with timestamps."""
    cache = _load_cache()
    result = []
    for key, entry in cache.items():
        cached_at = entry.get("cached_at", 0)
        expired = time.time() - cached_at >= CACHE_TTL_SECONDS
        result.append({
            "company_key": key,
            "company_name": entry.get("company_name", key),
            "cached_at": datetime.fromtimestamp(cached_at).isoformat(),
            "expired": expired,
        })
    return result


def clear_cache():
    """Clear all cached data."""
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
