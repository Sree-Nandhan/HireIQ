import json
import traceback
from typing import List

from langchain_google_genai import ChatGoogleGenerativeAI
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

        llm = ChatGoogleGenerativeAI(model=settings.gemini_model, temperature=0.5, google_api_key=settings.google_api_key)

        prompt = (
            "You are an expert interview coach. Generate exactly 4 likely interview "
            "questions for the candidate below, tailored to the specific job role. "
            "Mix of: 2 behavioral, 2 technical questions.\n\n"
            f"CANDIDATE PROFILE:\n{json.dumps(resume_parsed, indent=2)}\n\n"
            f"JOB DESCRIPTION:\n{json.dumps(jd_parsed, indent=2)}\n\n"
            f"GAP ANALYSIS:\n{json.dumps(gap_analysis, indent=2)}\n\n"
            "For each question provide: question, type (behavioral/technical/role-specific), "
            "and a model_answer (1-2 sentences tailored to the candidate).\n\n"
            "Respond with ONLY a JSON object with this exact structure:\n"
            '{"qa_pairs": [{"question": "string", "type": "behavioral", "model_answer": "string"}]}'
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
