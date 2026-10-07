import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


TEST_DB = Path(__file__).with_name("test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-not-used-in-production"
os.environ["GROQ_API_KEY"] = "test-key"

from app.db.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


engine = create_engine(
    os.environ["DATABASE_URL"], connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "recruiter",
            "email": "recruiter@example.com",
            "password": "secure-password",
        },
    )
    assert response.status_code == 201
    response = client.post(
        "/auth/login",
        data={"username": "recruiter@example.com", "password": "secure-password"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def pdf_bytes():
    import fitz

    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Jane Doe\nPython FastAPI Docker\njane@example.com")
    content = document.tobytes()
    document.close()
    return content
