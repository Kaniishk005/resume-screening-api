import io
import zipfile

from app.models.analysis import Analysis


def test_existing_analysis_status_dashboard_leaderboard_and_zip_workflow(
    client, auth_headers, pdf_bytes, monkeypatch
):
    feedback = {
        "summary": "Qualified",
        "strengths": ["Python"],
        "weaknesses": [],
        "recommendation": "Interview",
    }
    monkeypatch.setattr("app.api.analysis.generate_feedback", lambda *_args: feedback)
    job = client.post(
        "/jobs/",
        headers=auth_headers,
        json={
            "title": "Backend Engineer",
            "company": "Example",
            "description": "Build APIs",
            "required_skills": "Python, FastAPI",
            "experience": "2 years",
            "location": "Remote",
        },
    )
    assert job.status_code == 201
    job_id = job.json()["id"]

    analyzed = client.post(
        f"/analysis/{job_id}",
        headers=auth_headers,
        files={"file": ("candidate.pdf", pdf_bytes, "application/pdf")},
    )
    assert analyzed.status_code == 200
    assert analyzed.json()["status"] == "SHORTLISTED"

    # The history contract intentionally omits the internal id, so obtain it
    # through the same test database used by the application fixture.
    from conftest import TestingSessionLocal

    db = TestingSessionLocal()
    try:
        analysis_id = db.query(Analysis).order_by(Analysis.id.desc()).first().id
    finally:
        db.close()

    updated = client.patch(
        f"/analysis/{analysis_id}/status",
        headers=auth_headers,
        json={"status": "INTERVIEW"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "INTERVIEW"
    assert client.get("/analysis/history", headers=auth_headers).json()[0]["status"] == "INTERVIEW"

    dashboard = client.get(f"/jobs/{job_id}/dashboard", headers=auth_headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["total_resumes"] == 1

    leaderboard = client.get(f"/jobs/{job_id}/leaderboard", headers=auth_headers)
    assert leaderboard.status_code == 200
    assert leaderboard.json()["total_candidates"] == 1

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("candidate-one.pdf", pdf_bytes)
        bundle.writestr("nested/candidate-two.pdf", pdf_bytes)
    archive.seek(0)
    bulk = client.post(
        f"/analysis/{job_id}/zip",
        headers=auth_headers,
        files={"zip_file": ("candidates.zip", archive.getvalue(), "application/zip")},
    )
    assert bulk.status_code == 200
    body = bulk.json()
    assert body["successful"] == 2
    assert body["failed"] == 0
    assert all("skills" not in item for item in body["results"])
