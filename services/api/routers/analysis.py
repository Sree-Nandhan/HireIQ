import json
import logging
import uuid
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.config import settings
from api.database import get_db
from api.models import AnalysisResult, JobApplication, User
from api.schemas import AnalyzeRequest, AnalysisResultResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analysis"])

# Agent service calls involve LLM round-trips — allow generous timeout
AGENT_TIMEOUT_SECONDS = 600.0


def _to_json_str(value) -> str | None:
    """Serialize *value* to a JSON string for DB storage, or return None."""
    if value is None:
        return None
    if isinstance(value, str):
        return value  # already serialized
    return json.dumps(value)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/analyze", response_model=AnalysisResultResponse, status_code=status.HTTP_201_CREATED)
async def trigger_analysis(
    payload: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger the multi-agent analysis pipeline for a job application.

    1. Fetches the application from the database.
    2. Calls the agent service (`POST {agent_service_url}/analyze`) with the
       application's job description and resume text.
    3. Persists the returned analysis result in the database.
    4. Updates the application status to **analyzed**.

    The agent service call has a **120-second timeout** to accommodate LLM latency.

    Raises:
    - **404** if the application does not exist.
    - **502** if the agent service returns an error or is unreachable.
    - **500** for unexpected database errors.
    """
    # 1. Retrieve the application (must belong to the authenticated user) ----------
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with id={payload.application_id} not found.",
        )

    session_id = str(uuid.uuid4())
    logger.info(
        "Starting analysis session=%s for application id=%d (%s @ %s)",
        session_id,
        application.id,
        application.job_title,
        application.company,
    )

    # 2. Call the agent service --------------------------------------------------
    agent_payload = {
        "application_id": application.id,
        "session_id": session_id,
        "company": application.company,
        "job_title": application.job_title,
        "job_description": application.job_description,
        "resume_text": application.resume_text,
        "user_id": current_user.id,
    }

    try:
        async with httpx.AsyncClient(timeout=AGENT_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{settings.agent_service_url}/analyze",
                json=agent_payload,
            )
            response.raise_for_status()
            agent_data: dict = response.json()
    except httpx.TimeoutException as exc:
        logger.error("Agent service timed out for session=%s: %s", session_id, exc)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The agent service did not respond in time. Please retry later.",
        ) from exc
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Agent service returned HTTP %d for session=%s: %s",
            exc.response.status_code,
            session_id,
            exc.response.text,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Agent service error: {exc.response.text}",
        ) from exc
    except httpx.RequestError as exc:
        logger.error("Could not reach agent service for session=%s: %s", session_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach the agent service. Please check the service is running.",
        ) from exc

    # 3. Persist the analysis result ---------------------------------------------
    # ats_score from the agent is a dict {"score": int, ...}; the DB column is Integer.
    ats_score_raw = agent_data.get("ats_score")
    ats_score_int = ats_score_raw.get("score") if isinstance(ats_score_raw, dict) else ats_score_raw

    analysis = AnalysisResult(
        application_id=application.id,
        session_id=session_id,
        ats_score=ats_score_int,
        ats_details=_to_json_str(agent_data.get("ats_score")),
        match_percentage=agent_data.get("match_percentage"),
        gap_analysis=_to_json_str(agent_data.get("gap_analysis")),
        tailored_bullets=_to_json_str(agent_data.get("tailored_bullets")),
        cover_letter=agent_data.get("cover_letter"),
        input_tokens=agent_data.get("input_tokens", 0),
        output_tokens=agent_data.get("output_tokens", 0),
        interview_qa=_to_json_str(agent_data.get("interview_qa")),
        company_research=_to_json_str(agent_data.get("company_research")),
        created_at=datetime.utcnow(),
    )
    db.add(analysis)

    # 4. Update application status -----------------------------------------------
    application.status = "analyzed"

    try:
        db.commit()
        db.refresh(analysis)
        db.refresh(application)
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to persist analysis for session=%s: %s", session_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis completed but could not be saved. Please retry.",
        ) from exc

    logger.info(
        "Analysis saved: id=%d session=%s ats_score=%s match=%.1f%% tokens=in:%d/out:%d",
        analysis.id,
        session_id,
        analysis.ats_score,
        analysis.match_percentage or 0.0,
        analysis.input_tokens or 0,
        analysis.output_tokens or 0,
    )

    return AnalysisResultResponse.model_validate(analysis)


@router.get("/applications/{application_id}/analyses", response_model=list[AnalysisResultResponse])
def list_analyses(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all analysis results for a given job application, ordered newest first.

    Raises **404** if no application with the given id exists.
    """
    application = (
        db.query(JobApplication)
        .filter(JobApplication.id == application_id, JobApplication.user_id == current_user.id)
        .first()
    )
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with id={application_id} not found.",
        )

    analyses = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.application_id == application_id)
        .order_by(AnalysisResult.created_at.desc())
        .all()
    )

    logger.info("Listed %d analyses for application id=%d", len(analyses), application_id)
    return [AnalysisResultResponse.model_validate(a) for a in analyses]
