import re

import fitz

from app.utils.skills import SKILLS


def extract_text_from_pdf(file_path: str):

    doc = fitz.open(file_path)

    text = ""

    for page in doc:
        text += page.get_text()

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


def extract_skills(text: str):

    found = set()

    normalized_text = re.sub(r"[^a-zA-Z0-9#+]", " ", text.lower())

    for skill in SKILLS:
        if skill.lower() in normalized_text:
            found.add(skill)

        return sorted(found)


def parse_resume(file_path: str):

    text = extract_text_from_pdf(file_path)

    return {
        "candidate_name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "skills": extract_skills(text),
        "extracted_text": text,
    }
