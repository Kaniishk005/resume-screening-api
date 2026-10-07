import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from fastapi import UploadFile

from app.core.config import settings


class UploadValidationError(ValueError):
    pass


def validate_pdf_upload(file: UploadFile) -> None:
    filename = file.filename or ""
    if Path(filename).suffix.lower() != ".pdf":
        raise UploadValidationError("Only PDF files are supported.")

    allowed_content_types = {"application/pdf", "application/x-pdf"}
    if file.content_type and file.content_type.lower() not in allowed_content_types:
        raise UploadValidationError("The uploaded file must have a PDF content type.")


@contextmanager
def temporary_pdf(file: UploadFile) -> Iterator[str]:
    validate_pdf_upload(file)
    path: str | None = None
    total = 0
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp:
            path = temp.name
            while chunk := file.file.read(64 * 1024):
                total += len(chunk)
                if total > settings.MAX_UPLOAD_SIZE_BYTES:
                    raise UploadValidationError(
                        f"PDF exceeds the maximum upload size of "
                        f"{settings.MAX_UPLOAD_SIZE_BYTES} bytes."
                    )
                temp.write(chunk)

        if total == 0:
            raise UploadValidationError("The uploaded PDF is empty.")
        yield path
    finally:
        try:
            file.file.close()
        finally:
            if path and os.path.exists(path):
                os.remove(path)
