# HireIQ — How to Use

HireIQ is a multi-agent career intelligence system. You give it your resume and a job description; it runs a LangGraph pipeline powered by Claude and produces a gap analysis, tailored resume bullets, a cover letter, interview Q&A, and an ATS score.

There are two ways to interact with the system:

- **Mode 1 — Web UI:** open a browser, register, and use the React frontend.
- **Mode 2 — REST API:** call endpoints directly with curl, Postman, or any HTTP client.

---

## Quick Start in 5 Minutes

This is the fastest path to a working result.

**Step 1 — Prerequisites**

- Docker Desktop installed and running.
- An Anthropic API key (`sk-ant-...`). Get one at https://console.anthropic.com.

**Step 2 — Create the .env file**

In the project root (`/Users/sreenandhan/Desktop/HireIQ/`), create a file named `.env`:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

That single variable is all that is required to boot the full stack. The remaining environment variables (DATABASE_URL, AGENT_SERVICE_URL, CHROMA_HOST) are hard-wired in `docker-compose.yml` and do not need to be set manually.

**Step 3 — Start the stack**

```bash
cd /Users/sreenandhan/Desktop/HireIQ
docker-compose up --build
```

Wait until you see log lines from all four services: `db`, `chromadb`, `api-service`, and `agent-service`, plus `frontend`.

**Step 4 — Open the app**

Navigate to http://localhost:3000 in your browser.

**Step 5 — Register and run your first analysis**

1. Click "Register", enter any email and password, click "Create Account".
2. Click "+ New Analysis" in the top navigation.
3. Fill in Job Title, Company, and paste a job description.
4. Either upload a PDF resume or paste resume text.
5. Click "Analyze Application" and watch the progress bar as each agent completes.
6. You will be redirected to the Results dashboard automatically.

Total time from `docker-compose up` to first result: typically 3–5 minutes depending on PDF download time for the HuggingFace embedding model.

---

## Mode 1: Web UI (Frontend)

### Prerequisites

| Requirement | Version |
|-------------|---------|
| Docker Desktop | 4.x or later |
| Internet access | Required for the Claude API and HuggingFace model download |

A `.env` file at the project root with at minimum:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Optional LangSmith tracing (adds observability but is not required):

```
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__your-langsmith-key
```

### Starting the Stack

```bash
# From the project root
docker-compose up --build
```

On first boot, Docker pulls base images and the `agent-service` downloads the HuggingFace `all-MiniLM-L6-v2` embedding model (~90 MB). Subsequent starts are faster.

Service URLs once running:

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API service (Swagger docs) | http://localhost:8000/api/docs |
| Agent service | http://localhost:8001 |
| ChromaDB | http://localhost:8002 |

To stop the stack: `Ctrl+C`, then `docker-compose down`.
To also remove persisted data volumes: `docker-compose down -v`.

### Register / Sign In

When you open http://localhost:3000 you land on the Auth page.

- **Register:** click the "Register" tab, enter your email and password, click "Create Account". You are logged in immediately and receive a JWT token stored in the browser.
- **Sign In:** click the "Sign In" tab, enter your credentials, click "Sign In". Use this on return visits.

The auth endpoint rate-limits register to 10 requests/minute and login to 20 requests/minute per IP. If you see a 429 error, wait a moment and retry.

### Running a New Analysis

Click "+ New Analysis" (top navigation or the button on the Tracker page).

The form has four fields:

| Field | Required | Notes |
|-------|----------|-------|
| Job Title | Yes | e.g., "Senior Software Engineer" |
| Company | Yes | e.g., "Acme Corp" |
| Job Description | Yes | Paste the full text of the posting |
| Resume (PDF upload) | No — but resume text is required | PDF is parsed server-side; extracted text appears in the textarea below |
| Resume Text | Yes | Either upload a PDF (text fills automatically) or paste manually |

PDF requirements: text-based PDF only (not scanned images), maximum 5 MB.

