"""
app.py — Main Streamlit application for the AI Job Search Agent.

Features:
  ✅ Resume upload (PDF/DOCX) or free-text input
  ✅ Multi-source job search (Google Jobs, LinkedIn, Indeed, Naukri)
  ✅ ATS resume score comparison (cosine similarity + LLM deep analysis)
  ✅ Cover letter generator (with tone selection + DOCX download)
  ✅ Email alerts (immediate + scheduled)
  ✅ LangSmith tracing dashboard link
"""
from dotenv import load_dotenv

load_dotenv()
import os
import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# ── Local modules ────────────────────────────────────────────────────
from parsers.resume_parser import parse_resume
from parsers.input_parser import extract_profile
from agent.agent import build_agent, configure_langsmith
from ats.scorer import quick_ats_score, deep_ats_analysis, score_colour
from cover_letter.generator import generate_cover_letter, format_cover_letter_docx
from alerts.email_alerts import send_job_alert, alert_scheduler
from utils.formatters import score_gauge, keyword_badges, profile_summary_card
# ════════════════════════════════════════════════════════════════════
# Page config
# ════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="AI Job Search Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
  .stTabs [data-baseweb="tab"] { font-size: 15px; font-weight: 600; }
  .block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════
# Session state defaults
# ════════════════════════════════════════════════════════════════════
for key, default in {
    "profile": None,
    "resume_text": "",
    "jobs_output": "",
    "ats_result": None,
    "cover_letter": "",
    "alert_active": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ════════════════════════════════════════════════════════════════════
# Sidebar
# ════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/job.png", width=60)
    st.title("AI Job Search Agent")
    st.divider()

    st.subheader("⚙️ Search Preferences")
    location    = st.text_input("📍 Location", placeholder="e.g. London, Remote, Bangalore")
    job_type    = st.selectbox("💼 Job Type",    ["Any", "Full-time", "Part-time", "Remote", "Contract", "Internship"])
    seniority   = st.selectbox("🎯 Seniority",   ["Any", "Entry", "Mid", "Senior", "Lead", "Executive"])
    industry    = st.text_input("🏭 Industry (optional)", placeholder="e.g. FinTech, Healthcare")

    st.divider()
    st.subheader("🔔 Email Alert Settings")
    alert_email    = st.text_input("📧 Your Email", placeholder="you@example.com")
    alert_interval = st.selectbox("⏰ Alert Frequency", ["Daily", "Every 12 hours", "Every 6 hours", "Every hour"])
    interval_map   = {"Daily": 24, "Every 12 hours": 12, "Every 6 hours": 6, "Every hour": 1}

    st.divider()
    tracing_on = configure_langsmith()
    if tracing_on:
        project = os.getenv("LANGCHAIN_PROJECT", "job-search-agent")
        st.success(f"🔬 LangSmith Tracing: ON")
        st.markdown(
            f"[📊 View Traces](https://smith.langchain.com/projects/{project})",
            unsafe_allow_html=False
        )
    else:
        st.info("🔬 LangSmith Tracing: OFF\n\nSet `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` in `.env` to enable.")

# ════════════════════════════════════════════════════════════════════
# Header
# ════════════════════════════════════════════════════════════════════
st.title("🔍 AI Job Search Agent")
st.caption("Powered by LangChain · GPT-4o · Google Jobs · LinkedIn · Indeed · Naukri · LangSmith")
st.divider()

# ════════════════════════════════════════════════════════════════════
# TABS
# ════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 Profile & Search",
    "📊 ATS Score",
    "✉️ Cover Letter",
    "🔔 Email Alerts",
    "🔬 LangSmith Traces"
])

