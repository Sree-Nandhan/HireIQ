import json
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.config import settings
from api.database import get_db
from api.models import AnalysisResult, JobApplication, User
from api.schemas import CoachRequest, CoachResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["coach"])

AGENT_TIMEOUT_SECONDS = 60.0


def _latest_analysis(application: JobApplication):
    if not application.analyses:
        return None
    return max(application.analyses, key=lambda a: a.created_at)


def _safe_json(value) -> dict | list:
    """Parse a JSON string stored in the DB, returning empty structure on failure."""
    if not value:
        return {}
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, ValueError):
        return {}


@router.post("/coach", response_model=CoachResponse)
async def coach(
    payload: CoachRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Ask a follow-up career coaching question about a completed analysis.

    Retrieves the latest analysis for the given application and forwards both
    the question and full analysis context to the agent service for an LLM answer.

    Raises **404** if the application does not exist or has no analysis yet.
    Raises **502** if the agent service is unreachable.
    """
    application = (
        db.query(JobApplication)
        .filter(
            JobApplication.id == payload.application_id,
            JobApplication.user_id == current_user.id,
        )
        .first()
    )
    if not application:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Application with id={payload.application_id} not found.",
        )

    analysis = _latest_analysis(application)
    if not analysis:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="No analysis found for this application. Run /analyze first.",
        )

    agent_payload = {
        "question": payload.question,
        "resume_text": application.resume_text,
        "job_description": application.job_description,
        "gap_analysis": _safe_json(analysis.gap_analysis),
        "tailored_bullets": _safe_json(analysis.tailored_bullets),
        "cover_letter": analysis.cover_letter or "",
        "interview_qa": _safe_json(analysis.interview_qa),
        "ats_score": {"score": analysis.ats_score} if analysis.ats_score else {},
    }

    try:
        async with httpx.AsyncClient(timeout=AGENT_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{settings.agent_service_url}/coach",
                json=agent_payload,
            )
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The coach service did not respond in time.",
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_502_BAD_GATEWAY,
            detail=f"Coach service error: {exc.response.text}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach the agent service.",
        ) from exc

    logger.info(
        "Coach answered question for application id=%d user=%d",
        application.id,
        current_user.id,
    )
    return CoachResponse(answer=data["answer"])
