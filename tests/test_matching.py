import math

import pytest

from app.core.constants import MATCH_WEIGHTS
from app.schemas.intelligence import JobProfile
from app.schemas.matching import MatchStatus
from app.services.job_parser import parse_job_description
from app.services.matching import evaluate_match
from app.services.resume_intelligence import build_resume_profile


def resume(text: str):
    return build_resume_profile(text)


def job(
    *,
    required=(),
    preferred=(),
    experience=(),
    education=(),
    responsibilities=(),
    domains=(),
):
    return JobProfile(
        required_skills=list(required),
        preferred_skills=list(preferred),
        experience_requirements=list(experience),
        education_requirements=list(education),
        responsibilities=list(responsibilities),
        domain_keywords=list(domains),
        raw_description="test",
    )


def test_required_skills_all_matched_score_100():
    result = evaluate_match(resume("TECHNICAL SKILLS\nPython FastAPI Postgres"), job(required=("Python", "FastAPI", "PostgreSQL")))
    assert result.components["required_skills"].score == 100
    assert result.components["required_skills"].status == MatchStatus.MATCHED


def test_required_skills_partial_match():
    result = evaluate_match(resume("TECHNICAL SKILLS\nPython"), job(required=("Python", "Docker")))
    assert result.components["required_skills"].score == 50
    assert result.missing_required_skills == ["Docker"]


def test_required_skills_none_matched():
    result = evaluate_match(resume("TECHNICAL SKILLS\nReact"), job(required=("Python", "Docker")))
    assert result.components["required_skills"].score == 0
    assert result.components["required_skills"].status == MatchStatus.NOT_DEMONSTRATED


def test_required_skill_aliases_match():
    result = evaluate_match(resume("TECHNICAL SKILLS\nPostgres JS sklearn"), job(required=("PostgreSQL", "JavaScript", "Scikit-learn")))
    assert result.matched_required_skills == ["JavaScript", "PostgreSQL", "Scikit-learn"]


def test_required_skill_evidence_is_included():
    result = evaluate_match(resume("PROJECTS\nBuilt APIs with FastAPI"), job(required=("FastAPI",)))
    detail = result.required_skill_details[0]
    assert detail.evidence and detail.evidence[0].section == "projects"


def test_preferred_skills_all_matched():
    result = evaluate_match(resume("SKILLS\nAWS Docker"), job(preferred=("AWS", "Docker")))
    assert result.components["preferred_skills"].score == 100


def test_preferred_skills_partial_match():
    result = evaluate_match(resume("SKILLS\nDocker"), job(preferred=("AWS", "Docker")))
    assert result.components["preferred_skills"].score == 50


def test_no_preferred_skills_is_not_applicable():
    result = evaluate_match(resume("SKILLS\nPython"), job(required=("Python",)))
    assert result.components["preferred_skills"].status == MatchStatus.NOT_APPLICABLE


def test_missing_preferred_skill_is_not_a_required_gap():
    result = evaluate_match(resume("SKILLS\nPython"), job(required=("Python",), preferred=("AWS",)))
    assert result.missing_required_skills == []
    assert result.missing_preferred_skills == ["AWS"]
    assert any("preferred rather than required" in gap for gap in result.gaps)


@pytest.mark.parametrize(("resume_years", "expected_status"), [("4 years", MatchStatus.MATCHED), ("3 years", MatchStatus.MATCHED), ("2 years", MatchStatus.PARTIAL)])
def test_minimum_experience_comparison(resume_years, expected_status):
    jd = parse_job_description("Requirements:\n3+ years of backend experience")
    result = evaluate_match(resume(f"EXPERIENCE\nBackend Engineer {resume_years}"), jd)
    assert result.components["experience"].status == expected_status


def test_experience_range_requirement():
    jd = parse_job_description("Requirements:\n2-4 years of backend experience")
    result = evaluate_match(resume("EXPERIENCE\nBackend Engineer 3 years"), jd)
    assert result.components["experience"].score == 100


def test_no_job_experience_is_not_applicable():
    result = evaluate_match(resume("EXPERIENCE\nBackend Engineer 3 years"), job(required=("Python",)))
    assert result.components["experience"].status == MatchStatus.NOT_APPLICABLE


def test_no_resume_duration_is_not_demonstrated():
    jd = parse_job_description("Requirements:\n3+ years of backend experience")
    result = evaluate_match(resume("EXPERIENCE\nBackend Engineer"), jd)
    assert result.components["experience"].status == MatchStatus.NOT_DEMONSTRATED
    assert "No explicit duration" in result.experience_details[0].reason


