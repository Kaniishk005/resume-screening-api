def test_allowed_origin_preflight(client):
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_allowed_origin_normal_request(client):
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_unconfigured_origin_is_not_allowed(client):
    response = client.get("/health", headers={"Origin": "https://untrusted.example"})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_cors_does_not_bypass_authentication(client):
    response = client.get("/jobs", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 401