Once all fields are filled, click "Analyze Application". The form submits, creates an application record, and triggers the agent pipeline.

### Understanding the SSE Progress Bar

After you click "Analyze Application" the UI switches to a streaming view. A progress bar advances as each agent in the LangGraph pipeline completes. The seven agents run in order:

| Step | Agent | What it does |
|------|-------|--------------|
| 1/7 | resume_parser | Extracts structured sections from your resume (skills, experience, education) |
| 2/7 | jd_analyst | Parses the job description into required skills, responsibilities, and qualifications |
| 3/7 | gap_analyst | Compares resume to JD, produces match percentage, matching skills, and missing skills |
| 4/7 | resume_tailor | Rewrites your experience bullets to align with the JD language and keywords |
| 5/7 | cover_letter | Drafts a personalized cover letter for the role |
| 6/7 | interview_coach | Generates likely interview questions and model answers based on your background |
| 7/7 | ats_scorer | Scores your application against ATS criteria (0–100) with feedback |

Each completed step shows a checkmark. When the pipeline finishes (or the API call returns), the browser automatically redirects to the Results dashboard.

If the page shows an error, the most common causes are: `ANTHROPIC_API_KEY` not set, the agent-service container not yet healthy, or a network timeout (the pipeline can take up to 120 seconds for long resumes/JDs).

### Reading the Results Dashboard

The Results page shows the job title and company at the top with a tabbed interface containing five sections.

**Tab 1 — Gap Analysis**

Shows your overall match percentage as a large badge (e.g., "78% Match"), then two columns side by side:

- Matching Skills: skills from your resume that appear in the JD (shown in green).
- Missing Skills: skills the JD requires that were not found in your resume (shown in red). These are your highest-priority areas to address before applying.

**Tab 2 — Tailored Bullets**

A list of rewritten resume bullet points. Each bullet has been rephrased by the AI to use the exact language, keywords, and action verbs from the job description. You can copy these directly into your resume. The bullets are grounded in your actual experience — the agent does not fabricate achievements.

**Tab 3 — Cover Letter**

A full, ready-to-send cover letter drafted for the specific role and company. It draws on the gap analysis to emphasize your strongest matching qualifications and briefly acknowledges areas where you are growing. Review it, personalize the opening salutation and any company-specific details, then copy it into your application.

**Tab 4 — Interview Q&A**

A list of likely interview questions for the role with suggested answers based on your resume. Each item has a "Q:" and "A:" pair. Use these for practice. The answers are starting points — adapt them to your actual stories and experiences before your interview.

**Tab 5 — ATS Score**

Shows your ATS (Applicant Tracking System) score out of 100 as a large badge, followed by written feedback explaining what raised or lowered the score (keyword density, formatting signals, section headings, etc.). At the bottom, the total Claude API tokens consumed for this analysis run are displayed (Input tokens / Output tokens) — useful for cost awareness.

### Using the Job Tracker

