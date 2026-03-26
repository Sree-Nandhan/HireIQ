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
    """Convert schema artifacts or strings into proper lists, stripping null-like values."""
    if isinstance(v, list):
        return [x for x in v if isinstance(x, (str, dict))
                and (isinstance(x, dict) or str(x).strip().lower() not in _NULL_TOKENS)]
    if isinstance(v, dict):
        return []
    if isinstance(v, str):
        return [x.strip() for x in v.split(",")
                if x.strip() and x.strip().lower() not in _NULL_TOKENS]
    return []


class ParsedResume(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    skills: List[str]
    experience: List[dict] = []
    education: List[dict] = []
    summary: Optional[str] = None

    @field_validator("skills", mode="before")
    @classmethod
    def coerce_skills(cls, v):
        return _coerce_list(v)

    @field_validator("experience", "education", mode="before")
    @classmethod
    def coerce_dicts(cls, v):
        if isinstance(v, list):
            return [x for x in v if isinstance(x, dict)]
        return []


def resume_parser_node(state: AgentState) -> AgentState:
    """Parse the raw resume text into structured data and index it in ChromaDB."""
    try:
        llm = ChatGoogleGenerativeAI(model=settings.gemini_model, temperature=0, google_api_key=settings.google_api_key)

        resume_text = state['resume_text'][:4000]
        prompt = (
            "Parse this resume. Extract structured info.\n\n"
            f"RESUME:\n{resume_text}\n\n"
            "For skills: list every specific tool/framework/language (e.g. Python, React, Docker) — no broad categories.\n\n"
            "Respond with ONLY a JSON object:\n"
            '{"name": "string", "email": "string", "phone": "string or null", '
            '"skills": ["every", "specific", "tool", "and", "technology"], '
            '"experience": [{"title": "...", "company": "...", "bullets": ["..."]}], '
            '"education": [{"degree": "...", "institution": "..."}], '
            '"summary": "string or null"}'
        )

        parsed: ParsedResume = invoke_structured(llm, prompt, ParsedResume)
        resume_dict = parsed.model_dump()

        # Index resume into ChromaDB for later RAG retrieval.
        session_id = state.get("session_id", "unknown")
        chunks = [state["resume_text"]]
        ids = [f"resume_{session_id}_0"]
        try:
            index_documents(chunks, ids, collection_name="resumes")
        except Exception:
            pass

        return {
            **state,
            "resume_parsed": resume_dict,
            "completed_agents": state.get("completed_agents", []) + ["resume_parser"],
        }

    except Exception as exc:
        error_msg = f"resume_parser_node error: {traceback.format_exc()}"
        return {
            **state,
            "error": error_msg,
            "completed_agents": state.get("completed_agents", []) + ["resume_parser"],
        }
