import io
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import UploadFile

from app.core.config import settings
from app.services.parser import ResumeParsingError, extract_skills, parse_resume
from app.services.uploads import UploadValidationError, temporary_pdf


def test_skill_extraction_detects_multiple_skills():
    assert extract_skills("Python, FastAPI, Docker and PostgreSQL") == [
        "Docker",
        "FastAPI",
        "PostgreSQL",
        "Python",
    ]


def test_skill_extraction_returns_empty_list():
    assert extract_skills("Experienced technical writer and project coordinator") == []


def test_skill_extraction_avoids_substring_false_positive():
    assert "C" not in extract_skills("I use Scikit-learn and React")


def test_parser_response_contains_expected_keys(tmp_path, pdf_bytes):
    path = tmp_path / "resume.pdf"
    path.write_bytes(pdf_bytes)
    result = parse_resume(str(path))
    assert set(result) == {
        "candidate_name",
        "email",
        "phone",
        "skills",
        "extracted_text",
    }


def test_corrupt_pdf_has_controlled_error(tmp_path):
    path = tmp_path / "bad.pdf"
    path.write_bytes(b"not a pdf")
    with pytest.raises(ResumeParsingError, match="valid readable PDF"):
        parse_resume(str(path))


def test_temporary_file_cleaned_after_success(monkeypatch, pdf_bytes, tmp_path):
    path = tmp_path / "safe-temp.pdf"

    class ManagedFile:
        def __enter__(self):
            self.handle = path.open("wb")
            return self.handle

        def __exit__(self, *args):
            self.handle.close()

    monkeypatch.setattr("app.services.uploads.tempfile.NamedTemporaryFile", lambda **_: ManagedFile())
    upload = UploadFile(filename="../../resume.pdf", file=io.BytesIO(pdf_bytes), headers={"content-type": "application/pdf"})
    with temporary_pdf(upload) as saved:
        assert Path(saved) == path
        assert path.exists()
    assert not path.exists()


def test_temporary_file_cleaned_after_failure(monkeypatch, pdf_bytes, tmp_path):
    path = tmp_path / "failed-temp.pdf"

    class ManagedFile:
        def __enter__(self):
            self.handle = path.open("wb")
            return self.handle

        def __exit__(self, *args):
            self.handle.close()

    monkeypatch.setattr("app.services.uploads.tempfile.NamedTemporaryFile", lambda **_: ManagedFile())
    upload = UploadFile(filename="resume.pdf", file=io.BytesIO(pdf_bytes), headers={"content-type": "application/pdf"})
    with pytest.raises(RuntimeError):
        with temporary_pdf(upload):
            raise RuntimeError("processing failed")
    assert not path.exists()


def test_oversized_upload_rejected(monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_BYTES", 4)
    upload = UploadFile(filename="resume.pdf", file=io.BytesIO(b"12345"), headers={"content-type": "application/pdf"})
    with pytest.raises(UploadValidationError, match="maximum upload size"):
        with temporary_pdf(upload):
            pass


def test_upload_api_rejects_non_pdf(client, auth_headers):
    response = client.post(
        "/resume/upload",
        headers=auth_headers,
        files={"file": ("resume.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 415


def test_upload_api_uses_extracted_text(client, auth_headers, pdf_bytes):
    response = client.post(
        "/resume/upload",
        headers=auth_headers,
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    assert "Jane Doe" in response.json()["extracted_text"]