# ════════════════════════════════════════════════════════════════════
# TAB 1 — Profile & Job Search
# ════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Tell us about yourself")
    input_mode = st.radio(
        "How would you like to provide your information?",
        ["📄 Upload Resume (PDF/DOCX)", "✍️ Describe Yourself", "🗂️ Fill in Details"],
        horizontal=True
    )

    user_text = ""

    # ── Upload Resume ────────────────────────────────────────────────
    if input_mode == "📄 Upload Resume (PDF/DOCX)":
        uploaded = st.file_uploader("Upload your resume", type=["pdf", "docx", "txt"])
        if uploaded:
            with st.spinner("Parsing resume..."):
                user_text = parse_resume(uploaded)
                st.session_state.resume_text = user_text
            st.success("✅ Resume parsed successfully!")
            with st.expander("Preview extracted text (first 1500 chars)"):
                st.text(user_text[:1500])

    # ── Free text ────────────────────────────────────────────────────
    elif input_mode == "✍️ Describe Yourself":
        user_text = st.text_area(
            "Describe your background, skills, or the role you're looking for:",
            placeholder=(
                "e.g. I'm a full-stack developer with 4 years of experience in React and Node.js. "
                "I've built SaaS products and want a senior role in a product-led startup, preferably remote."
            ),
            height=200
        )

    # ── Structured form ──────────────────────────────────────────────
    else:
        c1, c2 = st.columns(2)
        with c1:
            name_input  = st.text_input("Your Name")
            title_input = st.text_input("Current / Target Job Title", placeholder="e.g. Data Scientist")
            exp_input   = st.number_input("Years of Experience", min_value=0, max_value=40, step=1)
            edu_input   = st.text_input("Highest Education", placeholder="e.g. B.Tech Computer Science")
        with c2:
            skills_input   = st.text_area("Key Skills (comma-separated)", placeholder="Python, SQL, TensorFlow, AWS", height=120)
            industry_input = st.text_input("Industry / Domain", placeholder="e.g. FinTech, E-commerce")
            extra_input    = st.text_area("Anything else?", placeholder="Open to relocation, prefer startups...", height=80)

        if title_input:
            user_text = (
                f"Name: {name_input}. Job title: {title_input}. "
                f"Experience: {exp_input} years. Education: {edu_input}. "
                f"Skills: {skills_input}. Industry: {industry_input}. Notes: {extra_input}."
            )

    # Append sidebar preferences
    if user_text:
        if location:    user_text += f" Location preference: {location}."
        if job_type != "Any": user_text += f" Job type: {job_type}."
        if seniority != "Any": user_text += f" Seniority: {seniority}."
        if industry:    user_text += f" Industry focus: {industry}."

    st.divider()

    search_btn = st.button("🚀 Find Matching Jobs", type="primary", disabled=not user_text.strip())

    if search_btn and user_text.strip():
        llm = ChatOpenAI(model="gpt-4o", temperature=0)

        with st.spinner("🧠 Building your profile..."):
            profile = extract_profile(user_text, llm)
            st.session_state.profile = profile

        st.markdown("### 🧑‍💼 Your Extracted Profile")
        st.markdown(profile_summary_card(profile), unsafe_allow_html=True)

        with st.expander("📂 Full profile JSON"):
            st.json(profile)

        with st.spinner("🔎 Searching jobs across Google, LinkedIn, Indeed, Naukri..."):
            executor, tracing = build_agent(profile)
            result = executor.invoke({
                "input": "Find the best matching jobs for the user profile",
                "profile": profile
            })
            st.session_state.jobs_output = result.get("output", "")

        st.markdown("### ✅ Top Job Matches")
        st.markdown(st.session_state.jobs_output)

        # ── Steps expander (LangSmith-style local view) ──────────────
        steps = result.get("intermediate_steps", [])
        if steps:
            with st.expander(f"🔬 Agent Reasoning ({len(steps)} steps)"):
                for i, (action, observation) in enumerate(steps, 1):
                    st.markdown(f"**Step {i} — Tool:** `{action.tool}`")
                    st.code(action.tool_input, language="text")
                    st.markdown(f"**Result preview:** {str(observation)[:400]}...")
                    st.divider()

    elif st.session_state.jobs_output:
        st.markdown("### ✅ Previous Job Matches")
        st.markdown(st.session_state.jobs_output)


