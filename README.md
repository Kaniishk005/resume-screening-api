# ResumeTrace API

Evidence-backed resume–job intelligence API built using **FastAPI**, **SQLAlchemy**, **JWT authentication**, and **Groq**. The API lets recruiters create job descriptions, upload resumes, calculate deterministic document-alignment scores, inspect evidence gaps, and generate grounded advisory feedback.

---

## 🌐 Live Demo

**API Base URL**

https://resume-screening-api-z2fi.onrender.com

**Swagger Documentation**

https://resume-screening-api-z2fi.onrender.com/docs

---

# ✨ Features

### 👤 Recruiter Authentication
- JWT Authentication
- Secure Password Hashing (bcrypt)
- Register/Login APIs
- Protected Routes

### 💼 Job Management
- Create Job
- View All Jobs
- View Single Job
- Delete Job

### 📄 Resume Parsing
- Upload Resume (PDF)
- Extract Candidate Name
- Extract Email
- Extract Phone Number
- Extract Technical Skills

### 📊 ATS Score Analysis
- Skill Matching
- ATS Score Calculation
- Match Percentage
- Missing Skills Detection

### 🤖 AI Feedback
Powered by the configured **Groq** model

Generates

- Resume Summary
- Strengths
- Weaknesses
- Conditional Resume-Improvement Recommendations

### 📚 Analysis History

Stores every resume analysis including

- ATS Score
- Match Percentage
- Skills Matched
- Missing Skills
- AI Feedback

---

# 🛠 Tech Stack

## Backend

- FastAPI
- Python
- SQLAlchemy ORM
- PostgreSQL (production) / SQLite (local development and tests)

## Authentication

- JWT
- OAuth2 Password Bearer
- Passlib (bcrypt)

## AI

- Groq API
- Llama 3

## Resume Parsing

- PyMuPDF
- Regex

## Deployment

- Render

---

# 📂 Project Structure

```
app/
│
├── api/
│   ├── auth.py
│   ├── jobs.py
│   ├── resume.py
│   └── analysis.py
│
├── core/
│   ├── config.py
│   └── security.py
│
├── db/
│   └── database.py
│
├── models/
│
├── schemas/
│
├── services/
│   ├── parser.py
│   ├── ats.py
│   └── ai.py
│
└── main.py
```

---

# 🔐 Authentication Flow

```
Register
      │
      ▼
Login
      │
      ▼
JWT Token
      │
      ▼
Protected APIs
```

---

# 📊 Resume Analysis Workflow

```
Recruiter Login
        │
        ▼
Create Job
        │
        ▼
Upload Resume
        │
        ▼
Extract Resume Information
        │
        ▼
Calculate ATS Score
        │
        ▼
Generate AI Feedback
        │
        ▼
Store Analysis History
```

---

# 📌 API Endpoints

## Authentication

| Method | Endpoint |
|---------|----------|
| POST | /auth/register |
| POST | /auth/login |

---

## Jobs

| Method | Endpoint |
|---------|----------|
| POST | /jobs |
| GET | /jobs |
| GET | /jobs/{id} |
| DELETE | /jobs/{id} |

---

## Resume

| Method | Endpoint |
|---------|----------|
| POST | /resume/upload |

---

## Analysis

| Method | Endpoint |
|---------|----------|
| POST | /analysis/{job_id} |
| GET | /analysis/history |

---

## Phase 2: deterministic document intelligence

Phase 2 adds a lightweight, offline intelligence layer that understands
resume and job-description structure without changing the existing ATS score.
It detects resume sections, builds a structured candidate profile, canonicalizes
skill aliases (for example `JS` → `JavaScript` and `Postgres` → `PostgreSQL`),
captures source evidence, and extracts explicit experience and education
evidence. Job descriptions are parsed into required versus preferred skills,
qualifications, responsibilities, experience requirements, education
requirements, and domain keywords.

The authenticated endpoints are:

| Method | Endpoint | Purpose |
|---------|----------|---------|
| POST | /intelligence/resume | Parse a PDF into a structured resume profile |
| POST | /intelligence/job-description | Parse JSON job-description text into structured requirements |

