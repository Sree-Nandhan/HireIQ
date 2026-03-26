import json
import traceback

from agents.tools.gemini import GeminiClient
from langchain_core.messages import HumanMessage

from agents.config import settings
from agents.state import AgentState


def cover_letter_node(state: AgentState) -> AgentState:
    """Generate a professional, personalized 3-paragraph cover letter."""
    try:
        resume_parsed = state.get("resume_parsed") or {}
        jd_parsed = state.get("jd_parsed") or {}
        gap_analysis = state.get("gap_analysis") or {}

        candidate_name = resume_parsed.get("name", "the candidate")
        job_title = jd_parsed.get("job_title", "the position")
        company = jd_parsed.get("company") or "your company"
        matching_skills = gap_analysis.get("matching_skills", [])

        llm = GeminiClient(model=settings.gemini_model, temperature=0.7, google_api_key=settings.google_api_key)

        candidate_slim = {
            "name": candidate_name,
            "skills": resume_parsed.get("skills", [])[:10],
            "experience": [{"title": e.get("title"), "company": e.get("company")} for e in resume_parsed.get("experience", [])[:3]],
        }
        jd_slim = {"title": job_title, "company": company, "required": jd_parsed.get("required_skills", [])[:8]}

        prompt = (
            f"Write a 3-paragraph cover letter for {candidate_name} applying to '{job_title}' at {company}.\n\n"
            f"CANDIDATE: {json.dumps(candidate_slim)}\nJD: {json.dumps(jd_slim)}\nMATCHES: {matching_skills[:8]}\n\n"
            "Para 1: enthusiasm. Para 2: 2-3 matching skills with examples. Para 3: closing.\n"
            "Return ONLY the cover letter text."
        )

        message = HumanMessage(content=prompt)
        response = llm.invoke([message])
        cover_letter_text = response.content.strip()

        return {
            **state,
            "cover_letter": cover_letter_text,
            "completed_agents": state.get("completed_agents", []) + ["cover_letter"],
        }

    except Exception as exc:
        error_msg = f"cover_letter_node error: {traceback.format_exc()}"
        return {
            **state,
            "error": error_msg,
            "completed_agents": state.get("completed_agents", []) + ["cover_letter"],
        }
