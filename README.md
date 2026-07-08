# AI Resume Screening API

An AI-powered Resume Screening API built with **FastAPI**, **SQLAlchemy**, **JWT Authentication**, and **Groq LLM**. The system allows recruiters to create job postings, upload resumes, automatically calculate ATS scores, identify skill gaps, generate AI-powered feedback, and maintain analysis history.

---

## Features

### Authentication
- Recruiter Registration
- Secure Login using JWT Authentication
- Password hashing with bcrypt
- Protected API endpoints

### Job Management
- Create Job Posts
- View All Jobs
- View Individual Job
- Delete Jobs

### Resume Parsing
- Upload PDF resumes
- Extract:
  - Candidate Name
  - Email
  - Phone Number
  - Skills
  - Resume Text

### 📊 ATS Score Calculation
- Skill matching between Resume and Job Description
- ATS Score generation
- Match Percentage
- Missing Skills Detection

### AI Feedback
Using **Groq LLM**, the API generates:

- Resume Summary
- Candidate Strengths
- Weaknesses
- Hiring Recommendation

### Analysis History
Every resume analysis is stored in the database along with:
- Candidate Name
- ATS Score
- Match Percentage
- Matched Skills
- Missing Skills
- AI Feedback
- Recruiter
- Job

---

# 🛠 Tech Stack

## Backend
- FastAPI
- SQLAlchemy 2.0
- SQLite

## Authentication
- JWT
- OAuth2 Password Flow
- Passlib
- bcrypt

## AI
- Groq API (Llama Model)

## Resume Parsing
- PyMuPDF

## Validation
- Pydantic v2

---

# 📂 Project Structure

```text
resume-screening-api/
│
├── app/
│   ├── api/
│   │   ├── auth.py
│   │   ├── jobs.py
│   │   ├── resume.py
│   │   └── analysis.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   │
│   ├── db/
│   │   └── database.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── job.py
│   │   └── analysis.py
│   │
│   ├── schemas/
│   │   ├── user.py
│   │   ├── job.py
│   │   ├── resume.py
│   │   └── analysis.py
│   │
│   ├── services/
│   │   ├── ai.py
│   │   ├── ats.py
│   │   └── parser.py
│   │
│   ├── utils/
│   │   └── skills.py
│   │
│   └── main.py
│
├── uploads/
├── tests/
├── requirements.txt
├── README.md
└── .env
```

---

# ⚙ Installation

## Clone Repository

```bash
git clone https://github.com/yourusername/resume-screening-api.git

cd resume-screening-api
```

---

## Create Virtual Environment

```bash
python -m venv venv
```

Windows

```bash
venv\Scripts\activate
```

Linux / macOS

```bash
source venv/bin/activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Configure Environment Variables

Create a `.env` file:

```env
SECRET_KEY=your_secret_key

ALGORITHM=HS256

ACCESS_TOKEN_EXPIRE_MINUTES=60

GROQ_API_KEY=your_groq_api_key
```

---

## Run Server

```bash
uvicorn app.main:app --reload
```

Swagger UI

```
http://127.0.0.1:8000/docs
```

---

# 📚 API Endpoints

## Authentication

| Method | Endpoint | Description |
|---------|----------|-------------|
| POST | `/auth/register` | Register Recruiter |
| POST | `/auth/login` | Login |

---

## Jobs

| Method | Endpoint |
|---------|----------|
| POST | `/jobs/` |
| GET | `/jobs/` |
| GET | `/jobs/{id}` |
| DELETE | `/jobs/{id}` |

---

## Resume

| Method | Endpoint |
|---------|----------|
| POST | `/resume/upload` |

---

## Analysis

| Method | Endpoint |
|---------|----------|
| POST | `/analysis/{job_id}` |
| GET | `/analysis/history` |

---

# 🧠 AI Workflow

```text
Resume PDF
      │
      ▼
Extract Resume Text
      │
      ▼
Extract Skills
      │
      ▼
Compare with Job Skills
      │
      ▼
Calculate ATS Score
      │
      ▼
Generate AI Feedback (Groq)
      │
      ▼
Store Analysis in Database
      │
      ▼
Return API Response
```

---

# 📸 Sample Response

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

# 🔒 Security Features

- JWT Authentication
- Password Hashing using bcrypt
- Protected Routes
- OAuth2 Password Flow
- Environment Variable Configuration

---

# 🚀 Future Improvements

- Docker Deployment
- PostgreSQL Support
- Role-Based Access Control (Recruiter/Admin)
- Resume Ranking
- Batch Resume Analysis
- Email Notifications
- Interview Recommendation Engine
- Analytics Dashboard
- CI/CD Pipeline
- Unit & Integration Tests

---

# 👨‍💻 Author

**Kanishk Tiwari**

- GitHub: https://github.com/Kaniishk005

---

## ⭐ If you found this project useful, consider giving it a star!