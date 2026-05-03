"""
formatters.py
Utility functions for formatting job results, profiles, and scores
for display in the Streamlit UI.
"""

import plotly.graph_objects as go
from typing import List


def score_gauge(score: int, title: str = "ATS Match Score") -> go.Figure:
    """
    Render a Plotly gauge chart for an ATS score (0-100).
    """
    colour = "#22C55E" if score >= 75 else "#F59E0B" if score >= 50 else "#EF4444"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": title, "font": {"size": 16}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1},
            "bar": {"color": colour},
            "steps": [
                {"range": [0, 50],   "color": "#FEE2E2"},
                {"range": [50, 75],  "color": "#FEF9C3"},
                {"range": [75, 100], "color": "#DCFCE7"},
            ],
            "threshold": {
                "line": {"color": "black", "width": 3},
                "thickness": 0.75,
                "value": score
            }
        }
    ))
    fig.update_layout(height=260, margin=dict(t=40, b=0, l=20, r=20))
    return fig


def keyword_badges(keywords: List[str], colour: str = "green") -> str:
    """
    Render a list of keywords as coloured HTML badge pills.
    colour: 'green' | 'red' | 'blue'
    """
    bg_map = {
        "green": "#DCFCE7", "red": "#FEE2E2", "blue": "#DBEAFE"
    }
    text_map = {
        "green": "#166534", "red": "#991B1B", "blue": "#1E40AF"
    }
    bg   = bg_map.get(colour, "#F3F4F6")
    text = text_map.get(colour, "#374151")

    badges = " ".join(
        f'<span style="display:inline-block;padding:3px 10px;margin:3px;'
        f'border-radius:999px;background:{bg};color:{text};'
        f'font-size:13px;font-weight:500;">{kw}</span>'
        for kw in keywords
    )
    return badges


def profile_summary_card(profile: dict) -> str:
    """Return an HTML summary card for the extracted profile."""
    titles = ", ".join(profile.get("job_titles", []) or ["N/A"])
    skills = ", ".join((profile.get("skills", []) or [])[:8])
    exp    = profile.get("experience_years", "N/A")
    loc    = profile.get("location_preference", "N/A")
    summ   = profile.get("summary", "")

    return f"""
    <div style='padding:16px;background:#F0F9FF;border-radius:8px;border-left:4px solid #0EA5E9;margin-bottom:16px;'>
      <b style='font-size:15px;'>🧑‍💼 {titles}</b><br>
      <span style='color:#6B7280;font-size:13px;'>
        📍 {loc} &nbsp;|&nbsp; 🕐 {exp} years exp &nbsp;|&nbsp; 🎓 {profile.get("education","N/A")}
      </span><br><br>
      <b>Top Skills:</b> {skills}<br>
      {f"<br><i>{summ}</i>" if summ else ""}
    </div>
    """