# HireIQ — Multi-Agent Career Intelligence System

LangGraph-powered multi-agent pipeline that analyzes resumes vs job descriptions and generates gap analysis, tailored bullets, cover letters, and interview prep.

---

## Usage Tracking

**IMPORTANT — Claude must ALWAYS report token usage after every response that involves code changes, using this format:**

```
[Usage] Input: X tokens | Output: Y tokens | Session total: ~Z tokens
```

---

## Architecture Overview

```
Services:
- api-service       (port 8000) — FastAPI + PostgreSQL. Job application CRUD + analysis history
- agent-service     (port 8001) — LangGraph multi-agent pipeline. Core AI logic
- chromadb          (port 8002) — Vector store for resume/JD embeddings
- db (PostgreSQL)   (port 5432) — Persistent storage

LangGraph Pipeline (7 nodes):
  Supervisor → ResumeParser → JDAnalyst → CompanyResearcher →
  GapAnalyst → ResumeTailor → CoverLetter → InterviewCoach → END

LLM: Groq API (llama-3.3-70b-versatile) via GeminiClient wrapper
Embeddings: HuggingFace all-MiniLM-L6-v2
Vector Store: ChromaDB
```

---

## Deployment

| Service | Platform | URL |
|---------|----------|-----|
| Frontend | Vercel | hire-iq-brown.vercel.app |
| API | Railway (hireiq-api) | hireiq-api-production.up.railway.app |
| Agents | Railway (hireiq-agents) | internal Railway network |
| PostgreSQL | Railway (hireiq-db) | internal Railway network |

**Railway project:** `diligent-integrity`

---

## Completed Work

### Auth
- [x] OTP-based passwordless auth (no email — OTP returned in API response, displayed on screen)
- [x] JWT tokens, session expiry handling
- [x] Auto-create user on first OTP request

### Agent Pipeline
- [x] 7-node LangGraph pipeline (ATS scorer removed — was redundant with gap analysis)
- [x] Gap analyst: deterministic skill matching with 60+ alias dictionary, weighted match % (required skills 2x weight)
- [x] Formatting tips folded into gap_analysis output (formatting_tips field)
- [x] Groq model: `llama-3.3-70b-versatile` (switched from decommissioned gemma2-9b-it)
- [x] Groq json_mode fix: auto-injects "json" keyword into prompts when required
- [x] Token tracking across all nodes

### Frontend (React + Vite on Vercel)
- [x] Auth page with OTP flow, displays OTP on screen
- [x] Tracker page — job application list
- [x] Results page — 4 tabs: Gap Analysis, Tailored Bullets, Cover Letter, Interview Q&A
- [x] Gap Analysis tab: match ring, AI summary, skill chips, partial matches, formatting tips
- [x] Tailored bullets: editable, copy per bullet, copy all, download
- [x] Cover letter: copy + download
- [x] Interview Q&A: questions with model answers
- [x] ATS Score tab removed (was duplicate of gap analysis)
- [x] Match % ring removed from header (shown only in Gap Analysis tab)
- [x] SSE simulated progress bar (7 steps)

### API
- [x] CRUD: /api/v1/applications
- [x] POST /api/v1/analyze — blocking analysis
- [x] POST /api/v1/analyze/stream — SSE streaming
- [x] GET /api/v1/applications/:id/analyses — history
- [x] POST /api/v1/coach — LLM follow-up Q&A on analysis
- [x] GET /health, /health/ready

### Database
- [x] OTP columns added manually via Railway psql (otp_hash, otp_expires_at, otp_attempts)
- [x] hashed_password made nullable for OTP-only users
- [x] ats_score / ats_details columns kept in DB but no longer written to (nullable, no migration needed)

---

## Known Limitations

| Issue | Detail | Fix |
|-------|--------|-----|
| Groq free tier TPD | 100k tokens/day — ~3-4 users/day before hitting limit | Upgrade to Groq Dev tier ($9/mo) for 500k TPD |
| Coach uses LLM | POST /coach fails when Groq TPD exhausted | Same fix as above |
| No email delivery | OTP shown on screen (Railway blocks SMTP) | Add Resend API key when ready |

---

## Dev Guidelines

- Never hard-code credentials — use `.env`
- All new endpoints need Pydantic request + response models
- LLM calls go through `GeminiClient` in `services/agents/tools/gemini.py` (Groq backend)
- Agent nodes must catch exceptions and set `state["error"]` without crashing the graph
- Groq requires the word "json" in the prompt when using json_mode — handled automatically in GeminiClient.invoke()
- `create_all()` only creates missing tables, never adds columns — use psql for column additions

---

## Environment Variables

### Railway — hireiq-api
| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET_KEY` | JWT signing secret |
| `AGENT_SERVICE_URL` | Internal URL of hireiq-agents |
| `GOOGLE_CLIENT_ID` | Optional — Google OAuth |

### Railway — hireiq-agents
| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Groq API key |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` |
| `DATABASE_URL` | PostgreSQL connection string |
| `CHROMA_HOST` | ChromaDB host |
