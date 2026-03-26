import json
import traceback

from langchain_google_genai import ChatGoogleGenerativeAI
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

        llm = ChatGoogleGenerativeAI(model=settings.gemini_model, temperature=0.7, google_api_key=settings.google_api_key)

        prompt = (
            f"You are a professional career coach. Write a compelling cover letter for "
            f"{candidate_name} applying for the '{job_title}' role at {company}.\n\n"
            f"CANDIDATE PROFILE:\n{json.dumps(resume_parsed, indent=2)}\n\n"
            f"JOB REQUIREMENTS:\n{json.dumps(jd_parsed, indent=2)}\n\n"
            f"MATCHING SKILLS: {matching_skills}\n\n"
            "Write exactly 3 paragraphs:\n"
            "1. Opening — express enthusiasm for the role and company.\n"
            "2. Body — highlight 2-3 matching skills with concrete examples.\n"
            "3. Closing — reiterate enthusiasm and invite next steps.\n\n"
            "Return ONLY the cover letter text, no additional commentary."
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
