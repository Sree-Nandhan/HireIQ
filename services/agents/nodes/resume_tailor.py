import json
import traceback
from typing import List

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from agents.config import settings
from agents.state import AgentState
from agents.tools.structured import invoke_structured


class TailoredBullet(BaseModel):
    original: str
    tailored: str
    reasoning: str


class TailoredBullets(BaseModel):
    bullets: List[TailoredBullet]


def resume_tailor_node(state: AgentState) -> AgentState:
    """Rewrite the top 5 most relevant resume bullet points to match the JD keywords."""
    try:
        resume_parsed = state.get("resume_parsed") or {}
        jd_parsed = state.get("jd_parsed") or {}
        gap_analysis = state.get("gap_analysis") or {}

        all_bullets: List[str] = []
        for exp in resume_parsed.get("experience", []):
            bullets = exp.get("bullets", [])
            if isinstance(bullets, list):
                all_bullets.extend([str(b) for b in bullets])

        if not all_bullets:
            return {
                **state,
                "tailored_bullets": [],
                "completed_agents": state.get("completed_agents", []) + ["resume_tailor"],
            }

        # Show up to 8 bullets for strong matches, fewer for weak ones.
        # Cap at len(all_bullets) so we never ask for more than exist.
        gap_pct = float((gap_analysis or {}).get("match_percentage", 0))
        if gap_pct >= 60:
            n_bullets = min(len(all_bullets), 8)
        elif gap_pct >= 30:
            n_bullets = min(len(all_bullets), 5)
        else:
            n_bullets = min(len(all_bullets), 3)

        llm = ChatGoogleGenerativeAI(model=settings.gemini_model, temperature=0.3, google_api_key=settings.google_api_key)

        prompt = (
            f"You are an expert resume writer. Select and rewrite the {n_bullets} most relevant "
            "resume bullet points to better match the target job description.\n\n"
            f"ALL RESUME BULLETS:\n{json.dumps(all_bullets, indent=2)}\n\n"
            f"JOB DESCRIPTION KEYWORDS & SKILLS:\n{json.dumps(jd_parsed, indent=2)}\n\n"
            f"GAP ANALYSIS:\n{json.dumps(gap_analysis, indent=2)}\n\n"
            f"Select exactly {n_bullets} bullets. For each, provide the original text, "
            "a rewritten version with strong action verbs and JD keywords, "
            "and brief reasoning for the improvement.\n\n"
            "Respond with ONLY a JSON object with this exact structure:\n"
            '{"bullets": [{"original": "string", "tailored": "string", "reasoning": "string"}]}'
        )

        result: TailoredBullets = invoke_structured(llm, prompt, TailoredBullets)
        # Drop any bullets the LLM returned with empty/null fields (happens when
        # the resume has fewer bullets than requested).
        _null = {"", "null", "none", "n/a"}
        tailored_list = [
            b.model_dump() for b in result.bullets
            if b.original.strip().lower() not in _null
            and b.tailored.strip().lower() not in _null
        ]

        return {
            **state,
            "tailored_bullets": tailored_list,
            "completed_agents": state.get("completed_agents", []) + ["resume_tailor"],
        }

    except Exception as exc:
        error_msg = f"resume_tailor_node error: {traceback.format_exc()}"
        return {
            **state,
            "error": error_msg,
            "completed_agents": state.get("completed_agents", []) + ["resume_tailor"],
        }
