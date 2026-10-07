from datetime import timedelta

from app.core.security import create_access_token


JOB = {
    "title": "Backend Engineer",
    "company": "Example",
    "description": "Build APIs",
    "required_skills": "Python, FastAPI",
    "experience": "2 years",
    "location": "Remote",
}


def register_and_login(client, username, email):
    assert client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": "password-123"},
    ).status_code == 201
    token = client.post(
        "/auth/login", data={"username": email, "password": "password-123"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_protected_endpoint_rejects_missing_token(client):
    assert client.get("/jobs/").status_code == 401


def test_invalid_token_returns_401(client):
    response = client.get("/jobs/", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401


def test_expired_token_returns_401(client):
    token = create_access_token(
        {"sub": "expired@example.com"}, expires_delta=timedelta(seconds=-1)
    )
    response = client.get("/jobs/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_job_creation_and_listing_are_owner_scoped(client, auth_headers):
    created = client.post("/jobs/", json=JOB, headers=auth_headers)
    assert created.status_code == 201
    other_headers = register_and_login(client, "other", "other@example.com")
    assert client.get("/jobs/", headers=other_headers).json() == []
    jobs = client.get("/jobs/", headers=auth_headers).json()
    assert [job["id"] for job in jobs] == [created.json()["id"]]


def test_job_deletion_and_missing_job(client, auth_headers):
    job_id = client.post("/jobs/", json=JOB, headers=auth_headers).json()["id"]
    assert client.delete(f"/jobs/{job_id}", headers=auth_headers).status_code == 200
    assert client.delete(f"/jobs/{job_id}", headers=auth_headers).status_code == 404


def test_another_user_cannot_delete_job(client, auth_headers):
    job_id = client.post("/jobs/", json=JOB, headers=auth_headers).json()["id"]
    other_headers = register_and_login(client, "other", "other@example.com")
    assert client.delete(f"/jobs/{job_id}", headers=other_headers).status_code == 404
    assert client.get(f"/jobs/{job_id}", headers=auth_headers).status_code == 200


def test_analysis_with_mocked_ai_output(client, auth_headers, pdf_bytes, monkeypatch):
    feedback = {
        "summary": "Qualified candidate",
        "strengths": ["Python"],
        "weaknesses": [],
        "recommendation": "Interview",
    }
    monkeypatch.setattr("app.api.analysis.generate_feedback", lambda *args: feedback)
    job_id = client.post("/jobs/", json=JOB, headers=auth_headers).json()["id"]
    response = client.post(
        f"/analysis/{job_id}",
        headers=auth_headers,
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["ai_feedback"] == feedback