# ════════════════════════════════════════════════════════════════════
# TAB 2 — ATS Score
# ════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("📊 ATS Resume Score Checker")
    st.caption("Compare your resume against any job description to see how well you match.")

    col_a, col_b = st.columns(2)

    with col_a:
        resume_for_ats = st.text_area(
            "📄 Resume Text",
            value=st.session_state.resume_text,
            height=300,
            placeholder="Paste your resume text here..."
        )

    with col_b:
        jd_text = st.text_area(
            "📋 Job Description",
            height=300,
            placeholder="Paste the target job description here..."
        )

    ats_mode = st.radio(
        "Analysis mode:",
        ["⚡ Quick (keyword similarity)", "🧠 Deep (LLM-powered, uses API credits)"],
        horizontal=True
    )

    if st.button("📊 Analyse ATS Match", type="primary", disabled=not (resume_for_ats and jd_text)):
        if "Quick" in ats_mode:
            score = quick_ats_score(resume_for_ats, jd_text)
            st.session_state.ats_result = {
                "overall_score": score,
                "summary": f"Keyword similarity score: {score}/100",
                "mode": "quick"
            }
        else:
            with st.spinner("🧠 Running deep ATS analysis with LLM..."):
                llm = ChatOpenAI(model="gpt-4o", temperature=0)
                result = deep_ats_analysis(resume_for_ats, jd_text, llm)
                result["mode"] = "deep"
                st.session_state.ats_result = result

    # ── Display ATS results ──────────────────────────────────────────
    if st.session_state.ats_result:
        r = st.session_state.ats_result
        score = int(r.get("overall_score", 0))
        emoji = score_colour(score)

        st.markdown(f"## {emoji} ATS Match Score: **{score}/100**")
        st.plotly_chart(score_gauge(score), use_container_width=False)
        st.info(r.get("summary", ""))

        if r.get("mode") == "deep":
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### ✅ Matched Keywords")
                matched = r.get("matched_keywords", [])
                st.markdown(keyword_badges(matched, "green"), unsafe_allow_html=True)

                st.markdown("### 💪 Matched Skills")
                m_skills = r.get("matched_skills", [])
                st.markdown(keyword_badges(m_skills, "blue"), unsafe_allow_html=True)

            with col2:
                st.markdown("### ❌ Missing Keywords")
                missing = r.get("missing_keywords", [])
                st.markdown(keyword_badges(missing, "red"), unsafe_allow_html=True)

                st.markdown("### ⚠️ Missing Skills")
                miss_skills = r.get("missing_skills", [])
                st.markdown(keyword_badges(miss_skills, "red"), unsafe_allow_html=True)

            st.markdown("### 🛠️ Recommendations to Improve Your Resume")
            for rec in r.get("recommendations", []):
                st.markdown(f"- {rec}")

            col3, col4 = st.columns(2)
            with col3:
                st.metric("Experience Match", r.get("experience_match", "N/A").title())
            with col4:
                st.metric("Education Match",  r.get("education_match", "N/A").title())


