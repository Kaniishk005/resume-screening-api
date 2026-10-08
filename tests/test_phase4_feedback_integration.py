import io
import zipfile
from types import SimpleNamespace

from app.services.ai import AIServiceError


JOB = {
    "title": "Backend Engineer",
    "company": "Example",
    "description": "Build REST APIs",
    "required_skills": "Python, FastAPI",
    "experience": "2 years",
    "location": "Remote",
}


def create_job(client, auth_headers):
    response = client.post("/jobs/", json=JOB, headers=auth_headers)
    assert response.status_code == 201
    return response.json()["id"]


def unavailable(*_args, **_kwargs):
    raise AIServiceError("provider unavailable")


GENERATED = {
    "summary": "The supplied evidence shows documented backend alignment.",
    "strengths": ["Python is explicitly demonstrated."],
    "weaknesses": ["FastAPI is not demonstrated in the supplied evidence."],
    "recommendation": "If accurate, add a concrete FastAPI example.",
    "evidence_references": {
        "Python is explicitly demonstrated.": ["REQ_SKILL_1"],
        "FastAPI is not demonstrated in the supplied evidence.": ["REQ_SKILL_2"],
    },
    "limitations": ["Only supplied evidence was reviewed."],
    "feedback_source": "groq",
    "feedback_status": "generated",
    "grounding_version": "1.0",
}


def test_grounded_ai_feedback_persists_without_changing_score_or_status(
    client, auth_headers, pdf_bytes, monkeypatch
):
    monkeypatch.setattr("app.api.analysis.generate_feedback", lambda *_args: GENERATED)
    job_id = create_job(client, auth_headers)

    response = client.post(
        f"/analysis/{job_id}",
        headers=auth_headers,
        files={"file": ("candidate.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ai_feedback"] == GENERATED
    assert body["status"] == "NEW"
    assert body["ats_score"] == round(body["match_breakdown"]["overall_score"])
    stored = client.get("/analysis/history", headers=auth_headers).json()[0]
    assert stored["ai_feedback"] == GENERATED
    assert stored["status"] == "NEW"
    assert stored["ats_score"] == body["ats_score"]


def test_provider_failure_keeps_analysis_successful_and_persists_fallback(
    client, auth_headers, pdf_bytes, monkeypatch
):
    monkeypatch.setattr("app.api.analysis.generate_feedback", unavailable)
    job_id = create_job(client, auth_headers)

    response = client.post(
        f"/analysis/{job_id}",
        headers=auth_headers,
        files={"file": ("candidate.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "NEW"
    assert body["match_breakdown"]
    assert body["ats_score"] == round(body["match_breakdown"]["overall_score"])
    assert body["ai_feedback"]["feedback_source"] == "deterministic_fallback"
    assert body["ai_feedback"]["feedback_status"] == "unavailable"

    history = client.get("/analysis/history", headers=auth_headers)
    assert history.status_code == 200
    stored = next(
        item for item in history.json() if item["analysis_id"] == body["analysis_id"]
    )
    assert stored["ai_feedback"] == body["ai_feedback"]
    assert stored["match_breakdown"] == body["match_breakdown"]


def test_bulk_and_zip_provider_failures_are_successes(
    client, auth_headers, pdf_bytes, monkeypatch
):
    monkeypatch.setattr("app.api.analysis.generate_feedback", unavailable)
    job_id = create_job(client, auth_headers)

    bulk = client.post(
        f"/analysis/{job_id}/bulk",
        headers=auth_headers,
        files=[
            ("files", ("one.pdf", pdf_bytes, "application/pdf")),
            ("files", ("two.pdf", pdf_bytes, "application/pdf")),
        ],
    )

    assert bulk.status_code == 200
    assert bulk.json()["successful"] == 2
    assert bulk.json()["failed"] == 0
    assert all(
        item["ai_feedback"]["feedback_source"] == "deterministic_fallback"
        for item in bulk.json()["results"]
    )

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("candidate.pdf", pdf_bytes)
    archive.seek(0)
    zipped = client.post(
        f"/analysis/{job_id}/zip",
        headers=auth_headers,
        files={"zip_file": ("candidates.zip", archive.getvalue(), "application/zip")},
    )

    assert zipped.status_code == 200
    assert zipped.json()["successful"] == 1
    assert zipped.json()["failed"] == 0
    assert zipped.json()["results"][0]["ai_feedback"]["feedback_status"] == "unavailable"
    history = client.get("/analysis/history", headers=auth_headers).json()
    assert len(history) == 3
    assert all(item["match_breakdown"] for item in history)


def test_missing_api_key_falls_back_without_failing_analysis(
    client, auth_headers, pdf_bytes, monkeypatch
):
    monkeypatch.setattr("app.services.ai.settings.GROQ_API_KEY", None)
    job_id = create_job(client, auth_headers)

    response = client.post(
        f"/analysis/{job_id}",
        headers=auth_headers,
        files={"file": ("candidate.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json()["ai_feedback"]["feedback_status"] == "unavailable"


def test_timeout_and_repeated_malformed_output_fall_back(
    client, auth_headers, pdf_bytes, monkeypatch
):
    job_id = create_job(client, auth_headers)

    def timeout(**_kwargs):
        raise TimeoutError("provider timeout")

    timeout_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=timeout))
    )
    monkeypatch.setattr("app.services.ai._get_client", lambda: timeout_client)
    timed_out = client.post(
        f"/analysis/{job_id}",
        headers=auth_headers,
        files={"file": ("timeout.pdf", pdf_bytes, "application/pdf")},
    )
    assert timed_out.status_code == 200
    assert timed_out.json()["ai_feedback"]["feedback_source"] == "deterministic_fallback"

    calls = []

    def malformed(**_kwargs):
        calls.append(1)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="not-json"))]
        )

    malformed_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=malformed))
    )
    monkeypatch.setattr("app.services.ai._get_client", lambda: malformed_client)
    invalid = client.post(
        f"/analysis/{job_id}",
        headers=auth_headers,
        files={"file": ("malformed.pdf", pdf_bytes, "application/pdf")},
    )
    assert invalid.status_code == 200
    assert invalid.json()["ai_feedback"]["feedback_status"] == "unavailable"
    assert len(calls) == 2


def test_legacy_feedback_remains_readable(client, auth_headers, pdf_bytes, monkeypatch):
    legacy = {
        "summary": "Earlier stored feedback",
        "strengths": ["Python"],
        "weaknesses": [],
        "recommendation": "Review the evidence.",
    }
    monkeypatch.setattr("app.api.analysis.generate_feedback", lambda *_args: legacy)
    job_id = create_job(client, auth_headers)
    created = client.post(
        f"/analysis/{job_id}",
        headers=auth_headers,
        files={"file": ("candidate.pdf", pdf_bytes, "application/pdf")},
    )
    assert created.status_code == 200

    history = client.get("/analysis/history", headers=auth_headers)
    stored = next(
        item
        for item in history.json()
        if item["analysis_id"] == created.json()["analysis_id"]
    )
    assert stored["ai_feedback"]["summary"] == "Earlier stored feedback"
    assert stored["ai_feedback"]["feedback_source"] == "legacy"
    assert stored["ai_feedback"]["evidence_references"] == {}