The Tracker page (http://localhost:3000/tracker) lists all applications you have created. It shows a table with Job Title, Company, Status, and Applied date.

**Status values and their meanings:**

| Status | Color | Meaning |
|--------|-------|---------|
| pending | Amber | Application created; analysis not yet run |
| analyzing | Blue | Pipeline is currently running |
| analyzed | Green | Analysis completed successfully |
| applied | Green | You have submitted the application externally |
| rejected | Red | You received a rejection |
| offered | Green | You received an offer |

**Filtering:** click a status button in the filter row to show only applications with that status. Click "All" to clear the filter. Filtering is server-side so it works correctly across pagination boundaries.

**Viewing results:** for any application with status "completed" (or "analyzed"), a "View Results" link appears in the row. Click it to go to the Results dashboard for that application.

**Creating a new analysis:** click "+ New Analysis" at the top right of the tracker.

### Running in Dev Mode (no Docker)

Use this workflow when you are making frontend or backend code changes and want hot-reload.

**Terminal 1 — Start infrastructure with Docker (database + chromadb only):**

```bash
cd /Users/sreenandhan/Desktop/HireIQ
docker-compose up db chromadb
```

**Terminal 2 — Start the agent service:**

```bash
cd /Users/sreenandhan/Desktop/HireIQ/services/agents
pip install -e .
uvicorn agents.main:app --host 0.0.0.0 --port 8001 --reload
```

**Terminal 3 — Start the API service:**

```bash
cd /Users/sreenandhan/Desktop/HireIQ/services/api
pip install -e .
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/hireiq \
AGENT_SERVICE_URL=http://localhost:8001 \
ANTHROPIC_API_KEY=sk-ant-your-key-here \
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 4 — Start the frontend with Vite dev server:**

```bash
cd /Users/sreenandhan/Desktop/HireIQ/services/frontend
npm install
npm run dev
```

The Vite config proxies all `/api` requests to `http://localhost:8000`, so the frontend communicates with the local API service transparently. Open http://localhost:3000.

---

## Mode 2: REST API (curl / Postman)

### Base URL

```
http://localhost:8000
```

All application endpoints are under `/api/v1/`. Interactive Swagger UI is available at:

```
http://localhost:8000/api/docs
```

ReDoc documentation is at:

```
http://localhost:8000/api/redoc
```

Every response includes an `X-API-Version: 1.0.0` header for client version negotiation.

### Authentication Flow

All application endpoints require a Bearer JWT token. The token is obtained by registering or logging in.

**Register a new account**

```bash
curl -s -X POST http://localhost:8000/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "supersecret"}' | jq .
```

Sample response (HTTP 201):

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

Error responses:
- `409 Conflict` — email already registered.
- `429 Too Many Requests` — rate limit exceeded (10 register requests/minute per IP).

**Log in with an existing account**

```bash
curl -s -X POST http://localhost:8000/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "supersecret"}' | jq .
```

Sample response (HTTP 200):

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

Error responses:
- `401 Unauthorized` — email not found or password incorrect.

**Store the token for subsequent requests**

```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

Pass it in the `Authorization` header on every protected request:

```
-H "Authorization: Bearer $TOKEN"
```

### Upload Resume PDF

Before creating an application you can extract plain text from a PDF resume. This step is optional — you can also paste resume text directly.

```bash
curl -s -X POST http://localhost:8000/api/v1/resume/extract \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/your-resume.pdf" | jq .
```

Sample response (HTTP 200):

```json
{
  "text": "Jane Doe\njane@example.com | linkedin.com/in/janedoe\n\nEXPERIENCE\n\nSoftware Engineer — Acme Corp (2021–2024)\n  • Built microservices in Python and Go...",
  "pages": 2
}
```

Constraints:
- File must be a text-based PDF (not a scanned image).
- Maximum size: 5 MB.
- Returns `400` if the file is not a PDF or exceeds 5 MB.
- Returns `422` if the PDF cannot be parsed or contains no extractable text.

Use the `text` value from this response as the `resume_text` field when creating an application.

### Create an Application

```bash
curl -s -X POST http://localhost:8000/api/v1/applications \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Acme Corp",
    "job_title": "Senior Software Engineer",
    "job_description": "We are looking for a senior engineer to lead backend systems...",
    "resume_text": "Jane Doe\n\nEXPERIENCE\nSoftware Engineer — Acme Corp (2021–2024)..."
  }' | jq .
