"""
scorer.py
ATS (Applicant Tracking System) resume scorer.
Compares a resume against a job description using:
  1. Keyword/skill overlap (TF-IDF cosine similarity)
  2. LLM deep analysis (structured JSON feedback)
"""

import json
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from agent.prompts import ATS_SCORE_PROMPT


# ── Quick cosine similarity score (no LLM cost) ─────────────────────

def quick_ats_score(resume_text: str, job_description: str) -> float:
    """
    Returns a 0-100 cosine similarity score between resume and JD.
    Fast and free — no API call required.
    """
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    try:
        tfidf = vectorizer.fit_transform([resume_text, job_description])
        score = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        return round(score * 100, 1)
    except Exception:
        return 0.0


# ── LLM-powered deep ATS analysis ───────────────────────────────────

def deep_ats_analysis(resume_text: str, job_description: str, llm: ChatOpenAI) -> dict:
    """
    Uses an LLM to produce a detailed ATS analysis with keyword gaps,
    skill matches, and actionable recommendations.

    Returns a dict with keys: overall_score, matched_keywords,
    missing_keywords, matched_skills, missing_skills,
    experience_match, education_match, recommendations, summary.
    """
    prompt = PromptTemplate(
        input_variables=["resume_text", "job_description"],
        template=ATS_SCORE_PROMPT
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    raw = chain.run(resume_text=resume_text[:4000], job_description=job_description[:3000]).strip()

    # Strip markdown fences
    if raw.startswith("```"):
        raw = re.sub(r"```[a-z]*\n?", "", raw).replace("```", "").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "overall_score": 0,
            "summary": "Could not parse ATS analysis.",
            "raw": raw
        }


# ── Score colour helper ──────────────────────────────────────────────

def score_colour(score: int) -> str:
    if score >= 75:
        return "🟢"
    elif score >= 50:
        return "🟡"
    else:
        return "🔴"
