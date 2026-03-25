import re
import traceback
from typing import List

from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

from agents.config import settings
from agents.state import AgentState
from agents.tools.rag import query_collection


_NULL_TOKENS = {"null", "none", "n/a", "na", "-", ""}


def _normalize(text: str) -> str:
    """Lowercase + strip punctuation for comparison."""
    return re.sub(r"[^a-z0-9\s]", " ", text.lower())


def _skill_match(skill: str, resume_text: str, resume_skills: List[str]) -> str:
    """
    Deterministically classify a JD skill against the resume.
    Returns 'match', 'partial', or 'miss'.
    """
    norm_skill = _normalize(skill)
    norm_resume = _normalize(resume_text)
    norm_skills_list = [_normalize(s) for s in resume_skills]

    # --- Full match: skill phrase appears literally in resume text ---
    if norm_skill in norm_resume:
        return "match"

    # --- Full match: against parsed skills list ---
    for s in norm_skills_list:
        if norm_skill == s or norm_skill in s or s in norm_skill:
            return "match"

    # --- Partial: a meaningful word (4+ chars) from the skill appears in resume text ---
    words = [w for w in norm_skill.split() if len(w) >= 4]
    if words and any(w in norm_resume for w in words):
        return "partial"

    return "miss"


def gap_analyst_node(state: AgentState) -> AgentState:
    """Perform a gap analysis between the parsed resume and the parsed JD."""
    try:
        resume_parsed = state.get("resume_parsed") or {}
        jd_parsed = state.get("jd_parsed") or {}
        resume_text = state.get("resume_text", "")

        resume_skills: List[str] = [
            s for s in (resume_parsed.get("skills") or [])
            if isinstance(s, str) and s.strip().lower() not in _NULL_TOKENS
        ]

        # All required skills from the JD (deduplicated)
        jd_required: List[str] = [
            s for s in (jd_parsed.get("required_skills") or [])
            if isinstance(s, str) and s.strip().lower() not in _NULL_TOKENS
        ]
        jd_nice: List[str] = [
            s for s in (jd_parsed.get("nice_to_have_skills") or [])
            if isinstance(s, str) and s.strip().lower() not in _NULL_TOKENS
        ]
        all_jd_skills = list(dict.fromkeys(jd_required + jd_nice))  # preserve order, dedup

        # --- Deterministic classification ---
        matching_skills: List[str] = []
        missing_skills: List[str] = []
        partial_matches: List[str] = []

        for skill in all_jd_skills:
            result = _skill_match(skill, resume_text, resume_skills)
            if result == "match":
                matching_skills.append(skill)
            elif result == "partial":
                partial_matches.append(skill)
            else:
                missing_skills.append(skill)

        # --- Deterministic match percentage ---
        total = len(all_jd_skills)
        if total > 0:
            match_pct = round((len(matching_skills) + 0.5 * len(partial_matches)) / total * 100, 1)
        else:
            match_pct = 0.0

        # --- LLM only for the summary text ---
        rag_context = ""
        try:
            job_title = jd_parsed.get("job_title", "")
            if job_title:
                chunks = query_collection(query=job_title, collection_name="resumes", n_results=3)
                if chunks:
                    rag_context = "\n\nAdditional resume context:\n" + "\n---\n".join(chunks)
        except Exception:
            pass

        llm = ChatGroq(model=settings.groq_model, temperature=0, groq_api_key=settings.groq_api_key)

        summary_prompt = (
            f"The candidate matches {match_pct}% of the job requirements.\n"
            f"Matching skills ({len(matching_skills)}): {', '.join(matching_skills[:8]) or 'none'}\n"
            f"Missing skills ({len(missing_skills)}): {', '.join(missing_skills[:8]) or 'none'}\n"
            f"Partial matches ({len(partial_matches)}): {', '.join(partial_matches[:5]) or 'none'}\n"
            f"{rag_context}\n\n"
            "Write 2 sentences summarising the candidate's fit for this role. Be direct and specific."
        )

        try:
            resp = llm.invoke([HumanMessage(content=summary_prompt)])
            summary = resp.content.strip()
        except Exception:
            summary = f"Candidate matches {match_pct}% of the job requirements."

        return {
            **state,
            "gap_analysis": {
                "matching_skills": matching_skills,
                "missing_skills": missing_skills,
                "partial_matches": partial_matches,
                "match_percentage": match_pct,
                "summary": summary,
            },
            "completed_agents": state.get("completed_agents", []) + ["gap_analyst"],
        }

    except Exception:
        error_msg = f"gap_analyst_node error: {traceback.format_exc()}"
        return {
            **state,
            "error": error_msg,
            "completed_agents": state.get("completed_agents", []) + ["gap_analyst"],
        }
