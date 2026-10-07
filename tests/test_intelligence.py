import pytest

from app.services.job_parser import detect_job_sections, parse_job_description
from app.services.resume_intelligence import build_resume_profile, detect_sections
from app.services.skill_normalizer import extract_normalized_skills, normalize_skill_name


def test_skill_aliases_normalize_to_canonical_names():
    assert normalize_skill_name("JS") == "JavaScript"
    assert normalize_skill_name("React.js") == "React"
    assert normalize_skill_name("Postgres") == "PostgreSQL"
    assert normalize_skill_name("NodeJS") == "Node.js"
    assert normalize_skill_name("ML") == "Machine Learning"


@pytest.mark.parametrize(
    ("alias", "canonical"),
    [
        ("ECMAScript", "JavaScript"),
        ("psql", "PostgreSQL"),
        ("sklearn", "Scikit-learn"),
        ("RESTful APIs", "REST API"),
        ("machine learning", "Machine Learning"),
    ],
)
def test_additional_skill_aliases_are_canonicalized(alias, canonical):
    assert normalize_skill_name(alias) == canonical


def test_skill_extraction_handles_punctuation_and_boundaries():
    skills = extract_normalized_skills("JS React.js Postgres NodeJS ML C++ C# C")
    assert skills == ["C", "C#", "C++", "JavaScript", "Machine Learning", "Node.js", "PostgreSQL", "React"]
    assert "C" not in extract_normalized_skills("React Cloud Docker")
    assert "Java" not in extract_normalized_skills("JavaScript")
    assert extract_normalized_skills("Python python PYTHON") == ["Python"]


def test_resume_sections_and_unknown_content_are_preserved():
    text = """Jane Doe\njane@example.com\nUnlabelled introduction\nTECHNICAL SKILLS:\nJS, Postgres\nWORK EXPERIENCE\nBackend Engineer - 3+ years of experience\nBuilt APIs with FastAPI\nPROJECTS:\nResume API using NodeJS\nEDUCATION\nB.Tech Computer Science\nCERTIFICATES:\nAWS Developer\n"""
    sections = detect_sections(text)
    assert sections["skills"] == "JS, Postgres"
    assert "Unlabelled introduction" in sections["other"]
    assert "experience" in sections and "projects" in sections and "education" in sections
    profile = build_resume_profile(text)
    assert profile.skills == ["AWS", "FastAPI", "JavaScript", "Node.js", "PostgreSQL"]
    assert profile.experience and profile.experience_evidence[0].minimum_years == 3
    assert profile.projects[0].skills == ["Node.js"]
    assert profile.education_evidence[0].degree == "B.Tech"
    assert profile.certifications[0].skills == ["AWS"]
    assert any(
        item.section == "projects"
        and item.canonical_skill == "Node.js"
        and item.context
        for item in profile.skill_evidence
    )


def test_resume_additional_sections_and_heading_variants():
    profile = build_resume_profile(
        """Alex Candidate
alex@example.com
PROFESSIONAL EXPERIENCE:
Worked with Python.
ACADEMIC PROJECTS:
Built a React app.
ACADEMIC BACKGROUND:
BSc Information Technology
AWARDS:
Employee of the year
POSITIONS OF RESPONSIBILITY:
Led a student team
+919876543210
"""
    )
    assert "experience" in profile.sections
    assert profile.projects and profile.projects[0].skills == ["React"]
    assert profile.education and profile.education_evidence[0].degree == "BSc"
    assert profile.achievements and profile.leadership
    assert profile.email == "alex@example.com"
    assert profile.phone == "+919876543210"


def test_sparse_resume_does_not_crash():
    profile = build_resume_profile("Alex Candidate\nemail@example.com\nSome text without headings.")
    assert profile.candidate_name == "Alex Candidate"
    assert profile.sections["other"]
    assert profile.projects == []


