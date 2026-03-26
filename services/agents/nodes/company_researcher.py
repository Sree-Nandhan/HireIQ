import traceback
from typing import List

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from agents.config import settings
from agents.state import AgentState
from agents.tools.structured import invoke_structured


_NULL_TOKENS = {"null", "none", "n/a", "na", "-", ""}


class CompanyResearch(BaseModel):
    company_name: str = ""
    what_they_do: str = ""           # 2-3 sentences about what the company does
    recent_projects: List[str] = []  # recent/current initiatives inferred from JD
    culture_notes: str = ""          # 1-2 sentences on culture/values inferred from JD
    why_apply: str = ""              # 1-2 sentences on why this is a good opportunity


def company_researcher_node(state: AgentState) -> AgentState:
    """Infer company insights from the job description using the LLM."""
    try:
        jd_parsed = state.get("jd_parsed") or {}
        job_description = state.get("job_description", "")

        # Extract company name from jd_parsed if available
        company_name_hint = jd_parsed.get("company_name", "") or jd_parsed.get("company", "")

        llm = ChatGoogleGenerativeAI(model=settings.gemini_model, temperature=0.5, google_api_key=settings.google_api_key)

        prompt = (
            "You are a company research analyst. Based solely on the job description below, "
            "infer as much as possible about the company.\n\n"
            f"COMPANY NAME HINT (from parsed JD, may be empty): {company_name_hint}\n\n"
            f"FULL JOB DESCRIPTION:\n{job_description}\n\n"
            "Based on the job description above:\n"
            "1. Identify or infer the company_name (use the hint if available, otherwise extract from the JD text).\n"
            "2. Describe in 2-3 sentences what the company does and what space they operate in (what_they_do).\n"
            "3. List 3-5 recent projects, initiatives, or focus areas the company is working on, inferred from the JD responsibilities and requirements (recent_projects). Each item should be a short phrase like 'Building real-time ML inference platform' or 'Expanding international payments infrastructure'.\n"
            "4. Write 1-2 sentences on company culture and values inferred from the JD tone and requirements (culture_notes).\n"
            "5. Write 1-2 sentences on why this is a good opportunity worth applying for (why_apply).\n\n"
            "Respond with ONLY a JSON object with these exact keys:\n"
            '{"company_name": "string", "what_they_do": "string", "recent_projects": ["list of short phrases"], '
            '"culture_notes": "string", "why_apply": "string"}'
        )

        research: CompanyResearch = invoke_structured(llm, prompt, CompanyResearch)

        # Filter null-like tokens from recent_projects
        cleaned_projects = [
            p for p in research.recent_projects
            if isinstance(p, str) and p.strip().lower() not in _NULL_TOKENS
        ]
        research_dict = research.model_dump()
        research_dict["recent_projects"] = cleaned_projects

        return {
            **state,
            "company_research": research_dict,
            "completed_agents": state.get("completed_agents", []) + ["company_researcher"],
        }

    except Exception:
        error_msg = f"company_researcher_node error: {traceback.format_exc()}"
        return {
            **state,
            "error": error_msg,
            "completed_agents": state.get("completed_agents", []) + ["company_researcher"],
        }
