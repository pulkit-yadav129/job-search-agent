"""
tools.py
LangChain @tool definitions for all job board integrations.
"""

import os
import requests
from langchain.tools import tool


# ── Helper ──────────────────────────────────────────────────────────

def _safe_get(url: str, params: dict = None, headers: dict = None) -> dict:
    try:
        r = requests.get(url, params=params, headers=headers, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def _safe_slice(val, length=250):
    if not isinstance(val, str):
        return ""
    return val[:length]


# ── Tool 1: Google Jobs ─────────────────────────────────────────────

@tool
def search_google_jobs(query: str) -> str:
    """Search Google Jobs via SerpAPI using a query string."""
    SERPAPI_KEY = os.getenv("SERPAPI_KEY")

    if not SERPAPI_KEY:
        raise ValueError("SerpAPI key not configured.")

    data = _safe_get(
        "https://serpapi.com/search",
        params={"engine": "google_jobs", "q": query, "api_key": SERPAPI_KEY, "num": 10}
    )

    jobs = data.get("jobs_results", [])
    if not jobs:
        return f"No Google Jobs results for: {query}"

    out = []
    for j in jobs[:8]:
        ext = j.get("detected_extensions", {}) or {}
        link = (j.get("related_links") or [{}])[0].get("link", "N/A")

        desc = _safe_slice(j.get("description"))

        out.append(
            f"[Google Jobs] **{j.get('title','N/A')}** @ {j.get('company_name','N/A')}\n"
            f"📍 {j.get('location','N/A')} | Posted: {ext.get('posted_at','N/A')} | "
            f"Type: {ext.get('schedule_type','N/A')}\n"
            f"🔗 {link}\n"
            f"📝 {desc}...\n"
        )

    return "\n---\n".join(out)


# ── Tool 2: JSearch ────────────────────────────────────────────────

@tool
def search_jsearch(query: str) -> str:
    """Search jobs from LinkedIn, Indeed, Glassdoor via JSearch (RapidAPI)."""
    JSEARCH_KEY = os.getenv("JSEARCH_RAPIDAPI_KEY")

    if not JSEARCH_KEY:
        raise ValueError("JSearch RapidAPI key not configured.")

    data = _safe_get(
        "https://jsearch.p.rapidapi.com/search",
        params={"query": query, "page": "1", "num_pages": "2"},
        headers={
            "X-RapidAPI-Key": JSEARCH_KEY,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }
    )

    jobs = data.get("data", [])
    if not jobs:
        return f"No JSearch results for: {query}"

    out = []
    for j in jobs[:8]:
        remote = (
            "🌐 Remote"
            if j.get("job_is_remote")
            else f"📍 {j.get('job_city','')}, {j.get('job_country','')}"
        )

        # ✅ SAFE DATE HANDLING (fixes your crash)
        posted = j.get("job_posted_at_datetime_utc") or "N/A"
        posted = posted[:10] if isinstance(posted, str) else "N/A"

        desc = _safe_slice(j.get("job_description"))

        out.append(
            f"[{j.get('job_publisher','JSearch')}] **{j.get('job_title','N/A')}** @ {j.get('employer_name','N/A')}\n"
            f"{remote} | Posted: {posted}\n"
            f"🔗 {j.get('job_apply_link','N/A')}\n"
            f"📝 {desc}...\n"
        )

    return "\n---\n".join(out)


# ── Tool 3: LinkedIn ───────────────────────────────────────────────

@tool
def search_linkedin_jobs(query: str) -> str:
    """Search LinkedIn Jobs via RapidAPI using a query string."""
    LINKEDIN_KEY = os.getenv("LINKEDIN_RAPIDAPI_KEY")

    if not LINKEDIN_KEY:
        raise ValueError("LinkedIn RapidAPI key not configured.")

    data = _safe_get(
        "https://linkedin-jobs-search.p.rapidapi.com/",
        params={
            "search_terms": query,
            "location": "",
            "page": "1"
        },
        headers={
            "X-RapidAPI-Key": LINKEDIN_KEY,
            "X-RapidAPI-Host": "linkedin-jobs-search.p.rapidapi.com"
        }
    )

    jobs = data if isinstance(data, list) else data.get("data", [])
    if not jobs:
        return f"No LinkedIn results for: {query}"

    out = []
    for j in jobs[:8]:
        desc = _safe_slice(j.get("job_description"))

        out.append(
            f"[LinkedIn] **{j.get('job_title', 'N/A')}** @ {j.get('company_name', 'N/A')}\n"
            f"📍 {j.get('job_location', 'N/A')} | "
            f"Type: {j.get('job_type', 'N/A')} | "
            f"Posted: {j.get('posted_date', 'N/A')}\n"
            f"🔗 {j.get('linkedin_job_url_cleaned', j.get('job_url', 'N/A'))}\n"
            f"📝 {desc}...\n"
        )

    return "\n---\n".join(out)


# ── All tools ──────────────────────────────────────────────────────

ALL_TOOLS = [search_google_jobs, search_jsearch, search_linkedin_jobs]