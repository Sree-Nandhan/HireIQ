# HireIQ — Project Story

**Format:** STAR (Situation, Task, Action, Result)
**Date:** March 2026
**Author:** Sree Nandhan Prabhakar

---

## Table of Contents

1. [STAR Narrative](#star-narrative)
2. [Full Tech Stack](#full-tech-stack)
3. [Architecture Diagram](#architecture-diagram)
4. [Phase-by-Phase Breakdown](#phase-by-phase-breakdown)
5. [Key Engineering Decisions and Trade-offs](#key-engineering-decisions-and-trade-offs)
6. [Test Coverage Summary](#test-coverage-summary)
7. [Metrics and Highlights](#metrics-and-highlights)

---

## STAR Narrative

### Situation

The modern job application process is broken for candidates. Applicants routinely submit the same generic resume and cover letter to dozens of postings, only to be filtered out by Applicant Tracking Systems (ATS) before a human ever reads their materials. Industry research consistently shows that over 75% of resumes are rejected by ATS software before reaching a recruiter — not because the candidate is unqualified, but because their resume language does not align with the job description's specific keywords, structure, or phrasing. At the same time, preparing tailored materials for every application — rewriting bullets, crafting a custom cover letter, anticipating likely interview questions, and scoring one's own resume against a target role — is a multi-hour manual process that most candidates either cannot afford the time for or do not know how to do well.

Existing tools in this space fell into two categories: shallow keyword-matching utilities that produce a single score with no actionable output, or expensive one-on-one career coaching services priced out of reach for most job seekers. There was a clear gap for an intelligent, automated system that could perform the deep analytical work of a senior career coach — gap analysis, resume tailoring, cover letter generation, and interview preparation — for any resume and any job description, at scale, in seconds.

The broader technical opportunity was equally compelling: the maturation of large language models, retrieval-augmented generation (RAG) tooling, and multi-agent orchestration frameworks like LangGraph had made it feasible to build a production-grade, coordinated pipeline of specialized AI agents — each owning a distinct task — without any single agent needing to do everything. This was an ideal application for a supervisor-worker multi-agent architecture backed by a real persistent API.

### Task

The goal was to design and build HireIQ — a production-ready, full-stack, multi-agent career intelligence system — from scratch. The system needed to do all of the following in a single automated pipeline: parse a candidate's resume into structured data, analyze a target job description to extract requirements, perform a gap analysis identifying matched and missing skills, rewrite resume bullets tailored to the role, generate a personalized cover letter, produce role-specific interview Q&A pairs, and output an ATS compatibility score with actionable improvement suggestions.

Beyond the core AI pipeline, the system needed to function as a real product: a FastAPI backend with a PostgreSQL database to persist job applications and analysis history, a full authentication system using JWT tokens, rate limiting to prevent abuse, real-time streaming of pipeline progress via Server-Sent Events, a conversational coaching endpoint for follow-up questions, resume PDF upload and text extraction, and a React frontend with protected routes, a job tracker, and a results dashboard. The system also needed to be fully containerized with Docker Compose and covered by a CI/CD pipeline enforcing a coverage gate above 90%.

The engineering constraints were strict: all LLM calls had to go through LangChain abstractions, no credentials could be hard-coded, every agent node had to handle its own exceptions without crashing the graph, and all new API endpoints required Pydantic request and response models. The architecture had to remain extensible through clearly defined phases — foundation, testing, authentication, enhanced AI, frontend, and production readiness — with each phase building cleanly on the last.

### Action

The project was executed across six sequential phases. Phase 0 established the complete foundation: the repository structure was scaffolded as a monorepo with separate `services/api`, `services/agents`, and `services/frontend` directories, each with its own Dockerfile and requirements. The LangGraph pipeline was the architectural centerpiece. A `StateGraph` was built with a `supervisor` node as the entry point and seven specialized agent nodes — `resume_parser`, `jd_analyst`, `gap_analyst`, `resume_tailor`, `cover_letter`, `interview_coach`, and `ats_scorer`. Each agent node communicated through a shared `AgentState` TypedDict, with the supervisor using conditional edges to route execution based on a `completed_agents` list, ensuring deterministic sequential processing. ChromaDB was integrated as a vector store using HuggingFace's `all-MiniLM-L6-v2` embedding model for RAG-backed analysis — resume and job description text was embedded and indexed, allowing agents to query for semantically similar past content. The FastAPI api-service was built with SQLAlchemy ORM models for `User`, `JobApplication`, and `AnalysisResult`, with a `docker-compose.yml` orchestrating all four services with proper health checks and dependency ordering.

Phase 1 delivered a comprehensive test suite with 91 tests across both services. Agent node tests used `unittest.mock` to patch `ChatAnthropic` and ChromaDB calls, verifying both happy paths and failure modes — critically confirming that RAG failures are swallowed without aborting the pipeline, and that LLM failures set `state["error"]` without raising exceptions. API tests used FastAPI's `TestClient` with an in-memory SQLite database via SQLAlchemy, mocking the agent service HTTP calls with `unittest.mock.patch`. Tests covered CRUD operations, ownership scoping (user A cannot access user B's data), error propagation (502, 504, 404), and SSE streaming event structure. Phase 2 implemented full JWT authentication: bcrypt password hashing, HS256 token signing, a `get_current_user` FastAPI dependency injected into all protected routes, and rate-limited register/login endpoints at 10 and 20 requests per minute respectively.

Phase 3 delivered the enhanced AI features. Server-Sent Events streaming was implemented via `graph.astream_events()` with a `v2` event protocol, emitting per-agent completion events with step counts and a final pipeline-done event. Token tracking was implemented as a custom `AsyncCallbackHandler` subclass (`TokenTracker`) injected into every `graph.ainvoke()` call via LangChain's callbacks system, accumulating input and output token counts from `usage_metadata` on each LLM response. The conversational coaching endpoint (`POST /coach` on the agent service, proxied via `POST /api/v1/coach` on the API service) accepted a free-form question alongside the full analysis context and returned a grounded, actionable answer. PDF resume upload was added at `POST /api/v1/resume/extract` using `pypdf`, with size validation (5 MB cap), content-type checking, and a 422 response for image-only PDFs with no extractable text. Phase 4 built the React frontend with Vite: an `AuthContext` providing JWT storage and logout, protected routes for the tracker and analysis pages, an `AnalyzePage` with a resume text area and job description form that connects to the SSE stream for real-time progress, a `ResultsPage` rendering all pipeline outputs, and a `TrackerPage` for the kanban-style application lifecycle tracker. Phase 5 completed the production hardening: Alembic migrations for the initial schema, `slowapi` rate limiting on all auth endpoints, `X-API-Version` response headers from HTTP middleware, dual health check endpoints (`/health` for liveness and `/health/ready` for readiness, the latter probing both PostgreSQL and the agent service), and a GitHub Actions CI/CD pipeline running Python tests with a 93% coverage gate, a Node 22 frontend build, and parallel Docker image builds for all three services.

### Result

HireIQ is a production-grade, end-to-end AI career intelligence system deployed as a five-service Docker Compose stack. The LangGraph pipeline reliably orchestrates seven specialized AI agents in sequence, producing a complete career coaching analysis — gap report, tailored bullets, cover letter, interview prep, and ATS score — from any resume and job description input. The system handles agent failures gracefully: ChromaDB outages are swallowed by the pipeline without interrupting execution, and LLM failures set an error field rather than crashing the graph, ensuring the API always returns a usable response.

The test suite achieved 91 tests and 92% code coverage across both Python services, with the GitHub Actions CI pipeline enforcing a 93% coverage gate on every push to main. Integration tests verified full end-to-end flows including analysis persistence, ownership scoping, SSE event structure, and all error paths (502 for unreachable agent service, 504 for timeout, 404 for missing resources). The JWT authentication system correctly scopes all data to authenticated users, with bcrypt hashing, token expiry, and rate limiting protecting the auth endpoints. The React frontend provides a complete user experience from registration through analysis results, connected to the SSE stream for real-time progress feedback.

The architecture demonstrates several advanced engineering patterns in a single cohesive system: multi-agent LangGraph orchestration with a supervisor-worker model, RAG with vector embeddings for semantic document retrieval, custom LangChain callback handlers for cross-cutting token tracking, SSE streaming from an async generator through a LangGraph event bus, and a clean microservices split between a persistence-focused API service and a stateless AI-focused agent service. Every layer is containerized, environment-driven, and covered by automated tests — making HireIQ a robust showcase of modern AI-native full-stack engineering.

---

## Full Tech Stack

| Technology | Role / Purpose | Why It Was Chosen |
|---|---|---|
| **Python 3.12** | Primary backend language for both services | Type hinting improvements, `tomllib` stdlib, latest performance gains; best ecosystem for ML/AI libraries |
| **FastAPI** | REST API framework for both api-service and agent-service | Async-native, Pydantic-integrated, automatic OpenAPI docs, dependency injection system ideal for `get_current_user` patterns |
| **LangGraph** | Multi-agent pipeline orchestration | First-class `StateGraph` abstraction for supervisor-worker patterns; supports conditional edges, async execution, and event streaming via `astream_events` |
| **LangChain (langchain-core, langchain-anthropic)** | LLM abstraction layer; structured output; callback hooks | Vendor-agnostic LLM interface; `with_structured_output()` for typed Pydantic schema extraction; `AsyncCallbackHandler` for token tracking |
| **Claude claude-sonnet-4-6 (Anthropic)** | Core LLM for all 7 agent nodes + coach endpoint | State-of-the-art instruction following and structured JSON output; low hallucination rate on extraction tasks |
| **ChromaDB** | Vector store for resume and JD embeddings | Lightweight, embeddable, runs as a standalone Docker service; official `langchain-chroma` integration; persistent volume support |
| **HuggingFace all-MiniLM-L6-v2** | Sentence embedding model for RAG indexing | Small (22M params), fast, high-quality semantic similarity; runs locally without API calls via `langchain-huggingface` |
| **PostgreSQL 16** | Persistent relational storage for users, applications, and analysis results | ACID-compliant; JSON text columns for flexible analysis output storage; official Docker image with health check support |
| **SQLAlchemy** | Python ORM for database models and sessions | Declarative model syntax; relationship management with cascading deletes; compatible with both PostgreSQL (production) and SQLite (tests) |
| **Alembic** | Database schema migration tool | Industry-standard for SQLAlchemy projects; supports versioned migrations with rollback capability |
| **Pydantic v2** | Request/response schema validation and settings management | FastAPI-native; `model_validate()` for ORM object serialization; `BaseSettings` for environment variable loading with `.env` support |
| **bcrypt (passlib)** | Password hashing | Industry-standard adaptive hashing; resistant to brute-force via configurable work factor |
| **python-jose** | JWT token creation and verification | HS256 signing; `exp` claim enforcement; used for both token generation and test-side decoding |
| **httpx** | Async HTTP client for service-to-service calls | Async-native; supports `AsyncClient` context manager; used for api-service to agent-service proxy calls with configurable timeouts |
| **slowapi** | Rate limiting middleware | FastAPI-compatible; decorator-based per-endpoint limits; IP-based key function |
| **pypdf** | PDF text extraction for resume upload | Pure Python; no external binary dependencies; supports per-page text extraction |
| **uvicorn** | ASGI server | Standard FastAPI deployment server; production-grade with worker configuration |
| **React 18 + Vite** | Frontend SPA framework and build tool | Fast HMR for development; tree-shaken production builds; official Vite Docker pattern for containerized frontend |
| **React Router v6** | Client-side routing and protected routes | Declarative `<Routes>` and `<Navigate>` for auth-gated pages |
| **Docker + Docker Compose** | Service containerization and local orchestration | Reproducible environments; service dependency ordering via `depends_on` with `condition: service_healthy`; named volumes for data persistence |
| **GitHub Actions** | CI/CD pipeline | Native GitHub integration; matrix builds for parallel Docker image validation; pip cache action for fast dependency installs |
| **pytest** | Test runner for both Python services | Parameterized tests; fixture-based test isolation; `conftest.py` for shared setup |
| **pytest-cov** | Code coverage measurement and enforcement | Line coverage reports; `--cov-fail-under` for CI coverage gate |
| **pytest-asyncio** | Async test support | Required for testing async FastAPI endpoints and async agent node functions |
| **LangSmith** | Optional LLM call tracing and observability | `LANGCHAIN_TRACING_V2` env flag; project-scoped trace grouping; zero-code-change integration via environment variables |
| **SQLite (test)** | In-memory database for test isolation | `sqlite:///:memory:` URL; no external DB required in CI; SQLAlchemy-compatible drop-in for PostgreSQL tests |

---

## Architecture Diagram

```
                        ┌─────────────────────────────────────────────────────┐
                        │                   BROWSER CLIENT                    │
                        │          React + Vite SPA  (port 3000)              │
                        │                                                      │
                        │  AuthPage  ──►  TrackerPage  ──►  AnalyzePage       │
                        │                                        │             │
                        │                              SSE EventSource        │
                        │                             (real-time progress)    │
                        └────────────────────┬────────────────────────────────┘
                                             │  HTTP / SSE
                                             ▼
                        ┌────────────────────────────────────────────────────┐
                        │               API SERVICE  (port 8000)             │
                        │               FastAPI + Uvicorn                    │
                        │                                                    │
                        │  POST /api/v1/register   POST /api/v1/login        │
                        │  GET/POST/PATCH/DELETE /api/v1/applications        │
                        │  POST /api/v1/analyze                              │
                        │  GET  /api/v1/applications/{id}/analyses           │
                        │  POST /api/v1/coach                                │
                        │  POST /api/v1/resume/extract                       │
                        │  GET  /health              GET /health/ready        │
                        │                                                    │
                        │  ┌──────────────────────────────────────────────┐  │
                        │  │  Middleware Stack                            │  │
                        │  │  CORS  ──►  slowapi rate limiter  ──►        │  │
                        │  │  X-API-Version header middleware             │  │
                        │  └──────────────────────────────────────────────┘  │
                        │                                                    │
                        │  JWT Auth (python-jose + bcrypt)                   │
                        │  get_current_user() ── scopes all data to user     │
                        └────────────┬──────────────────────┬────────────────┘
                                     │  SQLAlchemy ORM       │  httpx async
                                     ▼                       ▼
              ┌──────────────────────────┐    ┌─────────────────────────────────┐
              │  PostgreSQL 16           │    │  AGENT SERVICE  (port 8001)     │
              │  (port 5432)             │    │  FastAPI + LangGraph            │
              │                          │    │                                 │
              │  users                   │    │  POST /analyze                  │
              │  job_applications        │    │  POST /analyze/stream  (SSE)    │
              │  analysis_results        │    │  POST /coach                    │
              │                          │    │  GET  /health                   │
              │  Volumes:                │    │                                 │
              │  postgres_data           │    │  TokenTracker callback          │
              └──────────────────────────┘    │  LangSmith tracing (optional)  │
                                              │                                 │
                                              │  ┌─────────────────────────┐   │
                                              │  │   LangGraph StateGraph  │   │
                                              │  │                         │   │
                                              │  │  ┌─────────────────┐    │   │
                                              │  │  │   SUPERVISOR    │    │   │
                                              │  │  │  (entry point)  │    │   │
                                              │  │  └────────┬────────┘    │   │
                                              │  │    conditional edges    │   │
                                              │  │  based on next_agent    │   │
                                              │  │           │             │   │
                                              │  │  ┌────────▼──────────┐  │   │
                                              │  │  │  resume_parser    │  │   │
                                              │  │  └────────┬──────────┘  │   │
                                              │  │  ┌────────▼──────────┐  │   │
                                              │  │  │   jd_analyst      │  │   │
                                              │  │  └────────┬──────────┘  │   │
                                              │  │  ┌────────▼──────────┐  │   │
                                              │  │  │   gap_analyst     │  │   │
                                              │  │  └────────┬──────────┘  │   │
                                              │  │  ┌────────▼──────────┐  │   │
                                              │  │  │  resume_tailor    │  │   │
                                              │  │  └────────┬──────────┘  │   │
                                              │  │  ┌────────▼──────────┐  │   │
                                              │  │  │  cover_letter     │  │   │
                                              │  │  └────────┬──────────┘  │   │
                                              │  │  ┌────────▼──────────┐  │   │
                                              │  │  │ interview_coach   │  │   │
                                              │  │  └────────┬──────────┘  │   │
                                              │  │  ┌────────▼──────────┐  │   │
                                              │  │  │   ats_scorer      │  │   │
                                              │  │  └────────┬──────────┘  │   │
                                              │  │        ◄──┘ (all nodes  │   │
                                              │  │    route back to        │   │
                                              │  │    supervisor)          │   │
                                              │  │           │             │   │
                                              │  │        END              │   │
                                              │  └─────────────────────────┘   │
                                              │                                 │
                                              │  Claude claude-sonnet-4-6       │
                                              │  (via langchain-anthropic)     │
                                              └──────────────┬──────────────────┘
                                                             │  langchain-chroma
                                                             ▼
                                              ┌──────────────────────────────┐
                                              │  ChromaDB  (port 8002)       │
                                              │                              │
                                              │  Vector store for resume     │
                                              │  and JD embeddings           │
                                              │                              │
                                              │  Embeddings:                 │
                                              │  HuggingFace                 │
                                              │  all-MiniLM-L6-v2            │
                                              │                              │
                                              │  Volumes: chroma_data        │
                                              └──────────────────────────────┘


  DATA FLOW SUMMARY
  ─────────────────
  1. User registers/logs in → JWT token issued
  2. User creates job application (company, JD, resume text) → persisted in PostgreSQL
  3. User optionally uploads PDF resume → pypdf extracts text → returned to client
  4. User triggers analysis → api-service proxies to agent-service /analyze
  5. Agent-service builds LangGraph state, runs 7-agent pipeline
  6. Each agent: LLM call (Claude) + optional ChromaDB RAG query
  7. TokenTracker callback accumulates input/output tokens across all LLM calls
  8. Pipeline result returned → api-service persists AnalysisResult → application status = "analyzed"
  9. (Streaming variant) /analyze/stream emits SSE progress events per agent via astream_events()
 10. User asks coaching question → api-service proxies to agent-service /coach → grounded LLM answer
```

---

## Phase-by-Phase Breakdown

### Phase 0 — Foundation (Completed)

**Goal:** Stand up the complete system skeleton before adding any features.

| Item | Description |
|------|-------------|
| Directory scaffold | Monorepo with `services/api`, `services/agents`, `services/frontend`, each with `Dockerfile` and `requirements.txt` |
| LangGraph pipeline | `StateGraph` with 8 nodes (supervisor + 7 agents); `AgentState` TypedDict with 14 typed fields; conditional routing via `next_agent` |
| ChromaDB RAG tool | `index_documents()` and `query_collection()` tools using `langchain-chroma` and HuggingFace embeddings |
| FastAPI api-service | Application entrypoint with CORS middleware, router mounting, structured logging |
| SQLAlchemy models | `User`, `JobApplication` (status lifecycle: pending → analyzed → applied → rejected / offered), `AnalysisResult` with JSON text columns |
| API routers | `/api/v1/applications` (CRUD) and `/api/v1/analyze` |
| Docker Compose | 4-service stack (api, agents, chromadb, postgres) with named volumes, health checks, and `depends_on` ordering |
| Pydantic Settings | `settings` objects in both services loading from `.env` via `BaseSettings` |
| Structured logging | `logging.basicConfig` with timestamp, level, logger name on both services |

### Phase 1 — Testing (Completed)

**Goal:** Achieve 80%+ coverage with isolated, reproducible tests requiring no external services.

| Test ID | Scope | Count | Key Patterns |
|---------|-------|-------|--------------|
| TEST-01 | pytest setup, conftest, SQLite in-memory fixture | — | `TestClient` with `get_db` override; pre-registered test user; Bearer token injected |
| TEST-02 | Unit tests for all 7 LangGraph nodes + supervisor | 30 tests | `@patch("agents.nodes.*.ChatAnthropic")`; verifies RAG failures are swallowed; LLM failures set `state["error"]` |
| TEST-03 | Integration tests for CRUD endpoints | 24 tests | Full lifecycle: create, list, paginate, filter, update status, delete; ownership scoping |
| TEST-04 | End-to-end analysis pipeline tests | 16 tests | `httpx` mocked with `unittest.mock`; 502/504/404 error paths; analysis persistence |
| TEST-05 | pytest-cov with 93% coverage gate | — | `--cov-fail-under=93` enforced in CI |

### Phase 2 — Authentication (Completed)

**Goal:** Scope all data to authenticated users with industry-standard JWT security.

| Item | Description |
|------|-------------|
| User model | `id`, `email` (unique, indexed), `hashed_password`, `is_active`, `created_at`; cascade-deletes applications |
| `POST /api/v1/register` | bcrypt hashes password; creates user; issues HS256 JWT; 409 on duplicate email; rate-limited 10/min |
| `POST /api/v1/login` | Verifies bcrypt hash; issues JWT; 401 on bad credentials; rate-limited 20/min |
| JWT middleware | `get_current_user()` FastAPI dependency decodes token, resolves User from DB; injected via `Depends()` on all protected routes |
| Ownership scoping | All CRUD and analysis queries filter by `user_id == current_user.id` |

### Phase 3 — Enhanced AI (Completed)

**Goal:** Enrich the AI pipeline with streaming, observability, coaching, and PDF support.

| Item | Description |
|------|-------------|
| SSE streaming | `POST /analyze/stream` uses `graph.astream_events(version="v2")`; emits per-agent progress events `{agent, status, step, total}` and a final `{agent: "pipeline", status: "done"}` event |
| Token tracking | `TokenTracker(AsyncCallbackHandler)` injected via `config={"callbacks": [tracker]}`; reads `usage_metadata` from each LLM generation; `input_tokens` and `output_tokens` persisted to `analysis_results` |
| Conversational coaching | `POST /api/v1/coach` proxies to `POST /coach` on agent-service; full analysis context injected as system prompt; 404 if no prior analysis exists |
| LangSmith tracing | `LANGCHAIN_TRACING_V2=true` activates tracing; env vars propagated to `os.environ` at startup for LangChain detection; project name configurable via `LANGCHAIN_PROJECT` |
| PDF resume upload | `POST /api/v1/resume/extract`; `pypdf.PdfReader` for text extraction; 5 MB size cap; content-type validation; 422 for image-only PDFs with no extractable text |

### Phase 4 — Frontend (Completed)

**Goal:** Deliver a complete user-facing SPA connecting all backend capabilities.

| Item | Description |
|------|-------------|
| React + Vite scaffold | `services/frontend/` with `Dockerfile` on port 3000; added to `docker-compose.yml` with `VITE_API_URL` env var |
| `AuthContext` | React context providing `token`, `login()`, `logout()`; JWT stored in `localStorage`; injected into all API calls |
| `AuthPage` | Register and login forms with toggle; stores token on success |
| `AnalyzePage` | Resume textarea + JD textarea; SSE `EventSource` for real-time agent progress bar; submits to `/api/v1/analyze` |
| `ResultsPage` | Renders all pipeline outputs: gap analysis skill chips, tailored bullets, cover letter, interview Q&A accordion, ATS score gauge |
| `TrackerPage` | Job application list with status badges; create new application form; navigate to results |
| Protected routes | `ProtectedRoute` HOC redirects unauthenticated users to `/auth` |

### Phase 5 — Production Readiness (Completed)

**Goal:** Harden the system for real deployment with migrations, observability, CI/CD, and rate protection.

| Item | Description |
|------|-------------|
| Alembic migrations | `services/api/alembic/` with `env.py` and initial schema migration `8b820607257d_initial_schema.py`; replaces `create_all()` for production-safe schema management |
| Rate limiting | `slowapi` integrated in api-service; `Limiter(key_func=get_remote_address)` on `app.state`; `@limiter.limit()` decorators on register/login |
| API version headers | `add_api_version_header` HTTP middleware attaches `X-API-Version: 1.0.0` to every response |
| Health checks | `GET /health` (liveness — always 200); `GET /health/ready` (readiness — probes PostgreSQL with `SELECT 1` and agent-service `/health`; returns 503 if either fails) |
| GitHub Actions CI | Three jobs: Python tests (93% coverage gate), Frontend build (Node 22, `npm ci && npm run build`), Docker image builds (matrix across api/agents/frontend); pip caching |

---

## Key Engineering Decisions and Trade-offs

### 1. Supervisor-Worker Multi-Agent Pattern over a Single Monolithic Agent

The LangGraph pipeline uses a supervisor node that routes to each specialist agent in sequence, with all agents returning to the supervisor after completion. This was chosen over a single large LLM call for several reasons: it enables per-step observability (each node's inputs and outputs are inspectable), allows individual nodes to fail without corrupting the entire state, and makes it straightforward to add, remove, or reorder agents. The trade-off is additional round-trips to the LLM (7 calls instead of 1), which increases latency and cost. This was accepted because the quality of structured outputs from focused single-task agents significantly exceeds what a single mega-prompt produces.

### 2. Shared TypedDict State with Supervisor Routing

`AgentState` is a flat `TypedDict` containing both inputs and all intermediate outputs. Each agent reads from and writes to this shared state. The supervisor inspects `completed_agents` to decide the next node. This avoids complex message-passing plumbing and makes the graph deterministic and debuggable. The trade-off is that the state object grows large as the pipeline progresses — this is acceptable for the current scale but would need pagination or summarization for very long resumes or JDs.

### 3. RAG Errors Are Swallowed by Agent Nodes

Every agent node that uses ChromaDB wraps the RAG call in a `try/except` and continues execution if it fails. This was a deliberate resilience decision: ChromaDB is an enhancement (providing historical context from previous analyses) but not a hard dependency for producing useful output. If ChromaDB is down or slow, the pipeline degrades gracefully to pure LLM inference rather than failing entirely. Tests explicitly verify this behavior.

### 4. Separate API Service and Agent Service

The api-service handles all persistence, authentication, and application lifecycle management. The agent-service is stateless and handles only LLM orchestration. This separation means the agent-service can be scaled independently of the API (LLM calls are the compute bottleneck), and the API service can be updated without redeploying the agent pipeline. The trade-off is an additional network hop and the complexity of timeout handling (120-second default, 504 on expiry).

### 5. SQLite in Tests, PostgreSQL in Production

All tests use `sqlite:///:memory:` via a `get_db` dependency override. This keeps tests hermetic — no Docker required in CI, instant setup/teardown, and full parallelism. The risk is SQLite dialect differences from PostgreSQL (e.g., `RETURNING` clause behavior, JSON types). This was mitigated by using SQLAlchemy's ORM exclusively (no raw SQL) and validating against real PostgreSQL via Docker in local development.

### 6. Token Tracking via Callback Handler, Not Middleware

`TokenTracker` is implemented as a `AsyncCallbackHandler` subclass rather than wrapping each LLM call site. This means token counting works automatically across all 7 agents without any per-node changes. The handler reads `usage_metadata` from the Anthropic response object, which is populated by `langchain-anthropic` automatically. This pattern is also future-proof: adding new agent nodes automatically gets token tracking with no additional code.

### 7. SSE Streaming Uses Two Graph Invocations

The `/analyze/stream` endpoint first streams events via `graph.astream_events()` and then calls `graph.ainvoke()` a second time to get the final compiled state. This is a pragmatic choice given that `astream_events` does not return the final aggregated state in the same call. The trade-off is that the graph runs twice for the streaming endpoint, doubling LLM cost. In a production optimization, the final state could be extracted from the stream's last event rather than re-invoking.

---

## Test Coverage Summary

### Overall: 91 tests, 92% coverage (CI gate: 93%)

| Test Module | Tests | Scope | Key Assertions |
|-------------|-------|-------|----------------|
| `agents/tests/test_nodes.py` | 30 | Unit: all 7 agent nodes + supervisor | Happy path output shapes; RAG failure resilience; LLM error → `state["error"]`; supervisor routing (first agent, middle, last, all-done) |
| `agents/tests/test_sse.py` | 5 | Integration: SSE streaming endpoint | 7 progress events for 7 agents; correct `step`/`total` fields; non-agent events ignored; final `done` event with `match_percentage`; `text/event-stream` content-type |
| `api/tests/test_auth.py` | 8 | Integration: register + login | Token returned on register; 409 on duplicate email; 401 on wrong password; JWT payload contains `sub`, `email`, `exp` |
| `api/tests/test_applications.py` | 24 | Integration: full CRUD lifecycle | Create/list/get/update/delete; pagination; status filter; ownership scoping (user B cannot see/delete user A's data); health endpoint |
| `api/tests/test_analyze.py` | 16 | Integration: analysis pipeline | Result persistence; ATS score extraction from dict; status updated to "analyzed"; multiple analyses stored; 502/504/404 error paths; analyses ordered newest-first |
| `api/tests/test_coach.py` | 6 | Integration: coaching endpoint | Answer returned; 404 no app; 404 no prior analysis; 502 agent unreachable; 504 timeout; 422 missing question |
| `api/tests/test_resume.py` | 7 | Integration: PDF upload | 400 non-PDF; 400 oversized; 422 image-only; 200 with text+pages; 401 unauthenticated; 422 missing file; octet-stream accepted |

### Test Infrastructure

- **conftest.py (api):** SQLite in-memory engine, `Base.metadata.create_all`, pre-registered test user, `TestClient` with `Authorization: Bearer` header injected, `get_db` dependency override
- **conftest.py (agents):** `mock_graph` fixture patching `agents.main.graph` with a configurable `MagicMock`
- **Mocking strategy:** `unittest.mock.patch` for all external calls — `ChatAnthropic`, `index_documents`, `query_collection`, `httpx.AsyncClient`
- **CI command:** `python -m pytest --no-header -q` with `DATABASE_URL=sqlite:///:memory:`

---

## Metrics and Highlights

### Codebase Scale

| Metric | Value |
|--------|-------|
| Python source files | 43 (excluding `__init__.py`, `__pycache__`, node_modules) |
| React/JSX source files | 7 |
| Total Python test files | 7 |
| Total tests | 91 |
| Code coverage | 92% |
| CI coverage gate | 93% |
| Docker Compose services | 5 (api, agents, chromadb, postgres, frontend) |

### API Surface

| Service | Endpoint | Method | Description |
|---------|----------|--------|-------------|
| api-service | `/api/v1/register` | POST | User registration + JWT |
| api-service | `/api/v1/login` | POST | Authentication + JWT |
| api-service | `/api/v1/applications` | POST | Create job application |
| api-service | `/api/v1/applications` | GET | List applications (pagination, status filter) |
| api-service | `/api/v1/applications/{id}` | GET | Get application detail + analyses |
| api-service | `/api/v1/applications/{id}/status` | PATCH | Update application status |
| api-service | `/api/v1/applications/{id}` | DELETE | Delete application (cascades analyses) |
| api-service | `/api/v1/analyze` | POST | Trigger multi-agent analysis |
| api-service | `/api/v1/applications/{id}/analyses` | GET | List analyses (newest first) |
| api-service | `/api/v1/coach` | POST | Conversational coaching Q&A |
| api-service | `/api/v1/resume/extract` | POST | PDF resume text extraction |
| api-service | `/health` | GET | Liveness probe |
| api-service | `/health/ready` | GET | Readiness probe (DB + agent-service) |
| agent-service | `/analyze` | POST | Full pipeline (synchronous) |
| agent-service | `/analyze/stream` | POST | Full pipeline with SSE streaming |
| agent-service | `/coach` | POST | Follow-up coaching answer |
| agent-service | `/health` | GET | Liveness probe |

**Total endpoints:** 17 across 2 services

### LangGraph Pipeline

| Agent | Input | Output |
|-------|-------|--------|
| `supervisor` | `completed_agents` list | `next_agent` routing decision |
| `resume_parser` | `resume_text` | `resume_parsed` (structured: name, email, skills, experience, education, summary) |
| `jd_analyst` | `job_description` | `jd_parsed` (structured: title, company, required/nice-to-have skills, responsibilities, keywords) |
| `gap_analyst` | `resume_parsed`, `jd_parsed` + ChromaDB RAG | `gap_analysis` (matching/missing/partial skills, match_percentage, summary) |
| `resume_tailor` | `resume_parsed`, `jd_parsed`, `gap_analysis` | `tailored_bullets` (list of original → tailored pairs with reasoning) |
| `cover_letter` | `resume_parsed`, `jd_parsed`, `gap_analysis` | `cover_letter` (full text) |
| `interview_coach` | `resume_parsed`, `jd_parsed`, `gap_analysis` | `interview_qa` (question, type: behavioral/technical, model_answer) |
| `ats_scorer` | `resume_parsed`, `jd_parsed`, `tailored_bullets` | `ats_score` (score 0-100, keyword_matches, keyword_misses, formatting_suggestions, overall_assessment) |

### Database Schema

| Table | Columns | Key Relationships |
|-------|---------|-------------------|
| `users` | id, email, hashed_password, is_active, created_at | One-to-many with job_applications |
| `job_applications` | id, user_id, company, job_title, job_description, resume_text, status, created_at, updated_at | Many-to-one with users; One-to-many with analysis_results |
| `analysis_results` | id, application_id, session_id, ats_score, match_percentage, gap_analysis (JSON), tailored_bullets (JSON), cover_letter, interview_qa (JSON), input_tokens, output_tokens, created_at | Many-to-one with job_applications |

### Frontend Pages

| Page | Route | Purpose |
|------|-------|---------|
| `AuthPage` | `/auth` | Register / login toggle with JWT storage |
| `TrackerPage` | `/tracker` | List all applications with status; create new |
| `AnalyzePage` | `/analyze` | Resume + JD input; SSE progress; trigger analysis |
| `ResultsPage` | `/results/:id` | Full analysis output dashboard |

### CI/CD Pipeline (GitHub Actions)

| Job | Trigger | Steps |
|-----|---------|-------|
| Python Tests | push/PR to main | Python 3.12 setup → pip cache → install api + agents deps → pytest with 93% coverage gate |
| Frontend Build | push/PR to main | Node 22 setup → npm cache → `npm ci` → `npm run build` |
| Docker Build (api) | push/PR to main | `docker build -t hireiq-api:ci ./services/api` |
| Docker Build (agents) | push/PR to main | `docker build -t hireiq-agents:ci ./services/agents` |
| Docker Build (frontend) | push/PR to main | `docker build -t hireiq-frontend:ci ./services/frontend` |

---

*This document was generated as a portfolio and engineering review artifact for the HireIQ project.*
