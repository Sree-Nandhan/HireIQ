import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import status as http_status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from api.auth import create_access_token, get_current_user, hash_password, verify_password
from api.config import settings
from api.database import get_db
from api.models import User
from api.schemas import GoogleAuthRequest, Token, UserCreate, UserResponse

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=Token, status_code=http_status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def register(request: Request, payload: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account and return a JWT access token.

    Raises **409** if the email is already in use.
    """
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("Registered new user id=%d email=%s", user.id, user.email)
    return Token(access_token=create_access_token(user.id, user.email))


@router.post("/login", response_model=Token)
@limiter.limit("20/minute")
def login(request: Request, payload: UserCreate, db: Session = Depends(get_db)):
    """
    Authenticate with email + password and return a JWT access token.

    Raises **401** for invalid credentials.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info("User id=%d logged in", user.id)
    return Token(access_token=create_access_token(user.id, user.email))


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user


@router.post("/google", response_model=Token)
@limiter.limit("20/minute")
def google_auth(request: Request, payload: GoogleAuthRequest, db: Session = Depends(get_db)):
    """
    Authenticate via Google Sign-In.

    Verifies the Google ID token, then either logs in an existing user or
    creates a new account (with a random secure password) and returns a JWT.

    Raises **400** if the token is invalid or GOOGLE_CLIENT_ID is not configured.
    """
    if not settings.google_client_id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Google Sign-In is not configured on this server.",
        )

    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token
        id_info = google_id_token.verify_oauth2_token(
            payload.credential,
            google_requests.Request(),
            settings.google_client_id,
        )
    except ValueError as exc:
        logger.warning("Google token verification failed: %s", exc)
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid Google credential.",
        ) from exc

    email: str = id_info.get("email", "")
    if not email:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Google token did not contain an email address.",
        )

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        random_password = secrets.token_hex(32)
        user = User(email=email, hashed_password=hash_password(random_password))
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Auto-created user via Google Sign-In id=%d email=%s", user.id, user.email)
    else:
        logger.info("Google Sign-In for existing user id=%d email=%s", user.id, user.email)

    return Token(access_token=create_access_token(user.id, user.email))