def test_education_exact_degree_and_field():
    jd = parse_job_description("Education:\nBachelor's degree in Computer Science")
    result = evaluate_match(resume("EDUCATION\nBachelor's degree in Computer Science"), jd)
    assert result.components["education"].score == 100


def test_higher_degree_satisfies_lower_degree_level():
    jd = parse_job_description("Education:\nBachelor's degree in Computer Science")
    result = evaluate_match(resume("EDUCATION\nMaster's degree in Computer Science"), jd)
    assert result.components["education"].status == MatchStatus.MATCHED


def test_wrong_education_field_is_partial():
    jd = parse_job_description("Education:\nBachelor's degree in Computer Science")
    result = evaluate_match(resume("EDUCATION\nBachelor's degree in Mechanical Engineering"), jd)
    assert result.components["education"].score == 60
    assert result.components["education"].status == MatchStatus.PARTIAL


def test_related_computing_field_is_conservatively_accepted():
    jd = parse_job_description("Education:\nBachelor's degree in Computer Science or related field")
    result = evaluate_match(resume("EDUCATION\nB.Tech Information Technology"), jd)
    assert result.components["education"].score == 100


def test_no_job_education_is_not_applicable():
    result = evaluate_match(resume("EDUCATION\nB.Tech Computer Science"), job(required=("Python",)))
    assert result.components["education"].status == MatchStatus.NOT_APPLICABLE


def test_missing_resume_education_is_not_demonstrated():
    jd = parse_job_description("Education:\nBachelor's degree in Computer Science")
    result = evaluate_match(resume("SKILLS\nPython"), jd)
    assert result.components["education"].status == MatchStatus.NOT_DEMONSTRATED


def test_role_relevance_strong_overlap():
    result = evaluate_match(
        resume("PROJECTS\nDeveloped REST APIs with FastAPI and Postgres"),
        job(responsibilities=("Build REST APIs using FastAPI and PostgreSQL",)),
    )
    assert result.components["role_relevance"].score >= 75


def test_role_relevance_partial_overlap():
    result = evaluate_match(
        resume("PROJECTS\nDeveloped APIs with FastAPI"),
        job(responsibilities=("Build REST APIs using FastAPI and PostgreSQL",)),
    )
    assert 0 < result.components["role_relevance"].score < 100


def test_role_relevance_no_overlap():
    result = evaluate_match(
        resume("PROJECTS\nTrained machine learning models with Pandas"),
        job(responsibilities=("Build REST APIs using FastAPI and PostgreSQL",)),
    )
    assert result.components["role_relevance"].score == 0


def test_default_weights_total_one():
    assert sum(MATCH_WEIGHTS.values()) == pytest.approx(1.0)


def test_not_applicable_weight_is_redistributed():
    result = evaluate_match(resume("SKILLS\nPython"), job(required=("Python",)))
    assert result.components["required_skills"].effective_weight == 1.0
    assert result.components["education"].effective_weight == 0.0


def test_multiple_not_applicable_components_redistribute_generically():
    result = evaluate_match(resume("SKILLS\nPython Docker"), job(required=("Python",), preferred=("Docker",)))
    assert result.components["required_skills"].effective_weight == pytest.approx(5 / 6)
    assert result.components["preferred_skills"].effective_weight == pytest.approx(1 / 6)


@pytest.mark.parametrize(
    "resume_text",
    ["Sparse Candidate", "SKILLS\nPython", "SKILLS\nReact", "EXPERIENCE\n2 years"],
)
def test_score_is_finite_and_clamped(resume_text):
    result = evaluate_match(resume(resume_text), job(required=("Python",), preferred=("AWS",)))
    assert math.isfinite(result.overall_score)
    assert 0 <= result.overall_score <= 100


def test_evidence_coverage_is_separate_from_alignment_score():
    jd = parse_job_description("Education:\nBachelor's degree in Computer Science")
    result = evaluate_match(resume("EDUCATION\nBachelor's degree in Mechanical Engineering"), jd)
    assert result.evidence_coverage == 100
    assert result.overall_score == 60


def test_missing_evidence_is_reported_without_claiming_absence():
    jd = parse_job_description("Experience:\n3+ years of experience")
    result = evaluate_match(resume("EXPERIENCE\nBackend Engineer"), jd)
    assert any("not demonstrated" in gap.casefold() or "no qualifying duration" in gap.casefold() for gap in result.gaps)
    assert all("does not possess" not in item.casefold() for item in result.gaps)


