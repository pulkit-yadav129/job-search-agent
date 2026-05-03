"""
tools.py
LangChain @tool definitions for all job board integrations.
Sources: Google Jobs (SerpAPI), JSearch (LinkedIn/Indeed/Glassdoor),
         Naukri (RapidAPI), LinkedIn Jobs (RapidAPI).
"""

import os
import requests
from langchain.tools import tool

SERPAPI_KEY        = os.getenv("SERPAPI_KEY", "")
JSEARCH_KEY        = os.getenv("JSEARCH_RAPIDAPI_KEY", "")
NAUKRI_KEY         = os.getenv("NAUKRI_RAPIDAPI_KEY", "")
LINKEDIN_KEY       = os.getenv("LINKEDIN_RAPIDAPI_KEY", "")


# ── Helper ──────────────────────────────────────────────────────────

def _safe_get(url: str, params: dict = None, headers: dict = None) -> dict:
    try:
        r = requests.get(url, params=params, headers=headers, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# ── Tool 1: Google Jobs via SerpAPI ─────────────────────────────────

@tool
def search_google_jobs(query: str) -> str:
    """
    Search Google Jobs via SerpAPI.
    Input: a job search query string, e.g. 'Senior Python Developer remote'.
    Returns formatted job listings.
    """
    if not SERPAPI_KEY:
        return "SerpAPI key not configured."

    data = _safe_get(
        "https://serpapi.com/search",
        params={"engine": "google_jobs", "q": query, "api_key": SERPAPI_KEY, "num": 10}
    )
    jobs = data.get("jobs_results", [])
    if not jobs:
        return f"No Google Jobs results for: {query}"

    out = []
    for j in jobs[:8]:
        ext = j.get("detected_extensions", {})
        link = (j.get("related_links") or [{}])[0].get("link", "N/A")
        out.append(
            f"[Google Jobs] **{j.get('title')}** @ {j.get('company_name')}\n"
            f"📍 {j.get('location')} | Posted: {ext.get('posted_at','N/A')} | "
            f"Type: {ext.get('schedule_type','N/A')}\n"
            f"🔗 {link}\n"
            f"📝 {j.get('description','')[:250]}...\n"
        )
    return "\n---\n".join(out)


# ── Tool 2: JSearch — LinkedIn / Indeed / Glassdoor ─────────────────

@tool
def search_jsearch(query: str) -> str:
    """
    Search jobs aggregated from LinkedIn, Indeed, and Glassdoor via JSearch (RapidAPI).
    Input: a job search query string, e.g. 'Data Scientist New York'.
    Returns formatted job listings.
    """
    if not JSEARCH_KEY:
        return "JSearch RapidAPI key not configured."

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
        remote = "🌐 Remote" if j.get("job_is_remote") else f"📍 {j.get('job_city','')}, {j.get('job_country','')}"
        out.append(
            f"[{j.get('job_publisher','JSearch')}] **{j.get('job_title')}** @ {j.get('employer_name')}\n"
            f"{remote} | Posted: {j.get('job_posted_at_datetime_utc','N/A')[:10]}\n"
            f"🔗 {j.get('job_apply_link','N/A')}\n"
            f"📝 {j.get('job_description','')[:250]}...\n"
        )
    return "\n---\n".join(out)


# ── Tool 3: Naukri via RapidAPI ──────────────────────────────────────

@tool
def search_naukri(query: str) -> str:
    """
    Search Naukri.com jobs via RapidAPI.
    Best for India-based job searches.
    Input: job search query, e.g. 'React Developer Bangalore'.
    """
    if not NAUKRI_KEY:
        return "Naukri RapidAPI key not configured."

    # RapidAPI Naukri endpoint (naukri-com1.p.rapidapi.com)
    data = _safe_get(
        "https://naukri-com1.p.rapidapi.com/search",
        params={"keyword": query, "location": "", "experience": ""},
        headers={
            "X-RapidAPI-Key": NAUKRI_KEY,
            "X-RapidAPI-Host": "naukri-com1.p.rapidapi.com"
        }
    )

    jobs = data.get("jobDetails", data.get("data", []))
    if not jobs:
        return f"No Naukri results for: {query}"

    out = []
    for j in jobs[:8]:
        out.append(
            f"[Naukri] **{j.get('title', j.get('jobTitle', 'N/A'))}** "
            f"@ {j.get('companyName', 'N/A')}\n"
            f"📍 {j.get('location', 'N/A')} | "
            f"Exp: {j.get('experience', 'N/A')} | "
            f"Salary: {j.get('salary', 'Not disclosed')}\n"
            f"🔗 {j.get('jdURL', j.get('applyLink', 'N/A'))}\n"
            f"📝 {str(j.get('jobDescription', j.get('description', '')))[:250]}...\n"
        )
    return "\n---\n".join(out)


# ── Tool 4: LinkedIn Jobs via RapidAPI ───────────────────────────────

@tool
def search_linkedin_jobs(query: str) -> str:
    """
    Search LinkedIn Jobs via RapidAPI (linkedin-jobs-search.p.rapidapi.com).
    Input: a job search query, e.g. 'Machine Learning Engineer London'.
    """
    if not LINKEDIN_KEY:
        return "LinkedIn RapidAPI key not configured."

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

    # Response is a list directly
    jobs = data if isinstance(data, list) else data.get("data", [])
    if not jobs:
        return f"No LinkedIn results for: {query}"

    out = []
    for j in jobs[:8]:
        out.append(
            f"[LinkedIn] **{j.get('job_title', 'N/A')}** @ {j.get('company_name', 'N/A')}\n"
            f"📍 {j.get('job_location', 'N/A')} | "
            f"Type: {j.get('job_type', 'N/A')} | "
            f"Posted: {j.get('posted_date', 'N/A')}\n"
            f"🔗 {j.get('linkedin_job_url_cleaned', j.get('job_url', 'N/A'))}\n"
            f"📝 {str(j.get('job_description', ''))[:250]}...\n"
        )
    return "\n---\n".join(out)


# ── All tools list ───────────────────────────────────────────────────
ALL_TOOLS = [search_google_jobs, search_jsearch, search_naukri, search_linkedin_jobs]