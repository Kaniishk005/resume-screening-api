import re

import fitz

from app.services.skill_normalizer import extract_normalized_skills


class ResumeParsingError(ValueError):
    """Raised when an uploaded resume cannot be parsed safely."""


def extract_text_from_pdf(file_path: str) -> str:
    try:
        with fitz.open(file_path) as doc:
            if doc.page_count == 0:
                raise ResumeParsingError("The PDF is empty.")
            text = "".join(page.get_text() for page in doc)
    except ResumeParsingError:
        raise
    except (fitz.FileDataError, RuntimeError, ValueError, OSError) as exc:
        raise ResumeParsingError("The uploaded file is not a valid readable PDF.") from exc

    if not text.strip():
        raise ResumeParsingError("The PDF contains no extractable text.")
    return text


def extract_email(text: str):

    pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"

    match = re.search(pattern, text)

    return match.group() if match else ""


def extract_phone(text: str):

    pattern = r"(\+91[- ]?)?[6-9]\d{9}"

    match = re.search(pattern, text)

    return match.group() if match else ""


def extract_name(text: str):

    lines = text.split("\n")

    for line in lines:

        line = line.strip()

        if len(line.split()) >= 2 and len(line) < 40:
            return line

    return "Unknown"


def extract_skills(text: str) -> list[str]:
    return extract_normalized_skills(text)


def parse_resume(file_path: str):

    text = extract_text_from_pdf(file_path)

    return {
        "candidate_name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "skills": extract_skills(text),
        "extracted_text": text,
    }