def test_contact_and_identity_data_never_affect_score():
    first = resume("Python Docker\njava@example.com\n9999999999\nAge: 40 years\nJava Street\nSKILLS\nReact")
    second = resume("Node JavaScript\nother@example.com\n8888888888\nAge: 20 years\nPython Avenue\nSKILLS\nReact")
    jd = parse_job_description(
        "Required Skills:\nReact Python Docker Java JavaScript Node.js\nExperience:\n5+ years"
    )
    first_result = evaluate_match(first, jd)
    second_result = evaluate_match(second, jd)
    assert first_result.overall_score == second_result.overall_score
    assert first_result.matched_required_skills == ["React"]
    assert first_result.components["experience"].status == MatchStatus.NOT_DEMONSTRATED


def test_backend_end_to_end_example():
    jd = parse_job_description(
        """Backend Engineer
Required Skills:
Python FastAPI PostgreSQL REST API
Preferred:
Docker AWS
Experience:
3+ years
Education:
Bachelor's degree in Computer Science
Responsibilities:
Build REST APIs with FastAPI and PostgreSQL
"""
    )
    candidate = resume(
        """Backend Candidate
SKILLS
Python FastAPI Postgres REST APIs Docker
EXPERIENCE
Backend Engineer with 3 years of experience
PROJECTS
Built REST APIs with FastAPI and Postgres
EDUCATION
B.Tech Computer Science
"""
    )
    result = evaluate_match(candidate, jd)
    assert result.components["required_skills"].score == 100
    assert result.components["preferred_skills"].score == 50
    assert result.components["experience"].status == MatchStatus.MATCHED
    assert result.components["education"].status == MatchStatus.MATCHED
    assert result.required_skill_details[0].evidence


def test_ml_end_to_end_alias_example():
    result = evaluate_match(
        resume("SKILLS\nPython ML sklearn Pandas"),
        job(required=("Python", "Machine Learning", "Scikit-learn", "Pandas"), preferred=("PyTorch",)),
    )
    assert result.components["required_skills"].score == 100


def test_unrelated_candidate_scores_very_low():
    result = evaluate_match(
        resume("SKILLS\nPython Pandas Machine Learning"),
        job(required=("React", "TypeScript", "Node.js")),
    )
    assert result.overall_score == 0


def test_sparse_resume_is_safe():
    result = evaluate_match(resume("Sparse Candidate"), job(required=("Python",), preferred=("Docker",)))
    assert result.overall_score == 0 and result.evidence_coverage == 0


def test_sparse_job_is_safe_and_never_nan():
    result = evaluate_match(resume("SKILLS\nPython"), job())
    assert result.overall_score == 0 and result.evidence_coverage == 0


def test_duplicate_and_overlapping_required_preferred_skills_are_deduplicated():
    result = evaluate_match(
        resume("SKILLS\nPython"),
        job(required=("Python", "python"), preferred=("Python", "Docker", "Docker")),
    )
    assert result.matched_required_skills == ["Python"]
    assert result.missing_preferred_skills == ["Docker"]


def test_each_component_has_deterministic_explanation():
    result = evaluate_match(resume("SKILLS\nPython"), job(required=("Python",)))
    assert all(component.explanation for component in result.components.values())
    assert len(result.explanation) == len(MATCH_WEIGHTS)


def test_matching_api_requires_authentication(client, pdf_bytes):
    response = client.post(
        "/matching/evaluate",
        data={"job_description": "Required:\nPython"},
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 401


def test_matching_api_returns_breakdown(client, auth_headers, pdf_bytes):
    response = client.post(
        "/matching/evaluate",
        headers=auth_headers,
        data={"job_description": "Required:\nPython FastAPI"},
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    assert set(response.json()["components"]) == set(MATCH_WEIGHTS)


def test_existing_job_matching_respects_ownership(client, auth_headers, pdf_bytes):
    created = client.post(
        "/jobs/",
        headers=auth_headers,
        json={"title": "Backend", "company": "Example", "description": "Build APIs", "required_skills": "Python", "experience": "2 years", "location": "Remote"},
    )
    response = client.post(
        f"/matching/jobs/{created.json()['id']}",
        headers=auth_headers,
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    assert client.post(
        "/auth/register",
        json={"username": "other-matcher", "email": "other-matcher@example.com", "password": "password-123"},
    ).status_code == 201
    other_token = client.post(
        "/auth/login",
        data={"username": "other-matcher@example.com", "password": "password-123"},
    ).json()["access_token"]
    denied = client.post(
        f"/matching/jobs/{created.json()['id']}",
        headers={"Authorization": f"Bearer {other_token}"},
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert denied.status_code == 404


def test_existing_job_matching_missing_job_returns_404(client, auth_headers, pdf_bytes):
    response = client.post(
        "/matching/jobs/999999",
        headers=auth_headers,
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 404


def test_matching_endpoint_rejects_empty_job_description(client, auth_headers, pdf_bytes):
    response = client.post(
        "/matching/evaluate",
        headers=auth_headers,
        data={"job_description": "   "},
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 422
