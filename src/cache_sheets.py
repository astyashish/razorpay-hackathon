"""
Google Sheets-based cache for NexusAI pipeline results.
Replaces Redis with persistent, shareable cache in Google Sheets.
"""
import json
import os
import time
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from src.utils import get_google_credentials

CACHE_SHEET_ID = os.getenv("SHEET_ID")
CACHE_SHEET_NAME = "NexusAI_Cache"
CACHE_TTL_SECONDS = 86400  # 24 hours


def _get_sheets_service():
    creds = get_google_credentials()
    return build("sheets", "v4", credentials=creds)


def _ensure_cache_sheet(service):
    """Create the cache sheet tab if it doesn't exist."""
    try:
        meta = service.spreadsheets().get(spreadsheetId=CACHE_SHEET_ID).execute()
        existing = [s["properties"]["title"] for s in meta.get("sheets", [])]
        if CACHE_SHEET_NAME not in existing:
            service.spreadsheets().batchUpdate(
                spreadsheetId=CACHE_SHEET_ID,
                body={"requests": [{"addSheet": {"properties": {"title": CACHE_SHEET_NAME}}}]}
            ).execute()
            # Add header row
            service.spreadsheets().values().update(
                spreadsheetId=CACHE_SHEET_ID,
                range=f"{CACHE_SHEET_NAME}!A1:F1",
                valueInputOption="RAW",
                body={"values": [["company_key", "company_name", "profile_json", "contact_json", "email_json", "cached_at"]]}
            ).execute()
    except HttpError as e:
        print(f"⚠️ Cache sheet setup error: {e}")
        raise


def get_cached_result(company: str) -> dict | None:
    """Look up cached pipeline result from Google Sheets. Returns None if miss or expired."""
    if not CACHE_SHEET_ID:
        return None
    try:
        service = _get_sheets_service()
        _ensure_cache_sheet(service)
        result = service.spreadsheets().values().get(
            spreadsheetId=CACHE_SHEET_ID,
            range=f"{CACHE_SHEET_NAME}!A:F"
        ).execute()
        rows = result.get("values", [])
        key = company.strip().lower()
        for row in rows[1:]:  # skip header
            if len(row) >= 6 and row[0] == key:
                cached_at = float(row[5])
                if time.time() - cached_at < CACHE_TTL_SECONDS:
                    return {
                        "profile": json.loads(row[2]),
                        "contact": json.loads(row[3]),
                        "email": json.loads(row[4]),
                    }
                # Expired — still return None, will be overwritten
                return None
        return None
    except Exception as e:
        print(f"⚠️ Cache read error: {e}")
        return None


def save_to_cache(company: str, profile: dict, contact: dict, email: dict):
    """Save pipeline result to Google Sheets cache."""
    if not CACHE_SHEET_ID:
        return
    try:
        service = _get_sheets_service()
        _ensure_cache_sheet(service)

        key = company.strip().lower()
        now = str(time.time())

        # Check if row already exists for this company — update it
        result = service.spreadsheets().values().get(
            spreadsheetId=CACHE_SHEET_ID,
            range=f"{CACHE_SHEET_NAME}!A:A"
        ).execute()
        rows = result.get("values", [])
        row_idx = None
        for i, row in enumerate(rows):
            if row and row[0] == key:
                row_idx = i + 1  # 1-indexed for Sheets API
                break

        new_row = [
            key,
            company,
            json.dumps(profile, default=str),
            json.dumps(contact, default=str),
            json.dumps(email, default=str),
            now,
        ]

        if row_idx:
            # Update existing row
            service.spreadsheets().values().update(
                spreadsheetId=CACHE_SHEET_ID,
                range=f"{CACHE_SHEET_NAME}!A{row_idx}:F{row_idx}",
                valueInputOption="RAW",
                body={"values": [new_row]}
            ).execute()
        else:
            # Append new row
            service.spreadsheets().values().append(
                spreadsheetId=CACHE_SHEET_ID,
                range=f"{CACHE_SHEET_NAME}!A:F",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": [new_row]}
            ).execute()
    except Exception as e:
        print(f"⚠️ Cache write error: {e}")


def list_cached_companies() -> list[dict]:
    """Return list of cached companies with timestamps."""
    if not CACHE_SHEET_ID:
        return []
    try:
        service = _get_sheets_service()
        _ensure_cache_sheet(service)
        result = service.spreadsheets().values().get(
            spreadsheetId=CACHE_SHEET_ID,
            range=f"{CACHE_SHEET_NAME}!A:F"
        ).execute()
        rows = result.get("values", [])
        companies = []
        for row in rows[1:]:
            if len(row) >= 6:
                cached_at = float(row[5])
                expired = time.time() - cached_at >= CACHE_TTL_SECONDS
                companies.append({
                    "company_key": row[0],
                    "company_name": row[1],
                    "cached_at": datetime.fromtimestamp(cached_at).isoformat(),
                    "expired": expired,
                })
        return companies
    except Exception as e:
        print(f"⚠️ Cache list error: {e}")
        return []


def clear_cache():
    """Clear all cached data (keep header)."""
    if not CACHE_SHEET_ID:
        return
    try:
        service = _get_sheets_service()
        result = service.spreadsheets().values().get(
            spreadsheetId=CACHE_SHEET_ID,
            range=f"{CACHE_SHEET_NAME}!A:A"
        ).execute()
        rows = result.get("values", [])
        if len(rows) > 1:
            service.spreadsheets().values().clear(
                spreadsheetId=CACHE_SHEET_ID,
                range=f"{CACHE_SHEET_NAME}!A2:F{len(rows)}",
                body={}
            ).execute()
    except Exception as e:
        print(f"⚠️ Cache clear error: {e}")
