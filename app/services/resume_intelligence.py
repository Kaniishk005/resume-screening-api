"""Explainable, deterministic resume understanding.

The functions in this module deliberately preserve source text.  They detect
well-known section headings and explicit evidence, but do not guess employers,
dates, seniority, or other facts that are not stated in the document.
"""

from __future__ import annotations

import re
from collections import OrderedDict

from app.schemas.intelligence import (
    EducationEvidence,
    ExperienceEvidence,
    ResumeBlock,
    SkillEvidence,
    StructuredResumeProfile,
)
from app.services.parser import extract_email, extract_name, extract_phone
from app.services.skill_normalizer import extract_skill_evidence


SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "summary": ("summary", "profile", "professional summary", "objective", "career objective"),
    "skills": ("skills", "technical skills", "core competencies", "technologies", "technical expertise"),
    "experience": ("experience", "work experience", "professional experience", "employment", "employment history"),
    "projects": ("projects", "academic projects", "personal projects", "selected projects"),
    "education": ("education", "academic background", "qualifications", "educational background"),
    "certifications": ("certifications", "certificates", "licenses & certifications", "licenses and certifications"),
    "achievements": ("achievements", "awards", "honors", "honours"),
    "leadership": ("positions of responsibility", "leadership", "activities", "volunteering", "extracurricular activities"),
}

_HEADING_TO_SECTION = {
    alias.casefold(): section for section, aliases in SECTION_ALIASES.items() for alias in aliases
}


def _clean_heading(line: str) -> str:
    value = line.strip()
    value = re.sub(r"^[\s\-•*|]+", "", value)
    value = re.sub(r"[\s:|\-]+$", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.casefold()


def _section_heading(line: str) -> str | None:
    candidate = _clean_heading(line)
    if not candidate or len(candidate) > 80:
        return None
    return _HEADING_TO_SECTION.get(candidate)


def detect_sections(text: str) -> dict[str, str]:
    """Split resume text by common headings while preserving all content."""

    sections: OrderedDict[str, list[str]] = OrderedDict()
    current = "other"
    sections[current] = []
    for line in text.splitlines():
        detected = _section_heading(line)
        if detected:
            current = detected
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)

    return {
        name: "\n".join(lines).strip()
        for name, lines in sections.items()
        if "\n".join(lines).strip()
    }


def _blocks(section_text: str, section: str) -> list[ResumeBlock]:
    """Create conservative blocks without trying to infer missing metadata."""

    text = section_text.strip()
    if not text:
        return []
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", text) if chunk.strip()]
    if len(chunks) == 1:
        lines = [line.strip() for line in chunks[0].splitlines() if line.strip()]
        bullets = [line for line in lines if re.match(r"^(?:[-*•]|\d+[.)])\s+", line)]
        if len(bullets) >= 2 and len(bullets) == len(lines):
            chunks = [re.sub(r"^(?:[-*•]|\d+[.)])\s+", "", line) for line in bullets]

    result: list[ResumeBlock] = []
    for chunk in chunks:
        lines = chunk.splitlines()
        heading = lines[0].strip() if len(lines) > 1 else None
        content = chunk.strip()
        result.append(
            ResumeBlock(
                heading=heading,
                content=content,
                skills=sorted({e.canonical_skill for e in extract_skill_evidence(content)}),
                section=section,
            )
        )
    return result


_EXPERIENCE_PATTERN = re.compile(
    r"\b(?:(?:at\s+least|minimum(?:\s+of)?|over|more\s+than)\s+)?"
    r"(?P<minimum>\d+(?:\.\d+)?)\s*"
    r"(?:\+\s*|[-–]\s*(?P<maximum>\d+(?:\.\d+)?)\s*)?"
    r"(?:years?|yrs?)\b(?:\s+of\s+[^\n.;,]*)?",
    re.IGNORECASE,
)


