"""Build bounded, privacy-reduced facts for advisory AI feedback."""

from __future__ import annotations

import re

from app.schemas.feedback import GroundedFact, GroundedFeedbackContext
from app.schemas.intelligence import JobProfile, StructuredResumeProfile
from app.schemas.matching import MatchResult


MAX_EVIDENCE_SNIPPET_LENGTH = 240
MAX_EVIDENCE_SNIPPETS_PER_FACT = 2
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d(). -]{7,}\d)(?!\w)")
_LABELED_SENSITIVE_VALUE = re.compile(
    r"(?im)\b(?:age|date of birth|dob|gender|sex|race|ethnicity|religion|"
    r"disability|marital status|nationality|home address|address)\s*[:=-]"
    r"[^\n,;|.]*"
)


def _privacy_reduce(value: str, blocked_values: tuple[str, ...]) -> str:
    reduced = value
    for blocked in blocked_values:
        if blocked.strip():
            reduced = re.sub(re.escape(blocked.strip()), "[redacted]", reduced, flags=re.I)
    reduced = _EMAIL.sub("[redacted-email]", reduced)
    reduced = _PHONE.sub("[redacted-phone]", reduced)
    return _LABELED_SENSITIVE_VALUE.sub("[redacted-sensitive-data]", reduced)


def _bounded_snippet(value: str, blocked_values: tuple[str, ...] = ()) -> str:
    value = _privacy_reduce(value, blocked_values)
    compact = re.sub(r"\s+", " ", value).strip()
    if len(compact) <= MAX_EVIDENCE_SNIPPET_LENGTH:
        return compact
    boundary = compact.rfind(" ", 0, MAX_EVIDENCE_SNIPPET_LENGTH - 1)
    if boundary < MAX_EVIDENCE_SNIPPET_LENGTH // 2:
        boundary = MAX_EVIDENCE_SNIPPET_LENGTH - 1
    return compact[:boundary].rstrip(" ,;:") + "…"


def _evidence(items, blocked_values: tuple[str, ...]) -> tuple[str | None, list[str]]:
    selected = list(items)[:MAX_EVIDENCE_SNIPPETS_PER_FACT]
    section = next((item.section for item in selected if item.section), None)
    snippets = [
        _bounded_snippet(item.context, blocked_values)
        for item in selected
        if item.context.strip()
    ]
    return section, snippets


def build_feedback_context(
    resume_profile: StructuredResumeProfile,
    job_profile: JobProfile,
    match_result: MatchResult,
) -> GroundedFeedbackContext:
    """Return deterministic facts only; no identity, database, secrets, or network."""

    facts: list[GroundedFact] = []
    blocked_values = (
        resume_profile.candidate_name,
        resume_profile.email,
        resume_profile.phone,
    )
    for index, detail in enumerate(match_result.required_skill_details, start=1):
        section, snippets = _evidence(detail.evidence, blocked_values)
        facts.append(
            GroundedFact(
                fact_id=f"REQ_SKILL_{index}",
                category="required_skill",
                fact=detail.reason,
                section=section,
                evidence=snippets,
            )
        )
    for index, detail in enumerate(match_result.preferred_skill_details, start=1):
        section, snippets = _evidence(detail.evidence, blocked_values)
        facts.append(
            GroundedFact(
                fact_id=f"PREF_SKILL_{index}",
                category="preferred_skill",
                fact=detail.reason,
                section=section,
                evidence=snippets,
            )
        )
    for index, detail in enumerate(match_result.experience_details, start=1):
        section, snippets = _evidence(detail.evidence, blocked_values)
        facts.append(
            GroundedFact(
                fact_id=f"EXP_{index}",
                category="experience",
                fact=detail.reason,
                section=section,
                evidence=snippets,
            )
        )
    for index, detail in enumerate(match_result.education_details, start=1):
        section, snippets = _evidence(detail.evidence, blocked_values)
        facts.append(
            GroundedFact(
                fact_id=f"EDU_{index}",
                category="education",
                fact=detail.reason,
                section=section,
                evidence=snippets,
            )
        )

    role_component = match_result.components["role_relevance"]
    role_fact = " ".join(role_component.explanation)
    facts.append(
        GroundedFact(
            fact_id="ROLE_1",
            category="role_relevance",
            fact=role_fact,
            section="experience_or_projects",
            evidence=[],
        )
    )

    return GroundedFeedbackContext(
        job_title=job_profile.job_title,
        overall_score=match_result.overall_score,
        evidence_coverage=match_result.evidence_coverage,
        required_skills_demonstrated=match_result.matched_required_skills,
        required_skills_not_demonstrated=match_result.missing_required_skills,
        preferred_skills_demonstrated=match_result.matched_preferred_skills,
        preferred_skills_not_demonstrated=match_result.missing_preferred_skills,
        experience_results=[detail.reason for detail in match_result.experience_details],
        education_results=[detail.reason for detail in match_result.education_details],
        role_relevance_result=role_fact,
        deterministic_strengths=match_result.strengths,
        deterministic_gaps=match_result.gaps,
        facts=facts,
    )


def deterministic_feedback(match_result: MatchResult) -> dict:
    """Identify provider failure honestly while preserving deterministic facts."""

    return {
        "summary": (
            "Deterministic resume-job alignment was completed, but AI-generated "
            "feedback is temporarily unavailable."
        ),
        "strengths": match_result.strengths,
        "weaknesses": match_result.gaps,
        "recommendation": (
            "Review the evidence gaps above. Add job-relevant evidence only where "
            "it accurately reflects your experience."
        ),
        "evidence_references": {},
        "limitations": ["AI-generated feedback was unavailable for this analysis."],
        "feedback_source": "deterministic_fallback",
        "feedback_status": "unavailable",
        "grounding_version": "1.0",
    }