Parsing is deterministic and does not require `GROQ_API_KEY`, internet access,
embeddings, or a database migration. These endpoints expose document facts for
future explainable matching; they do not make hiring decisions or replace the
existing ATS analysis.

## Phase 3: explainable resume/job alignment

Phase 3 replaces the legacy score bucket used by new analyses with a pure,
deterministic matching service. The score describes only what the supplied
resume demonstrates relative to the supplied job description. It is not a
hiring recommendation, a qualification decision, or proof that a candidate
does or does not possess information omitted from the resume.

The five default component weights are explicit product assumptions rather
than scientifically validated measures:

| Component | Default weight |
|-----------|----------------|
| Required skills | 50% |
| Preferred skills | 10% |
| Explicit experience duration | 20% |
| Explicit education | 10% |
| Deterministic responsibility relevance | 10% |

Required and preferred skills are scored separately using the Phase 2
canonical taxonomy and source evidence. Experience uses only explicit year
evidence. Education compares degree level and field conservatively. Role
relevance uses canonical technical skills, domain phrases, and filtered
lexical overlap in resume experience/projects; it is not semantic similarity.

If the job description does not contain a component, that component is marked
`NOT_APPLICABLE` and its weight is redistributed proportionally across all
applicable components. For example, when only required skills (50%) and
experience (20%) apply, their effective weights become 71.43% and 28.57%.

`evidence_coverage` is reported separately from `overall_score`. Coverage
measures how much of the requested evaluation is supported by explicit resume
evidence; it can be high even when the evidence demonstrates only partial
alignment. Every component reports its status, effective weight, point
contribution, explanation, and available evidence references.

The authenticated matching endpoints are:

| Method | Endpoint | Purpose |
|---------|----------|---------|
| POST | /matching/evaluate | Evaluate a PDF resume against multipart job-description text |
| POST | /matching/jobs/{job_id} | Evaluate a PDF against a recruiter-owned stored job |

New `/analysis/{job_id}` records persist the explainable breakdown in the
nullable `analysis.match_breakdown` field. The legacy `ats_score` remains as a
rounded compatibility representation of the deterministic overall alignment
score. New analyses always begin at workflow status `NEW`; shortlist/reject
transitions are manual and independent of score. Dashboard qualified/rejected
counts likewise use explicit workflow status rather than a score threshold.

The deterministic score does not call Groq or any other LLM. Existing Groq
feedback remains downstream of the score and cannot change it. Candidate name,
email, phone, photographs, addresses, and protected/personal attributes do not
participate in matching.

## Phase 4: grounded AI resume feedback

Phase 4 keeps the Phase 2/3 deterministic pipeline authoritative and uses the
LLM only as an advisory explanation layer. After matching completes, a
deterministic builder creates a bounded, privacy-reduced context containing the
job title, authoritative score and evidence coverage, required/preferred skill
results, structured experience and education results, role relevance,
deterministic strengths/gaps, and short job-relevant evidence snippets.

The feedback request does **not** include the complete resume or job
description, candidate name, email, phone, address/header text, or other
unrelated personal information. Known identity/contact values and common
email/phone patterns are also redacted from selected evidence. The model does
not receive secrets or database records.

Each supplied fact has a deterministic request-local ID such as
`REQ_SKILL_1`, `EXP_1`, or `ROLE_1`. Factual strengths and evidence gaps in the
provider response must cite known fact IDs. Provider JSON is validated with a
strict schema: unknown fields (including score or status fields), unknown fact
IDs, ungrounded factual items, non-conditional improvement advice, and hiring
decision language are rejected. Invalid output receives at most one retry.

System instructions and user data are separate messages. The system message
states that all resume/JD evidence is untrusted data and that embedded
instructions must not be followed. This architecture reduces prompt-injection
risk and makes score/status mutation impossible through the feedback schema,
but it is not a mathematical guarantee against every possible model behavior;
strict server-side validation remains the enforcement boundary.

