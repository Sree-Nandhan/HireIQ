import logging

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from api.config import settings
from api.database import engine, Base
import api.models  # noqa: F401 — registers all models with Base
from api.routers import applications, analysis, auth, coach, resume

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

API_VERSION = "1.0.0"

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="HireIQ API",
    version=API_VERSION,
    description="Career intelligence API: manage job applications and trigger multi-agent analysis.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)


@app.on_event("startup")
def create_tables():
    try:
        Base.metadata.create_all(bind=engine)
        logging.getLogger(__name__).info("DB tables created/verified")
    except Exception as exc:
        logging.getLogger(__name__).warning("DB create_all failed at startup: %s", exc)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_api_version_header(request: Request, call_next):
    """Attach X-API-Version to every response for client version negotiation."""
    response = await call_next(request)
    response.headers["X-API-Version"] = API_VERSION
    return response


app.include_router(auth.router, prefix="/api/v1")
app.include_router(applications.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(coach.router, prefix="/api/v1")
app.include_router(resume.router, prefix="/api/v1")


@app.post("/api/v1/company-preview", tags=["analysis"])
async def company_preview_proxy(request: Request):
    """Proxy to agent-service /company-preview for quick company research during analysis."""
    body = await request.json()
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(f"{settings.agent_service_url}/company-preview", json=body)
        return JSONResponse(content=resp.json(), status_code=resp.status_code)


@app.get("/health", tags=["health"])
async def health():
    """Liveness check — always returns 200 if the process is up."""
    return {"status": "ok", "service": "api", "version": API_VERSION}


@app.get("/health/ready", tags=["health"])
async def readiness():
    """
    Readiness check — verifies DB and agent-service connectivity.

    Returns **503** if any dependency is unavailable.
    """
    errors: dict[str, str] = {}

    # Check PostgreSQL
    try:
        from api.database import engine
        with engine.connect() as conn:
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception as exc:
        errors["database"] = str(exc)

    # Check agent-service
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{settings.agent_service_url}/health")
            if resp.status_code != 200:
                errors["agent_service"] = f"HTTP {resp.status_code}"
    except Exception as exc:
        errors["agent_service"] = str(exc)

    if errors:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "errors": errors},
        )

    return {"status": "ready", "service": "api", "version": API_VERSION}
