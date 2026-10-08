import io
import zipfile

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
    assert analyzed.json()["status"] == "NEW"
    assert analyzed.json()["match_breakdown"]
    assert analyzed.json()["ats_score"] == round(
        analyzed.json()["match_breakdown"]["overall_score"]
    )
    analysis_id = analyzed.json()["analysis_id"]
    assert isinstance(analysis_id, int)

    shortlisted = client.patch(
        f"/analysis/{analysis_id}/status",
        headers=auth_headers,
        json={"status": "SHORTLISTED"},
    )
    assert shortlisted.status_code == 200
    updated = client.patch(
        f"/analysis/{analysis_id}/status",
        headers=auth_headers,
        json={"status": "INTERVIEW"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "INTERVIEW"
    history = client.get("/analysis/history", headers=auth_headers).json()[0]
    assert history["analysis_id"] == analysis_id
    assert history["status"] == "INTERVIEW"
    assert history["match_breakdown"]

    dashboard = client.get(f"/jobs/{job_id}/dashboard", headers=auth_headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["total_resumes"] == 1
    assert dashboard.json()["qualified"] == 1

    leaderboard = client.get(f"/jobs/{job_id}/leaderboard", headers=auth_headers)
    assert leaderboard.status_code == 200
    assert leaderboard.json()["total_candidates"] == 1

    bulk = client.post(
        f"/analysis/{job_id}/bulk",
        headers=auth_headers,
        files=[
            ("files", ("candidate-one.pdf", pdf_bytes, "application/pdf")),
            ("files", ("candidate-two.pdf", pdf_bytes, "application/pdf")),
        ],
    )
    assert bulk.status_code == 200
    assert bulk.json()["successful"] == 2
    assert all(item["status"] == "NEW" for item in bulk.json()["results"])
    assert all(isinstance(item["analysis_id"], int) for item in bulk.json()["results"])
    assert all(item["match_breakdown"] for item in bulk.json()["results"])

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
    assert all(isinstance(item["analysis_id"], int) for item in body["results"])
    assert all("skills" not in item for item in body["results"])


def test_analysis_status_update_enforces_ownership_not_found_and_transitions(
    client, auth_headers, pdf_bytes, monkeypatch
):
    monkeypatch.setattr(
        "app.api.analysis.generate_feedback",
        lambda *_args: {
            "summary": "Qualified",
            "strengths": ["Python"],
            "weaknesses": [],
            "recommendation": "Interview",
        },
    )
    job = client.post(
        "/jobs/",
        headers=auth_headers,
        json={
            "title": "Backend Engineer",
            "company": "Example",
            "description": "Build APIs",
            "required_skills": "Python",
            "experience": "2 years",
            "location": "Remote",
        },
    )
    analysis = client.post(
        f"/analysis/{job.json()['id']}",
        headers=auth_headers,
        files={"file": ("candidate.pdf", pdf_bytes, "application/pdf")},
    )
    analysis_id = analysis.json()["analysis_id"]

    assert client.post(
        "/auth/register",
        json={
            "username": "other-recruiter",
            "email": "other-recruiter@example.com",
            "password": "password-123",
        },
    ).status_code == 201
    other_token = client.post(
        "/auth/login",
        data={
            "username": "other-recruiter@example.com",
            "password": "password-123",
        },
    ).json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    assert client.patch(
        f"/analysis/{analysis_id}/status",
        headers=other_headers,
        json={"status": "SHORTLISTED"},
    ).status_code == 404
    assert client.patch(
        "/analysis/999999/status",
        headers=auth_headers,
        json={"status": "SHORTLISTED"},
    ).status_code == 404
    assert client.patch(
        f"/analysis/{analysis_id}/status",
        headers=auth_headers,
        json={"status": "HIRED"},
    ).status_code == 400

    updated = client.patch(
        f"/analysis/{analysis_id}/status",
        headers=auth_headers,
        json={"status": "SHORTLISTED"},
    )
    assert updated.status_code == 200
    history = client.get("/analysis/history", headers=auth_headers).json()
    persisted = next(item for item in history if item["analysis_id"] == analysis_id)
    assert persisted["status"] == "SHORTLISTED"