The additive feedback metadata identifies whether content came from `groq` or
`deterministic_fallback`, along with generated/unavailable status, evidence
references, limitations, and grounding version. If Groq is unavailable,
misconfigured, times out, or repeatedly returns invalid output, the valid
deterministic analysis is still persisted and returned with an explicitly
labeled fallback built from `MatchResult`. The same resilience applies to bulk
and ZIP processing. AI feedback never changes scores, candidate status,
dashboard calculations, or leaderboard ordering, and it never recommends
hiring, rejection, shortlisting, or interviewing.

---

# ⚙️ Installation

Clone Repository

```bash
git clone https://github.com/Kaniishk005/resume-screening-api.git

cd resume-screening-api
```

Create Virtual Environment

```bash
python -m venv venv
```

Activate Environment

Windows

```bash
venv\Scripts\activate
```

Linux/Mac

```bash
source venv/bin/activate
```

Install Dependencies

```bash
pip install -r requirements.txt
```

Run Server

```bash
uvicorn app.main:app --reload
```

Run Tests

```bash
pytest -q
```

Apply database migrations before starting or redeploying the API:

```bash
alembic upgrade head
```

The initial migration is safe for both existing databases and fresh databases:
it adds `analysis.status` only when the table exists and the column is absent.
Application startup also runs `alembic upgrade head` before serving requests so
deployments cannot start against an older schema.

Database configuration

Local development and tests may use SQLite:

```dotenv
DATABASE_URL=sqlite:///./resume.db
```

Production should use a durable PostgreSQL database:

```dotenv
DATABASE_URL=postgresql+psycopg://user:password@host:5432/database
```

Render-provided `postgres://` and plain `postgresql://` URLs are normalized to
the Psycopg 3 SQLAlchemy dialect. SQLite-only connection arguments are applied
only to SQLite.

Application startup runs Alembic before `Base.metadata.create_all()`. The
`create_all()` call remains a temporary bootstrap fallback because the current
migration history starts with an incremental migration rather than a complete
initial-schema migration. Alembic should become the sole schema authority after
a future baseline-migration cleanup.

Open

```
http://127.0.0.1:8000/docs
```

---

# 🔑 Environment Variables

Create a `.env`

```env
DATABASE_URL=sqlite:///resume.db

SECRET_KEY=your_secret_key

ALGORITHM=HS256

ACCESS_TOKEN_EXPIRE_MINUTES=30

GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b

# Optional (defaults shown)
MAX_UPLOAD_SIZE_BYTES=5242880
GROQ_TIMEOUT_SECONDS=20
```

`SECRET_KEY` is required. `GROQ_API_KEY` is required only for AI analysis;
the application and health endpoint can start without it. Production deployments
should supply configuration through environment variables rather than committing a
`.env` file.

Only PDF resumes are supported. Files are validated, limited to the configured
maximum size (5 MiB by default), processed through temporary files, and removed
after each request.

The basic health check is available at `GET /health` and does not contact Groq.

---

# 📈 Sample Response

```json
{
  "candidate_name": "KANISHK TIWARI",
  "ats_score": 40,
  "match_percentage": 40,
  "matched_skills": [
    "Python",
    "FastAPI"
  ],
  "missing_skills": [
    "Docker",
    "AWS",
    "SQL"
  ],
  "ai_feedback": {
    "summary": "...",
    "strengths": [],
    "weaknesses": [],
    "recommendation": "...",
    "evidence_references": {},
    "limitations": [],
    "feedback_source": "groq",
    "feedback_status": "generated",
    "grounding_version": "1.0"
  }
}
```

---

# 📷 Screenshots

## Swagger Documentation

![alt text](image.png)

---
# 👨‍💻 Author

**Kanishk Tiwari**

GitHub

https://github.com/Kaniishk005

---

# ⭐ If you found this project useful, consider giving it a star.
### Browser development CORS

Set `CORS_ALLOWED_ORIGINS` to a comma-separated list of explicit frontend origins, for example:

`CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`

Bearer-token requests do not require credentialed cookies; origins are explicit rather than wildcarded.