def extract_experience_evidence(text: str, section: str | None = None) -> list[ExperienceEvidence]:
    """Extract explicit year ranges; date strings without ``years`` are ignored."""

    results: list[ExperienceEvidence] = []
    seen: set[tuple[float | None, float | None, str]] = set()
    for match in _EXPERIENCE_PATTERN.finditer(text):
        minimum = float(match.group("minimum"))
        maximum = float(match.group("maximum")) if match.group("maximum") else None
        raw = re.sub(r"\s+", " ", match.group(0)).strip()
        key = (minimum, maximum, raw.casefold())
        if key in seen:
            continue
        seen.add(key)
        results.append(
            ExperienceEvidence(
                minimum_years=minimum,
                maximum_years=maximum,
                raw_text=raw,
                section=section,
            )
        )
    return results


_DEGREE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("Bachelor's degree", r"bachelor(?:'s|s)?\s+degree"),
    ("Master's degree", r"master(?:'s|s)?\s+degree"),
    ("B.Tech", r"b\.?\s*tech\.?"),
    ("B.E.", r"b\.?\s*e\.?"),
    ("BSc", r"b\.?\s*sc\.?"),
    ("BS", r"\bbs\b"),
    ("BCA", r"bca"),
    ("M.Tech", r"m\.?\s*tech\.?"),
    ("MSc", r"m\.?\s*sc\.?"),
    ("MS", r"\bms\b"),
    ("MCA", r"mca"),
    ("MBA", r"mba"),
)
_FIELD_PATTERN = re.compile(r"\b(computer\s+science|information\s+technology|software\s+engineering|data\s+science|related\s+field)\b", re.IGNORECASE)


def extract_education_evidence(text: str, section: str | None = None) -> list[EducationEvidence]:
    results: list[EducationEvidence] = []
    seen: set[tuple[str | None, str]] = set()
    for line in (line.strip() for line in text.splitlines() if line.strip()):
        degree = None
        for label, pattern in _DEGREE_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                degree = label
                break
        field_match = _FIELD_PATTERN.search(line)
        field = field_match.group(1) if field_match else None
        if degree or field:
            raw = re.sub(r"\s+", " ", line)
            key = (degree, raw.casefold())
            if key not in seen:
                seen.add(key)
                results.append(EducationEvidence(degree=degree, field=field, raw_text=raw, section=section))
    return results


def _skill_evidence_for_sections(sections: dict[str, str]) -> list[SkillEvidence]:
    evidence: list[SkillEvidence] = []
    for section, content in sections.items():
        for item in extract_skill_evidence(content, section=section):
            start = max(0, item.start - 45)
            end = min(len(content), item.end + 45)
            context = re.sub(r"\s+", " ", content[start:end]).strip()
            evidence.append(
                SkillEvidence(
                    canonical_skill=item.canonical_skill,
                    matched_text=item.matched_text,
                    section=section,
                    context=context,
                )
            )
    return evidence


def build_resume_profile(text: str, filename: str | None = None) -> StructuredResumeProfile:
    """Build a structured profile from extracted resume text."""

    sections = detect_sections(text)
    section_evidence = _skill_evidence_for_sections(sections)
    skills = sorted({item.canonical_skill for item in section_evidence})
    if not skills:
        skills = sorted({item.canonical_skill for item in extract_skill_evidence(text)})

    experience_text = sections.get("experience", "")
    education_text = sections.get("education", "")
    profile = StructuredResumeProfile(
        filename=filename,
        candidate_name=extract_name(text),
        email=extract_email(text),
        phone=extract_phone(text),
        skills=skills,
        skill_evidence=section_evidence,
        experience=_blocks(experience_text, "experience"),
        experience_evidence=extract_experience_evidence(experience_text or text, "experience" if experience_text else None),
        projects=_blocks(sections.get("projects", ""), "projects"),
        education=_blocks(education_text, "education"),
        education_evidence=extract_education_evidence(education_text or text, "education" if education_text else None),
        certifications=_blocks(sections.get("certifications", ""), "certifications"),
        achievements=_blocks(sections.get("achievements", ""), "achievements"),
        leadership=_blocks(sections.get("leadership", ""), "leadership"),
        sections=sections,
        extracted_text=text,
    )
    return profile


# Descriptive alias for callers that prefer a parser-style name.
parse_resume_intelligence = build_resume_profile