# ════════════════════════════════════════════════════════════════════
# TAB 3 — Cover Letter
# ════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("✉️ Cover Letter Generator")
    st.caption("Generate a personalised, ATS-optimised cover letter for any job in seconds.")

    c1, c2 = st.columns(2)
    with c1:
        cl_job_title = st.text_input("Job Title", placeholder="e.g. Senior Data Scientist")
        cl_company   = st.text_input("Company Name", placeholder="e.g. Stripe")
        cl_location  = st.text_input("Location", placeholder="e.g. San Francisco, CA")
    with c2:
        cl_tone = st.selectbox("Tone", ["professional", "enthusiastic", "concise"])
        cl_name = st.text_input("Your Name (for sign-off)", placeholder="e.g. Jane Smith")

    cl_jd = st.text_area(
        "Job Description (paste full JD for best results)",
        height=200,
        placeholder="Paste the job description here..."
    )

    use_profile = st.checkbox("Use extracted profile from Tab 1", value=True)

    if st.button("✉️ Generate Cover Letter", type="primary",
                 disabled=not (cl_job_title and cl_company and cl_jd)):
        profile_to_use = st.session_state.profile if (use_profile and st.session_state.profile) else {"summary": "Experienced professional"}
        with st.spinner("✍️ Writing your cover letter..."):
            llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
            letter = generate_cover_letter(
                profile=profile_to_use,
                job_title=cl_job_title,
                company=cl_company,
                location=cl_location,
                job_description=cl_jd,
                llm=llm,
                tone=cl_tone
            )
            st.session_state.cover_letter = letter

    if st.session_state.cover_letter:
        st.markdown("### 📄 Your Cover Letter")
        st.markdown(
            f"<div style='background:#F9FAFB;padding:24px;border-radius:8px;"
            f"border:1px solid #E5E7EB;white-space:pre-wrap;font-size:14px;line-height:1.7;'>"
            f"{st.session_state.cover_letter}</div>",
            unsafe_allow_html=True
        )

        # ── Downloads ────────────────────────────────────────────────
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.download_button(
                "📥 Download as .txt",
                data=st.session_state.cover_letter,
                file_name=f"cover_letter_{cl_company.replace(' ','_')}.txt",
                mime="text/plain"
            )
        with col_d2:
            docx_bytes = format_cover_letter_docx(st.session_state.cover_letter, cl_name or "Candidate")
            st.download_button(
                "📥 Download as .docx",
                data=docx_bytes,
                file_name=f"cover_letter_{cl_company.replace(' ','_')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

        # ── Quick ATS check on the cover letter ─────────────────────
        if cl_jd:
            cl_score = quick_ats_score(st.session_state.cover_letter, cl_jd)
            emoji = score_colour(cl_score)
            st.metric(f"{emoji} Cover Letter ATS Score", f"{cl_score}/100",
                      help="Keyword similarity between your cover letter and the job description.")


# ════════════════════════════════════════════════════════════════════
# TAB 4 — Email Alerts
# ════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("🔔 Job Alert Notifications")
    st.caption("Get new job matches sent directly to your inbox on a schedule.")

    if not alert_email:
        st.warning("⚠️ Please enter your email address in the sidebar first.")
    else:
        st.info(f"📧 Alerts will be sent to: **{alert_email}**")

    col_e1, col_e2 = st.columns(2)

    with col_e1:
        # Send immediate alert
        if st.button("📤 Send Immediate Alert Now", disabled=not st.session_state.jobs_output):
            if not st.session_state.jobs_output:
                st.error("Please run a job search in Tab 1 first.")
            else:
                summary = str(st.session_state.profile.get("summary", "Job seeker"))[:100] if st.session_state.profile else "Job seeker"
                ok, msg = send_job_alert(
                    jobs_text=st.session_state.jobs_output,
                    profile_summary=summary,
                    recipient=alert_email
                )
                if ok:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")

    with col_e2:
        # Scheduled alerts
        if not alert_scheduler.is_running:
            if st.button("⏰ Start Scheduled Alerts", disabled=not st.session_state.profile):
                profile = st.session_state.profile
                summary = str(profile.get("summary", ""))[:100] if profile else ""

                def search_fn():
                    executor, _ = build_agent(profile)
                    result = executor.invoke({"input": "Find the best matching jobs for this user."})
                    return result.get("output", "")

                alert_scheduler.start(
                    search_fn=search_fn,
                    profile_summary=summary,
                    recipient=alert_email,
                    interval_hours=interval_map[alert_interval]
                )
                st.session_state.alert_active = True
                st.success(f"✅ Scheduled alerts started! ({alert_interval})")
        else:
            st.success(f"✅ Alerts are running ({alert_interval})")
            if st.button("🛑 Stop Alerts"):
                alert_scheduler.stop()
                st.session_state.alert_active = False
                st.info("Alerts stopped.")

    st.divider()
    st.markdown("""
    #### 📋 Email Alert Setup Guide

    1. **Gmail users:** Create an [App Password](https://support.google.com/accounts/answer/185833)
       (Google Account → Security → App Passwords)
    2. Add these to your `.env` file:
    ```
    ALERT_EMAIL_SENDER=you@gmail.com
    ALERT_EMAIL_PASSWORD=your_16_char_app_password
    ALERT_EMAIL_RECIPIENT=you@gmail.com
    ```
    3. Run a job search in **Tab 1** first, then send alerts here.
    4. Scheduled alerts re-run the search automatically and email only if new results are found.
    """)


# ════════════════════════════════════════════════════════════════════
# TAB 5 — LangSmith Tracing
# ════════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("🔬 LangSmith Observability")

    if tracing_on:
        project = os.getenv("LANGCHAIN_PROJECT", "job-search-agent")
        st.success("✅ LangSmith tracing is **active**. Every agent run is being logged.")

        st.markdown(f"""
        ### 📊 Your LangSmith Dashboard
        **Project:** `{project}`

        👉 [Open LangSmith Traces →](https://smith.langchain.com/projects/{project})

        #### What you can monitor:
        | Feature | Details |
        |---|---|
        | 🔗 **Runs** | Every agent invocation with full input/output |
        | 🛠️ **Tool calls** | Which tools were called, with what args and results |
        | ⏱️ **Latency** | Per-step and total response times |
        | 💰 **Token usage** | Prompt + completion tokens per run |
        | 🐛 **Errors** | Failed steps with full stack traces |
        | 🔁 **Agent steps** | Complete ReAct reasoning chain |
        | 📈 **Feedback** | Add thumbs up/down ratings to runs |
        """)
    else:
        st.warning("⚠️ LangSmith tracing is currently **disabled**.")
        st.markdown("""
        ### How to Enable LangSmith Tracing

        1. Sign up free at [smith.langchain.com](https://smith.langchain.com)
        2. Create a project (e.g. `job-search-agent`)
        3. Copy your API key from **Settings → API Keys**
        4. Add to your `.env` file:

        ```env
        LANGCHAIN_TRACING_V2=true
        LANGCHAIN_API_KEY=ls__your_key_here
        LANGCHAIN_PROJECT=job-search-agent
        LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
        ```

        5. Restart the Streamlit app — tracing will activate automatically.

        #### What LangSmith gives you:
        - Full trace of every LLM call and tool invocation
        - Debugging broken agent steps
        - Token cost tracking per session
        - A/B testing different prompts
        - Sharing traces with collaborators
        """)