def test_job_description_required_preferred_and_evidence_are_separate():
    jd = """Backend Engineer\nRequirements:\n- Python\n- FastAPI\n- PostgreSQL\nNice to have:\n- Docker\n- AWS\nResponsibilities:\n- Build REST APIs\n- Operate microservices\nQualifications:\n- Bachelor's degree in Computer Science\n- 3+ years of backend development experience\n"""
    profile = parse_job_description(jd)
    assert profile.job_title == "Backend Engineer"
    assert profile.required_skills == ["FastAPI", "PostgreSQL", "Python"]
    assert profile.preferred_skills == ["AWS", "Docker"]
    assert profile.experience_requirements[0].minimum_years == 3
    assert profile.education_requirements[0].degree == "Bachelor's degree"
    assert profile.responsibilities == ["Build REST APIs", "Operate microservices"]
    assert profile.qualifications[:3] == ["Python", "FastAPI", "PostgreSQL"]
    assert "Bachelor's degree in Computer Science" in profile.qualifications
    assert profile.preferred_qualifications == ["Docker", "AWS"]
    assert "backend development" in profile.domain_keywords


def test_job_description_supports_ranges_and_no_optional_section():
    profile = parse_job_description(
        "ML Engineer\nMust Have: Python, ML, scikit-learn\nEducation: Master's degree in Data Science\n2-4 years of experience"
    )
    assert profile.required_skills == ["Machine Learning", "Python", "Scikit-learn"]
    assert profile.preferred_skills == []
    assert profile.experience_requirements[0].minimum_years == 2
    assert profile.experience_requirements[0].maximum_years == 4
    assert profile.education_requirements[0].degree == "Master's degree"


@pytest.mark.parametrize("heading", ["Must Have:", "Must-have:", "Required Qualifications:"])
def test_job_required_heading_variants(heading):
    profile = parse_job_description(f"{heading}\n- Python\n")
    assert profile.required_skills == ["Python"]


@pytest.mark.parametrize("heading", ["Nice to have:", "Good to have:", "Preferred:"])
def test_job_preferred_heading_variants(heading):
    profile = parse_job_description(f"{heading}\n- Docker\n")
    assert profile.preferred_skills == ["Docker"]


@pytest.mark.parametrize("text", ["at least 3 years of experience", "minimum 2 years experience"])
def test_job_minimum_experience_wording(text):
    profile = parse_job_description(f"Requirements:\n- Python\n{text}")
    assert profile.experience_requirements
    assert profile.experience_requirements[0].minimum_years in (2, 3)


def test_job_without_optional_requirements_is_safe():
    profile = parse_job_description("Responsibilities:\n- Build APIs\nPython developer")
    assert profile.preferred_skills == []
    assert profile.education_requirements == []
    assert profile.responsibilities[0] == "Build APIs"


def test_job_section_heading_variants():
    sections = detect_job_sections("What You'll Do:\n- Build\nPreferred Qualifications:\n- Docker")
    assert sections["responsibilities"] == "- Build"
    assert sections["preferred"] == "- Docker"


def test_intelligence_endpoints_require_authentication(client, pdf_bytes):
    assert client.post("/intelligence/resume", files={"file": ("resume.pdf", pdf_bytes, "application/pdf")}).status_code == 401
    assert client.post("/intelligence/job-description", json={"description": "Python"}).status_code == 401


def test_resume_intelligence_endpoint_returns_structured_profile(client, auth_headers, pdf_bytes):
    response = client.post(
        "/intelligence/resume",
        headers=auth_headers,
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["candidate_name"] == "Jane Doe"
    assert "Python" in body["skills"]
    assert "skill_evidence" in body


def test_job_intelligence_endpoint_is_deterministic_and_does_not_need_groq(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.services.ai.generate_feedback", lambda *_args: (_ for _ in ()).throw(AssertionError("Groq must not be called")))
    response = client.post(
        "/intelligence/job-description",
        headers=auth_headers,
        json={"description": "Requirements:\n- Postgres\nNice to have:\n- AWS\n3+ years experience"},
    )
    assert response.status_code == 200
    assert response.json()["required_skills"] == ["PostgreSQL"]
    assert response.json()["preferred_skills"] == ["AWS"]


def test_intelligence_endpoints_reject_malformed_inputs(client, auth_headers):
    bad_resume = client.post(
        "/intelligence/resume",
        headers=auth_headers,
        files={"file": ("resume.txt", b"not a pdf", "text/plain")},
    )
    assert bad_resume.status_code == 415
    empty_jd = client.post(
        "/intelligence/job-description",
        headers=auth_headers,
        json={"description": "   "},
    )
    assert empty_jd.status_code == 422

