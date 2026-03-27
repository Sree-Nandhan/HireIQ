import json
import logging
import traceback
from typing import List

from agents.tools.gemini import GeminiClient
from pydantic import BaseModel, field_validator

from agents.config import settings
from agents.state import AgentState
from agents.tools.structured import invoke_structured

logger = logging.getLogger(__name__)


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


class ATSScore(BaseModel):
    score: int = 0
    keyword_matches: List[str] = []
    keyword_misses: List[str] = []
    formatting_suggestions: List[str] = []
    overall_assessment: str = ""

    @field_validator("keyword_matches", "keyword_misses", "formatting_suggestions", mode="before")
    @classmethod
    def coerce_lists(cls, v):
        return _coerce_list(v)


def ats_scorer_node(state: AgentState) -> AgentState:
    """Estimate ATS compatibility and provide keyword + formatting feedback."""
    session_id = state.get("session_id", "?")
    logger.info("ats_scorer_node: starting [session=%s]", session_id)
    try:
        resume_text = state.get("resume_text", "")
        jd_parsed = state.get("jd_parsed") or {}
        resume_parsed = state.get("resume_parsed") or {}
        tailored_bullets = state.get("tailored_bullets") or []

        llm = GeminiClient(model=settings.gemini_model, temperature=0, google_api_key=settings.google_api_key, json_mode=True)

        candidate_skills = resume_parsed.get("skills", [])
        jd_keywords = jd_parsed.get("keywords", [])
        jd_required = jd_parsed.get("required_skills", [])

        prompt = (
            "You are an ATS expert. Score the candidate's resume for this job.\n\n"
            f"CANDIDATE SKILLS: {candidate_skills}\n\n"
            f"TAILORED BULLETS: {[b.get('tailored') for b in tailored_bullets]}\n\n"
            f"JOB REQUIRED SKILLS: {jd_required}\n"
            f"JOB KEYWORDS: {jd_keywords}\n\n"
            "Provide: score (0-100), keyword_matches (list), keyword_misses (list), "
            "formatting_suggestions (2 tips as a list), and overall_assessment (1-2 sentences).\n\n"
            "Respond with ONLY a JSON object with these exact keys:\n"
            '{"score": 0, "keyword_matches": ["list"], "keyword_misses": ["list"], '
            '"formatting_suggestions": ["tip1", "tip2"], "overall_assessment": "string"}'
        )

        result: ATSScore = invoke_structured(llm, prompt, ATSScore)
        score_dict = result.model_dump()

        # Pin the ATS score to the gap analysis match_percentage so both
        # numbers stay consistent — one score, one story.
        gap_pct = float((state.get("gap_analysis") or {}).get("match_percentage", 0))
        score_dict["score"] = max(0, min(100, round(gap_pct)))

        logger.info(
            "ats_scorer_node: done [session=%s] score=%d keyword_matches=%d keyword_misses=%d",
            session_id,
            score_dict.get("score", 0),
            len(score_dict.get("keyword_matches", [])),
            len(score_dict.get("keyword_misses", [])),
        )
        return {
            **state,
            "ats_score": score_dict,
            "completed_agents": state.get("completed_agents", []) + ["ats_scorer"],
        }

    except Exception as exc:
        error_msg = f"ats_scorer_node error: {traceback.format_exc()}"
        logger.error("ats_scorer_node: FAILED [session=%s]: %s", session_id, exc, exc_info=True)
        return {
            **state,
            "error": error_msg,
            "completed_agents": state.get("completed_agents", []) + ["ats_scorer"],
        }
