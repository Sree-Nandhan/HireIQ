# HireIQ — Multi-Agent Career Intelligence System

LangGraph-powered multi-agent pipeline that analyzes resumes vs job descriptions and generates gap analysis, tailored bullets, cover letters, interview prep, and ATS scoring.

---

## Usage Tracking

**IMPORTANT — Claude must ALWAYS report token usage after every response that involves code changes, using this format:**

```
[Usage] Input: X tokens | Output: Y tokens | Session total: ~Z tokens
```

When running multi-agent tasks, report per-agent usage separately. Example:

```
[Usage] ResumeParser — Input: 1,200 tokens | Output: 340 tokens
[Usage] GapAnalyst   — Input: 2,100 tokens | Output: 520 tokens
[Usage] Session total: ~4,160 tokens
```

---

## Architecture Overview

```
Services:
- api-service       (port 8000) — FastAPI + PostgreSQL. Job application CRUD + analysis history
- agent-service     (port 8001) — LangGraph multi-agent pipeline. Core AI logic
- chromadb          (port 8002) — Vector store for resume/JD embeddings
- db (PostgreSQL)   (port 5432) — Persistent storage

LangGraph Pipeline (agent-service):
  Supervisor → ResumeParser → JDAnalyst → GapAnalyst →
  ResumeTailor → CoverLetter → InterviewCoach → ATSScorer → END

LLM: Claude API (claude-sonnet-4-6) via langchain-anthropic
Embeddings: HuggingFace all-MiniLM-L6-v2 via langchain-huggingface
Vector Store: ChromaDB (langchain-chroma)
```

---

## Task Board

### Phase 0 — Completed (Foundation)

- [x] Project directory scaffold
- [x] LangGraph agent pipeline (state, graph, all 7 agent nodes)
- [x] ChromaDB RAG tool + HF embeddings
- [x] FastAPI API service with PostgreSQL
- [x] SQLAlchemy models: JobApplication, AnalysisResult
- [x] Routers: /api/v1/applications (CRUD), /api/v1/analyze
- [x] docker-compose.yml (api + agents + chromadb + postgres)
- [x] Pydantic Settings with .env support
- [x] CORS middleware on both services
- [x] Structured logging

### Phase 1 — Pending: Testing

- [ ] TEST-01: pytest setup for both services
- [ ] TEST-02: Unit tests for all LangGraph node functions (mock LLM)
- [ ] TEST-03: Integration tests for API CRUD endpoints
- [ ] TEST-04: End-to-end test for /analyze pipeline
- [ ] TEST-05: pytest-cov with 80% coverage gate

### Phase 2 — Pending: Authentication

- [ ] AUTH-01: User model (id, email, hashed_password, created_at)
- [ ] AUTH-02: POST /api/v1/register and POST /api/v1/login → JWT tokens
- [ ] AUTH-03: JWT middleware (Depends(get_current_user)) on all protected routes
- [ ] AUTH-04: Scope applications to authenticated user

### Phase 3 — Pending: Enhanced AI

- [ ] AI-01: Stream LangGraph execution events via SSE (Server-Sent Events)
- [ ] AI-02: Add token/cost tracking per analysis session (log input_tokens, output_tokens to DB)
- [ ] AI-03: POST /api/v1/coach — conversational follow-up Q&A about the analysis
- [ ] AI-04: LangSmith tracing integration (LANGCHAIN_TRACING_V2=true)
- [ ] AI-05: Resume PDF upload support (PyPDF2 extraction)

### Phase 4 — Pending: Frontend

- [ ] FE-01: React + Vite scaffold in services/frontend/
- [ ] FE-02: Upload resume + paste JD form
- [ ] FE-03: Real-time progress indicator (SSE stream of agent steps)
- [ ] FE-04: Results dashboard: gap analysis, tailored bullets, cover letter, interview Q&A, ATS score
- [ ] FE-05: Job application tracker (kanban or list view)
- [ ] FE-06: Add frontend to docker-compose (port 3000)

### Phase 5 — Pending: Production Readiness

- [ ] PROD-01: Proper Alembic migrations
- [ ] PROD-02: Rate limiting (slowapi)
- [ ] PROD-03: API versioning and deprecation headers
- [ ] PROD-04: Health check endpoints with DB/ChromaDB connectivity checks
- [ ] PROD-05: GitHub Actions CI/CD pipeline (lint + test + build)

---

## Known Issues Log

| ID | File | Issue | Status |
|----|------|-------|--------|
| —  | —    | No issues yet | — |

---

## Dev Guidelines

- **Running the stack:** `docker-compose up --build`
- Never hard-code credentials — use `.env`
- All new endpoints need Pydantic request + response models
- LLM calls must go through LangChain abstractions (not raw httpx to Claude API)
- Use `from api.config import settings` / `from agents.config import settings` for env vars
- Agent nodes must catch exceptions and set `state["error"]` without crashing the graph

---

## Environment Variables Required

Create a `.env` file at the project root with the following variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key for LLM calls |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `AGENT_SERVICE_URL` | Yes | URL of the agent-service (e.g. http://agent-service:8001) |
| `CHROMA_HOST` | Yes | ChromaDB host (e.g. chromadb) |
| `LANGCHAIN_TRACING_V2` | Optional | Set to `true` to enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | Optional | Required if LANGCHAIN_TRACING_V2 is true |
