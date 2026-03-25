import json
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_validator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_json_field(value: Any) -> Any:
    """Return parsed JSON if *value* is a string, otherwise pass it through."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value
    return value


# ---------------------------------------------------------------------------
# JobApplication schemas
# ---------------------------------------------------------------------------

class JobApplicationCreate(BaseModel):
    """Payload for creating a new job application."""

    company: str
    job_title: str
    job_description: str
    resume_text: str


class JobApplicationResponse(BaseModel):
    """Lightweight response returned in list views."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    company: str
    job_title: str
    status: str
    created_at: datetime
    # Convenience fields populated from the latest analysis (may be absent)
    ats_score: Optional[int] = None
    match_percentage: Optional[float] = None


class JobApplicationDetail(JobApplicationResponse):
    """Full application detail including raw texts and all analyses."""

    job_description: str
    resume_text: str
    analyses: list["AnalysisResultResponse"] = []


# ---------------------------------------------------------------------------
# AnalysisResult schemas
# ---------------------------------------------------------------------------

class AnalysisResultResponse(BaseModel):
    """Analysis result returned to callers, with JSON strings decoded to native types."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: str
    ats_score: Optional[int] = None
    ats_details: Optional[dict] = None
    match_percentage: Optional[float] = None
    gap_analysis: Optional[dict] = None
    tailored_bullets: Optional[list] = None
    cover_letter: Optional[str] = None
    interview_qa: Optional[list] = None
    company_research: Optional[dict] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    created_at: datetime

    # ------------------------------------------------------------------
    # Field validators: transparently decode JSON strings stored in the DB
    # ------------------------------------------------------------------

    @field_validator("ats_details", mode="before")
    @classmethod
    def parse_ats_details(cls, v: Any) -> Optional[dict]:
        parsed = _parse_json_field(v)
        return parsed if isinstance(parsed, dict) else parsed

    @field_validator("gap_analysis", mode="before")
    @classmethod
    def parse_gap_analysis(cls, v: Any) -> Optional[dict]:
        """Decode gap_analysis from a JSON string if necessary."""
        parsed = _parse_json_field(v)
        if parsed is None:
            return None
        if isinstance(parsed, dict):
            return parsed
        # Unexpected type — surface it as-is and let Pydantic report the error
        return parsed

    @field_validator("tailored_bullets", mode="before")
    @classmethod
    def parse_tailored_bullets(cls, v: Any) -> Optional[list]:
        """Decode tailored_bullets from a JSON string if necessary."""
        parsed = _parse_json_field(v)
        if parsed is None:
            return None
        if isinstance(parsed, list):
            return parsed
        return parsed

    @field_validator("interview_qa", mode="before")
    @classmethod
    def parse_interview_qa(cls, v: Any) -> Optional[list]:
        """Decode interview_qa from a JSON string if necessary."""
        parsed = _parse_json_field(v)
        if parsed is None:
            return None
        if isinstance(parsed, list):
            return parsed
        return parsed

    @field_validator("company_research", mode="before")
    @classmethod
    def parse_company_research(cls, v: Any) -> Optional[dict]:
        """Decode company_research from a JSON string if necessary."""
        parsed = _parse_json_field(v)
        if parsed is None:
            return None
        if isinstance(parsed, dict):
            return parsed
        return parsed


# ---------------------------------------------------------------------------
# Coach schemas
# ---------------------------------------------------------------------------

class CoachRequest(BaseModel):
    """Request body for the conversational coach endpoint."""
    application_id: int
    question: str


class CoachResponse(BaseModel):
    """Answer returned by the career coach."""
    answer: str


# ---------------------------------------------------------------------------
# Action schemas
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Auth schemas
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    """Payload for registering a new user."""
    email: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserResponse(BaseModel):
    """Public user info returned after register / in profile calls."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    created_at: datetime


class Token(BaseModel):
    """JWT bearer token returned after successful login or register."""
    access_token: str
    token_type: str = "bearer"


class GoogleAuthRequest(BaseModel):
    """Payload for Google Sign-In — contains the Google ID token credential."""
    credential: str


class AnalyzeRequest(BaseModel):
    """Request body for triggering the agent analysis pipeline."""

    application_id: int


class StatusUpdate(BaseModel):
    """Request body for updating the lifecycle status of an application."""

    status: str  # one of: pending / analyzed / applied / rejected / offered