```

Sample response (HTTP 201):

```json
{
  "id": 42,
  "company": "Acme Corp",
  "job_title": "Senior Software Engineer",
  "status": "pending",
  "created_at": "2026-03-24T10:15:00.000Z",
  "ats_score": null,
  "match_percentage": null
}
```

The `id` field is used in all subsequent requests for this application. Applications are scoped to the authenticated user — other users cannot see or modify yours.

### Trigger the Analysis Pipeline

Pass the `id` returned from the create step.

```bash
curl -s -X POST http://localhost:8000/api/v1/analyze \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"application_id": 42}' | jq .
```

This call is **synchronous but slow** — the API service forwards the request to the agent service which runs all seven LangGraph agents (LLM calls). Allow up to 120 seconds. The request will block until the full pipeline completes.

What happens internally:
1. The API service fetches the application from PostgreSQL.
2. It calls `POST http://agent-service:8001/analyze` with the resume and JD text.
3. The agent service runs the seven-node LangGraph graph (ResumeParser → JDAnalyst → GapAnalyst → ResumeTailor → CoverLetter → InterviewCoach → ATSScorer).
4. Results are written to the `analysis_results` table.
5. The application `status` is updated to `analyzed`.
6. The full analysis result is returned.

Sample response (HTTP 201):

```json
{
  "id": 7,
  "session_id": "f3a2b1c4-...",
  "ats_score": 74,
  "match_percentage": 0.81,
  "gap_analysis": {
    "match_percentage": 0.81,
    "matching_skills": ["Python", "REST APIs", "PostgreSQL", "Docker"],
    "missing_skills": ["Kubernetes", "Go"],
    "summary": "Strong backend match. Candidate lacks container orchestration experience."
  },
  "tailored_bullets": [
    "Designed and deployed RESTful microservices in Python (FastAPI) serving 500K daily requests",
    "Led migration of monolithic PostgreSQL schema to event-sourced architecture, reducing query latency by 40%"
  ],
  "cover_letter": "Dear Hiring Manager,\n\nI am excited to apply for the Senior Software Engineer role at Acme Corp...",
  "interview_qa": [
    {
      "question": "Tell me about a time you improved system performance.",
      "answer": "At my previous role I identified an N+1 query problem in our ORM layer..."
    }
  ],
  "input_tokens": 4821,
  "output_tokens": 1103,
  "created_at": "2026-03-24T10:18:42.000Z"
}
```

Error responses:
- `404` — application id not found or does not belong to the authenticated user.
- `504 Gateway Timeout` — agent service did not respond within 120 seconds.
- `502 Bad Gateway` — agent service returned an error or is not reachable.

### Retrieve Application Details and Analysis History

```bash
curl -s http://localhost:8000/api/v1/applications/42 \
  -H "Authorization: Bearer $TOKEN" | jq .
```

Sample response (HTTP 200):

```json
{
  "id": 42,
  "company": "Acme Corp",
  "job_title": "Senior Software Engineer",
  "status": "analyzed",
  "created_at": "2026-03-24T10:15:00.000Z",
  "ats_score": 74,
  "match_percentage": 0.81,
  "job_description": "We are looking for a senior engineer...",
  "resume_text": "Jane Doe\n\nEXPERIENCE...",
  "analyses": [
    {
      "id": 7,
      "session_id": "f3a2b1c4-...",
      "ats_score": 74,
      "match_percentage": 0.81,
      "gap_analysis": { ... },
      "tailored_bullets": [ ... ],
      "cover_letter": "Dear Hiring Manager...",
      "interview_qa": [ ... ],
      "input_tokens": 4821,
      "output_tokens": 1103,
      "created_at": "2026-03-24T10:18:42.000Z"
    }
  ]
}
```

The `analyses` array contains every analysis run for that application, ordered newest first by the API. You can run the pipeline multiple times on the same application (e.g., after updating your resume text) and all runs are preserved.

To list only the analyses for an application:

```bash
curl -s http://localhost:8000/api/v1/applications/42/analyses \
  -H "Authorization: Bearer $TOKEN" | jq .
```

### List All Applications

