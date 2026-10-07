"""Deterministic parsing of job descriptions into explainable requirements."""

from __future__ import annotations

import re
from collections import OrderedDict

from app.schemas.intelligence import EducationEvidence, ExperienceEvidence, JobProfile
from app.services.resume_intelligence import extract_education_evidence, extract_experience_evidence
from app.services.skill_normalizer import extract_normalized_skills


_JD_SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "required": (
        "requirements", "required", "required skills", "minimum qualifications",
        "must have", "must-have", "essential", "essential skills", "what you need", "what you'll need", "required qualifications", "qualifications",
    ),
    "preferred": (
        "preferred", "preferred qualifications", "preferred skills", "nice to have",
        "nice-to-have", "bonus", "good to have", "desired skills", "desired qualifications",
    ),
    "responsibilities": (
        "responsibilities", "what you'll do", "what you will do", "role responsibilities",
        "your impact", "duties", "key responsibilities", "core responsibilities",
    ),
    "experience": ("experience", "experience requirements", "required experience"),
    "education": ("education", "education requirements", "educational qualifications"),
}
_JD_HEADING_TO_SECTION = {
    alias.casefold(): section for section, aliases in _JD_SECTION_ALIASES.items() for alias in aliases
}

DOMAIN_KEYWORDS: tuple[str, ...] = (
    "backend development", "frontend development", "full-stack development",
    "machine learning", "data engineering", "data science", "cloud infrastructure",
    "distributed systems", "microservices", "rest api", "ci/cd", "nlp",
    "computer vision", "llm", "generative ai", "devops", "software testing",
)
_DOMAIN_ALIASES: dict[str, tuple[str, ...]] = {
    "rest api": ("rest api", "rest apis", "restful api", "restful apis"),
    "llm": ("llm", "llms", "large language model", "large language models"),
}


def _heading_value(line: str) -> tuple[str, str | None] | None:
    stripped = line.strip()
    if len(stripped) > 100:
        return None
    before, separator, after = stripped.partition(":")
    candidate = re.sub(r"^[\s\-•*|]+|[\s|\-]+$", "", before if separator else stripped)
    candidate = re.sub(r"\s+", " ", candidate).casefold()
    section = _JD_HEADING_TO_SECTION.get(candidate)
    if section:
        return section, after.strip() if separator and after.strip() else None
    return None


def detect_job_sections(text: str) -> dict[str, str]:
    """Split a JD into recognized sections without discarding unknown text."""

    sections: OrderedDict[str, list[str]] = OrderedDict()
    current = "overview"
    sections[current] = []
    for line in text.splitlines():
        heading = _heading_value(line)
        if heading:
            current, trailing = heading
            sections.setdefault(current, [])
            if trailing:
                sections[current].append(trailing)
            continue
        sections.setdefault(current, []).append(line)
    return {
        name: "\n".join(lines).strip()
        for name, lines in sections.items()
        if "\n".join(lines).strip()
    }


def _items(text: str) -> list[str]:
    """Return clean responsibility/qualification items while preserving wording."""

    lines = [re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    if not lines and text.strip():
        return [text.strip()]
    return lines


def _unique_skills(*texts: str) -> list[str]:
    return sorted({skill for text in texts for skill in extract_normalized_skills(text)})


def _extract_title(raw: str, provided: str | None) -> str | None:
    if provided and provided.strip():
        return provided.strip()
    for line in raw.splitlines():
        match = re.match(r"^\s*(?:job\s+title|role|position)\s*:\s*(.+?)\s*$", line, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    first = next((line.strip() for line in raw.splitlines() if line.strip()), "")
    if first and len(first) <= 100 and not re.match(r"^[-*•]", first) and not _heading_value(first):
        return first
    return None


def _fallback_classified_sections(raw: str) -> tuple[list[str], list[str]]:
    required_lines: list[str] = []
    preferred_lines: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lowered = stripped.casefold()
        if any(marker in lowered for marker in ("nice to have", "nice-to-have", "preferred", "bonus", "good to have", "desired")):
            preferred_lines.append(stripped)
        elif any(marker in lowered for marker in ("must have", "must-have", "required", "essential", "minimum qualification", "what you need")):
            required_lines.append(stripped)
    return required_lines, preferred_lines


def parse_job_description(description: str, title: str | None = None) -> JobProfile:
    """Parse a JD without external services or probabilistic inference."""

    raw = description.strip()
    sections = detect_job_sections(raw)
    required_text = "\n".join(
        sections.get(name, "") for name in ("required", "experience", "education")
    )
    preferred_text = "\n".join(
        sections.get(name, "") for name in ("preferred",)
    )

    if "required" not in sections and "preferred" not in sections:
        fallback_required, fallback_preferred = _fallback_classified_sections(raw)
        required_text = "\n".join(fallback_required)
        preferred_text = "\n".join(fallback_preferred)

    all_skills = _unique_skills(raw)
    preferred_skills = _unique_skills(preferred_text)
    required_skills = _unique_skills(required_text) if required_text.strip() else sorted(set(all_skills) - set(preferred_skills))
    # If explicit required headings are absent, skill mentions outside a
    # preferred block are conservatively treated as required.
    if not required_skills and not preferred_skills:
        required_skills = all_skills

    # Year expressions are explicit evidence, so scanning the complete JD is
    # safe and handles descriptions that place experience under
    # Responsibilities or Qualifications rather than a dedicated heading.
    experience_text = raw
    education_text = "\n".join(sections.get(name, "") for name in ("education", "required", "preferred", "overview"))
    experience_requirements = extract_experience_evidence(experience_text)
    education_requirements = extract_education_evidence(education_text)

    responsibilities = _items(sections.get("responsibilities", ""))
    qualifications = _items(sections.get("required", ""))
    preferred_qualifications = _items(sections.get("preferred", ""))
    domain_keywords = sorted(
        {
            keyword
            for keyword in DOMAIN_KEYWORDS
            if any(
                re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", raw, re.IGNORECASE)
                for alias in _DOMAIN_ALIASES.get(keyword, (keyword,))
            )
        }
    )

    return JobProfile(
        job_title=_extract_title(raw, title),
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        experience_requirements=experience_requirements,
        education_requirements=education_requirements,
        responsibilities=responsibilities,
        qualifications=qualifications,
        preferred_qualifications=preferred_qualifications,
        domain_keywords=domain_keywords,
        sections=sections,
        raw_description=description,
    )


# Alternate descriptive names for library callers.
parse_job = parse_job_description
build_job_profile = parse_job_description


def parse_stored_job(
    *,
    title: str,
    description: str,
    required_skills: str,
    experience: str,
) -> JobProfile:
    """Build a Phase 2 profile from the existing normalized job record."""

    composed = (
        f"{title.strip()}\n"
        f"Required Skills:\n{required_skills.strip()}\n"
        f"Experience:\n{experience.strip()}\n"
        f"Responsibilities:\n{description.strip()}"
    )
    return parse_job_description(composed, title=title)

