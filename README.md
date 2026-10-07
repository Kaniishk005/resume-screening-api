# 🚀 AI Resume Screening API

An AI-powered Resume Screening API built using **FastAPI**, **SQLAlchemy**, **JWT Authentication**, and **Groq LLM**. The API allows recruiters to create job descriptions, upload resumes, calculate ATS scores, identify missing skills, and generate AI-powered hiring feedback.

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
Powered by **Groq Llama 3**

Generates

- Resume Summary
- Strengths
- Weaknesses
- Hiring Recommendation

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
- SQLite

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
    "recommendation": "..."
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
