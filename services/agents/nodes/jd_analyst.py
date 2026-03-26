import traceback
from typing import List, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, field_validator

from agents.config import settings
from agents.state import AgentState
from agents.tools.rag import index_documents
from agents.tools.structured import invoke_structured


_NULL_TOKENS = {"null", "none", "n/a", "na", "-", ""}

def _coerce_list(v):
    if isinstance(v, list):
        return [str(x) for x in v if x and str(x).strip().lower() not in _NULL_TOKENS]
    if isinstance(v, dict):
        return []
    if isinstance(v, str):
        return [x.strip() for x in v.split(",")
                if x.strip() and x.strip().lower() not in _NULL_TOKENS]
    return []


class ParsedJD(BaseModel):
    job_title: str
    company: Optional[str] = None
    required_skills: List[str] = []
    nice_to_have_skills: List[str] = []
    experience_years: Optional[int] = None
    responsibilities: List[str] = []
    keywords: List[str] = []

    @field_validator("required_skills", "nice_to_have_skills", "responsibilities", "keywords", mode="before")
    @classmethod
    def coerce_lists(cls, v):
        return _coerce_list(v)


def jd_analyst_node(state: AgentState) -> AgentState:
    """Parse the job description into structured data and index it in ChromaDB."""
    try:
        llm = ChatGoogleGenerativeAI(model=settings.gemini_model, temperature=0, google_api_key=settings.google_api_key)

        jd_text = state['job_description'][:3000]
        prompt = (
            "Extract structured info from this job description.\n\n"
            f"JD:\n{jd_text}\n\n"
            "Skills: short names only (1-4 words, e.g. Python, React, Docker — not full sentences).\n\n"
            "Respond with ONLY a JSON object:\n"
            '{"job_title": "string", "company": "string or null", '
            '"required_skills": ["Python", "React", "short skill names only"], '
            '"nice_to_have_skills": ["short", "skill", "names"], '
            '"experience_years": 0, '
            '"responsibilities": ["list", "of", "strings"], '
            '"keywords": ["list", "of", "strings"]}'
        )

        parsed: ParsedJD = invoke_structured(llm, prompt, ParsedJD)
        jd_dict = parsed.model_dump()

        # Index JD into ChromaDB for later RAG retrieval.
        session_id = state.get("session_id", "unknown")
        chunks = [state["job_description"]]
        ids = [f"jd_{session_id}_0"]
        try:
            index_documents(chunks, ids, collection_name="job_descriptions")
        except Exception:
            pass

        return {
            **state,
            "jd_parsed": jd_dict,
            "completed_agents": state.get("completed_agents", []) + ["jd_analyst"],
        }

    except Exception as exc:
        error_msg = f"jd_analyst_node error: {traceback.format_exc()}"
        return {
            **state,
            "error": error_msg,
            "completed_agents": state.get("completed_agents", []) + ["jd_analyst"],
        }
