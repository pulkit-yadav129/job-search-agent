"""
input_parser.py
Uses an LLM to extract a structured job-seeker profile from any free-form input.
"""

import json
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain


PROFILE_EXTRACTION_PROMPT = """
You are a career advisor AI. Extract a structured job seeker profile from the input below.
Return ONLY valid JSON — no markdown, no explanation — with exactly these keys:

{{
  "job_titles": ["list of desired or relevant job titles"],
  "skills": ["list of technical and soft skills"],
  "experience_years": <integer or null>,
  "education": "<highest degree and field or null>",
  "location_preference": "<city/country or 'remote' or null>",
  "industries": ["list of relevant industries"],
  "seniority": "<entry/mid/senior/executive or null>",
  "job_type": "<full-time/part-time/remote/contract or null>",
  "summary": "<2-sentence professional summary>"
}}

Input:
{user_input}

JSON:
"""


def extract_profile(user_input: str, llm: ChatOpenAI) -> dict:
    """Extract structured profile dict from raw user input."""

    prompt = PromptTemplate(
        input_variables=["user_input"],
        template=PROFILE_EXTRACTION_PROMPT
    )

    chain = LLMChain(llm=llm, prompt=prompt)
    raw = chain.run(user_input=user_input).strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw_extraction": raw, "summary": user_input[:300]}