```bash
# All applications
curl -s "http://localhost:8000/api/v1/applications" \
  -H "Authorization: Bearer $TOKEN" | jq .

# Filter by status
curl -s "http://localhost:8000/api/v1/applications?status=analyzed" \
  -H "Authorization: Bearer $TOKEN" | jq .

# Pagination (page 2 with 10 per page)
curl -s "http://localhost:8000/api/v1/applications?limit=10&offset=10" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

Valid status filter values: `pending`, `analyzed`, `applied`, `rejected`, `offered`.

### Update Application Status

After you have submitted the real job application or heard back, update the status to track your pipeline:

```bash
curl -s -X PATCH http://localhost:8000/api/v1/applications/42/status \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "applied"}' | jq .
```

Valid values: `pending`, `analyzed`, `applied`, `rejected`, `offered`.

### Delete an Application

```bash
curl -s -X DELETE http://localhost:8000/api/v1/applications/42 \
  -H "Authorization: Bearer $TOKEN"
# Returns HTTP 204 No Content on success
```

This permanently deletes the application and all associated analysis results.

### Career Coach Q&A

After an analysis has been run, ask a follow-up question. The coach uses the full analysis context (resume, JD, gap analysis, cover letter, interview Q&A, ATS score) to give a grounded, specific answer.

```bash
curl -s -X POST http://localhost:8000/api/v1/coach \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "application_id": 42,
    "question": "How should I address my lack of Kubernetes experience in the interview?"
  }' | jq .
```

Sample response (HTTP 200):

```json
{
  "answer": "Since Kubernetes is listed as a missing skill in your gap analysis, you should address it proactively rather than waiting for the interviewer to bring it up. Frame it around your existing Docker and container experience: explain that you have built and deployed containerized services with Docker Compose and are actively working toward CKA certification. Emphasize your strong foundation in distributed systems and cite a specific example from your PostgreSQL migration work to show you understand the operational concerns that Kubernetes solves. Interviewers at this level generally respond well to candidates who are self-aware about gaps and have a concrete learning plan."
}
```

Requirements:
- The application must exist and belong to the authenticated user.
- At least one analysis must have been run on the application (returns `404` otherwise).

The coach endpoint has a 60-second timeout.

### Health Checks

**Liveness check** — returns 200 if the API process is running:

```bash
curl -s http://localhost:8000/health | jq .
```

```json
{"status": "ok", "service": "api", "version": "1.0.0"}
```

**Readiness check** — verifies PostgreSQL and agent-service connectivity:

```bash
curl -s http://localhost:8000/health/ready | jq .
```

Success (HTTP 200):

```json
{"status": "ready", "service": "api", "version": "1.0.0"}
```

Failure (HTTP 503) — one or more dependencies are down:

```json
{
  "status": "unavailable",
  "errors": {
    "database": "could not connect to server: Connection refused",
    "agent_service": "HTTP 503"
  }
}
```

The agent service also has its own liveness endpoint:

```bash
curl -s http://localhost:8001/health | jq .
```

```json
{"status": "ok", "service": "agent-service"}
```

### Interactive API Documentation

Open http://localhost:8000/api/docs in your browser for the full Swagger UI. You can:

- Browse all endpoints with request/response schemas.
- Click "Authorize" and paste your JWT token to make authenticated requests directly from the browser.
- Use "Try it out" on any endpoint to send real requests and inspect responses.

ReDoc (read-only, more readable layout): http://localhost:8000/api/redoc

---

## Troubleshooting

**"Could not reach the agent service"** — the agent-service container may still be starting. Check `docker-compose logs agent-service`. The HuggingFace model download must complete before the service is ready.

**"Only PDF files are accepted"** — ensure you are uploading a `.pdf` file, not a `.doc` or image file.

**"No text could be extracted"** — your PDF is likely a scanned image (rasterized). Use a text-based PDF or paste the resume text manually.

**Analysis takes more than 2 minutes** — the default timeout is 120 seconds. For very long resumes or job descriptions this may be exceeded. Try trimming the input to the most relevant content (2 pages of resume, full JD).

**"An account with this email already exists"** — use the Sign In tab instead of Register.

**Port conflicts** — if ports 3000, 8000, 8001, 8002, or 5432 are in use on your machine, stop the conflicting service or edit the `ports` mappings in `docker-compose.yml`.
