import json
import traceback
from typing import List

from agents.tools.gemini import GeminiClient
from pydantic import BaseModel

from agents.config import settings
from agents.state import AgentState
from agents.tools.structured import invoke_structured


class InterviewQA(BaseModel):
    model_config = {"protected_namespaces": ()}

    question: str
    type: str          # behavioral | technical | role-specific
    model_answer: str


class InterviewQAList(BaseModel):
    qa_pairs: List[InterviewQA]


def interview_coach_node(state: AgentState) -> AgentState:
    """Generate 8 tailored interview questions with model answers."""
    try:
        resume_parsed = state.get("resume_parsed") or {}
        jd_parsed = state.get("jd_parsed") or {}
        gap_analysis = state.get("gap_analysis") or {}

        llm = GeminiClient(model=settings.gemini_model, temperature=0.5, google_api_key=settings.google_api_key)

        candidate_slim = {
            "name": resume_parsed.get("name"),
            "skills": resume_parsed.get("skills", [])[:10],
            "experience": [{"title": e.get("title"), "company": e.get("company")} for e in resume_parsed.get("experience", [])[:3]],
        }
        jd_slim = {"title": jd_parsed.get("job_title"), "required": jd_parsed.get("required_skills", [])[:10]}
        gap_slim = {"missing": gap_analysis.get("missing_skills", [])[:6], "matching": gap_analysis.get("matching_skills", [])[:6]}

        prompt = (
            "Generate 4 interview questions (2 behavioral, 2 technical) for this candidate.\n\n"
            f"CANDIDATE: {json.dumps(candidate_slim)}\nJD: {json.dumps(jd_slim)}\nGAPS: {json.dumps(gap_slim)}\n\n"
            "For each: question, type (behavioral/technical), model_answer (1-2 sentences).\n\n"
            'Respond with ONLY: {"qa_pairs": [{"question": "string", "type": "behavioral", "model_answer": "string"}]}'
        )

        result: InterviewQAList = invoke_structured(llm, prompt, InterviewQAList)
        qa_list = [qa.model_dump() for qa in result.qa_pairs]

        return {
            **state,
            "interview_qa": qa_list,
            "completed_agents": state.get("completed_agents", []) + ["interview_coach"],
        }

    except Exception as exc:
        error_msg = f"interview_coach_node error: {traceback.format_exc()}"
        return {
            **state,
            "error": error_msg,
            "completed_agents": state.get("completed_agents", []) + ["interview_coach"],
        }
