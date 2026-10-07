"""Pure deterministic resume/job alignment evaluation.

Only structured Phase 2 document facts participate. Candidate identity,
contact details, protected attributes, databases, network calls, and LLMs are
deliberately outside this module.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from app.core.constants import MATCH_WEIGHTS
from app.schemas.intelligence import EducationEvidence, ExperienceEvidence, JobProfile, StructuredResumeProfile
from app.schemas.matching import (
    EducationMatchDetail,
    EvidenceReference,
    ExperienceMatchDetail,
    MatchComponent,
    MatchResult,
    MatchStatus,
    SkillMatchDetail,
)
from app.services.skill_normalizer import extract_normalized_skills, normalize_skill_name


_DEGREE_LEVELS = {
    "bachelor's degree": 1,
    "b.tech": 1,
    "b.e.": 1,
    "bsc": 1,
    "bs": 1,
    "bca": 1,
    "master's degree": 2,
    "m.tech": 2,
    "msc": 2,
    "ms": 2,
    "mca": 2,
    "mba": 2,
}

_COMPUTING_FIELDS = {
    "computer science",
    "information technology",
    "software engineering",
    "data science",
}

_ROLE_STOP_WORDS = {
    "and", "the", "with", "using", "for", "from", "into", "that", "this",
    "your", "our", "you", "will", "must", "have", "has", "are", "is", "be",
    "build", "develop", "maintain", "work", "working", "responsible", "role",
    "team", "teams", "strong", "knowledge", "experience", "years", "skills",
    "ability", "including", "related", "field", "candidate", "preferred",
}

_SCORING_SECTIONS = {
    "summary",
    "skills",
    "experience",
    "projects",
    "certifications",
}


def _clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


def _canonical_skills(skills: Iterable[str]) -> list[str]:
    canonical: set[str] = set()
    for skill in skills:
        normalized = normalize_skill_name(skill)
        canonical.add(normalized or skill.strip())
    return sorted(item for item in canonical if item)


def _evidence_for_skill(profile: StructuredResumeProfile, skill: str) -> list[EvidenceReference]:
    return [
        EvidenceReference(
            section=item.section,
            context=item.context or item.matched_text,
            matched_text=item.matched_text,
        )
        for item in profile.skill_evidence
        if item.canonical_skill == skill and item.section in _SCORING_SECTIONS
    ]


def _scoring_skills(profile: StructuredResumeProfile) -> set[str]:
    """Return skills backed by explicitly job-relevant resume sections.

    Unlabelled header/contact/address content is intentionally excluded so
    candidate identity and other personal attributes cannot affect scoring.
    """

    return {
        item.canonical_skill
        for item in profile.skill_evidence
        if item.section in _SCORING_SECTIONS
    }


def _score_skills(
    requested: list[str],
    profile: StructuredResumeProfile,
    component_name: str,
) -> tuple[MatchComponent, list[SkillMatchDetail], list[str], list[str]]:
    skills = _canonical_skills(requested)
    resume_skills = _scoring_skills(profile)
    base_weight = MATCH_WEIGHTS[component_name]
    if not skills:
        return (
            MatchComponent(
                status=MatchStatus.NOT_APPLICABLE,
                base_weight=base_weight,
                explanation=[f"The job description contains no {component_name.replace('_', ' ')}."],
            ),
            [],
            [],
            [],
        )

    details: list[SkillMatchDetail] = []
    matched: list[str] = []
    missing: list[str] = []
    evidence_supported = 0
    for skill in skills:
        evidence = _evidence_for_skill(profile, skill)
        if skill in resume_skills:
            matched.append(skill)
            evidence_supported += int(bool(evidence))
            details.append(
                SkillMatchDetail(
                    skill=skill,
                    status=MatchStatus.MATCHED,
                    evidence=evidence,
                    reason=f"{skill} is explicitly demonstrated in the resume.",
                )
            )
        else:
            missing.append(skill)
            details.append(
                SkillMatchDetail(
                    skill=skill,
                    status=MatchStatus.NOT_DEMONSTRATED,
                    reason=f"{skill} was requested but was not detected in the resume.",
                )
            )

    score = _clamp(100 * len(matched) / len(skills))
    status = (
        MatchStatus.MATCHED
        if len(matched) == len(skills)
        else MatchStatus.PARTIAL
        if matched
        else MatchStatus.NOT_DEMONSTRATED
    )
    label = component_name.replace("_", " ")
    return (
        MatchComponent(
            status=status,
            score=score,
            base_weight=base_weight,
            evidence_coverage=_clamp(100 * evidence_supported / len(skills)),
            matched_count=len(matched),
            total_count=len(skills),
            explanation=[f"{len(matched)} of {len(skills)} {label} are demonstrated."],
        ),
        details,
        matched,
        missing,
    )


def _experience_score(requirement: ExperienceEvidence, evidence: ExperienceEvidence) -> float:
    required = requirement.minimum_years
    demonstrated = evidence.minimum_years
    if required is None or required <= 0:
        return 100.0
    if demonstrated is None:
        return 0.0
    if demonstrated >= required:
        return 100.0
    return _clamp(100 * demonstrated / required)


def _score_experience(
    requirements: list[ExperienceEvidence],
    resume_evidence: list[ExperienceEvidence],
) -> tuple[MatchComponent, list[ExperienceMatchDetail]]:
    weight = MATCH_WEIGHTS["experience"]
    if not requirements:
        return (
            MatchComponent(
                status=MatchStatus.NOT_APPLICABLE,
                base_weight=weight,
                explanation=["The job description contains no explicit experience-duration requirement."],
            ),
            [],
        )

    details: list[ExperienceMatchDetail] = []
    for requirement in requirements:
        if not resume_evidence:
            details.append(
                ExperienceMatchDetail(
                    required_minimum_years=requirement.minimum_years,
                    required_maximum_years=requirement.maximum_years,
                    status=MatchStatus.NOT_DEMONSTRATED,
                    score=0.0,
                    reason="No explicit duration evidence was found in the resume.",
                )
            )
            continue
        best = max(resume_evidence, key=lambda item: _experience_score(requirement, item))
        score = _experience_score(requirement, best)
        status = MatchStatus.MATCHED if score == 100 else MatchStatus.PARTIAL
        required_text = requirement.raw_text
        details.append(
            ExperienceMatchDetail(
                required_minimum_years=requirement.minimum_years,
                required_maximum_years=requirement.maximum_years,
                demonstrated_minimum_years=best.minimum_years,
                demonstrated_maximum_years=best.maximum_years,
                status=status,
                score=score,
                evidence=[EvidenceReference(section=best.section, context=best.raw_text)],
                reason=(
                    f"The resume explicitly demonstrates {best.raw_text}, satisfying {required_text}."
                    if status == MatchStatus.MATCHED
                    else f"The resume explicitly demonstrates {best.raw_text} against the stated requirement {required_text}."
                ),
            )
        )

    score = _clamp(sum(item.score for item in details) / len(details))
    if all(item.status == MatchStatus.MATCHED for item in details):
        status = MatchStatus.MATCHED
    elif any(item.score > 0 for item in details):
        status = MatchStatus.PARTIAL
    else:
        status = MatchStatus.NOT_DEMONSTRATED
    coverage = _clamp(100 * sum(bool(item.evidence) for item in details) / len(details))
    return (
        MatchComponent(
            status=status,
            score=score,
            base_weight=weight,
            evidence_coverage=coverage,
            matched_count=sum(item.status == MatchStatus.MATCHED for item in details),
            total_count=len(details),
            explanation=[item.reason for item in details],
        ),
        details,
    )


def _degree_level(degree: str | None) -> int | None:
    if not degree:
        return None
    return _DEGREE_LEVELS.get(degree.casefold())


def _normalized_field(field: str | None) -> str | None:
    if not field:
        return None
    return re.sub(r"\s+", " ", field.strip().casefold())


def _education_score(
    requirement: EducationEvidence,
    evidence: EducationEvidence,
) -> tuple[float, bool, bool]:
    degree_required = bool(requirement.degree)
    field_required = bool(requirement.field and _normalized_field(requirement.field) != "related field")
    degree_match = not degree_required
    if degree_required:
        required_level = _degree_level(requirement.degree)
        demonstrated_level = _degree_level(evidence.degree)
        degree_match = bool(
            required_level is not None
            and demonstrated_level is not None
            and demonstrated_level >= required_level
        )

    field_match = not field_required
    if field_required:
        required_field = _normalized_field(requirement.field)
        demonstrated_field = _normalized_field(evidence.field)
        field_match = demonstrated_field == required_field
        if not field_match and "related field" in requirement.raw_text.casefold():
            field_match = bool(
                required_field in _COMPUTING_FIELDS and demonstrated_field in _COMPUTING_FIELDS
            )

    if degree_required and field_required:
        score = (60.0 if degree_match else 0.0) + (40.0 if field_match else 0.0)
    elif degree_required:
        score = 100.0 if degree_match else 0.0
    elif field_required:
        score = 100.0 if field_match else 0.0
    else:
        score = 100.0
    return score, degree_match, field_match


def _score_education(
    requirements: list[EducationEvidence],
    resume_evidence: list[EducationEvidence],
) -> tuple[MatchComponent, list[EducationMatchDetail]]:
    weight = MATCH_WEIGHTS["education"]
    if not requirements:
        return (
            MatchComponent(
                status=MatchStatus.NOT_APPLICABLE,
                base_weight=weight,
                explanation=["The job description contains no explicit education requirement."],
            ),
            [],
        )

    details: list[EducationMatchDetail] = []
    for requirement in requirements:
        if not resume_evidence:
            details.append(
                EducationMatchDetail(
                    required_degree=requirement.degree,
                    required_field=requirement.field,
                    status=MatchStatus.NOT_DEMONSTRATED,
                    score=0.0,
                    reason="No explicit education evidence was found in the resume.",
                )
            )
            continue
        scored = [(_education_score(requirement, evidence), evidence) for evidence in resume_evidence]
        (score, degree_match, field_match), best = max(scored, key=lambda item: item[0][0])
        status = MatchStatus.MATCHED if score == 100 else MatchStatus.PARTIAL if score > 0 else MatchStatus.NOT_DEMONSTRATED
        if status == MatchStatus.MATCHED:
            reason = f"The resume education evidence satisfies {requirement.raw_text}."
        elif degree_match and not field_match:
            reason = "The degree level is demonstrated, but the requested field is not demonstrated."
        elif field_match and not degree_match:
            reason = "The requested field is demonstrated, but the required degree level is not demonstrated."
        else:
            reason = "The requested degree and field are not demonstrated by the resume education evidence."
        details.append(
            EducationMatchDetail(
                required_degree=requirement.degree,
                required_field=requirement.field,
                demonstrated_degree=best.degree,
                demonstrated_field=best.field,
                status=status,
                score=_clamp(score),
                evidence=[EvidenceReference(section=best.section, context=best.raw_text)],
                reason=reason,
            )
        )

    score = _clamp(sum(item.score for item in details) / len(details))
    status = (
        MatchStatus.MATCHED
        if all(item.status == MatchStatus.MATCHED for item in details)
        else MatchStatus.PARTIAL
        if any(item.score > 0 for item in details)
        else MatchStatus.NOT_DEMONSTRATED
    )
    coverage = _clamp(100 * sum(bool(item.evidence) for item in details) / len(details))
    return (
        MatchComponent(
            status=status,
            score=score,
            base_weight=weight,
            evidence_coverage=coverage,
            matched_count=sum(item.status == MatchStatus.MATCHED for item in details),
            total_count=len(details),
            explanation=[item.reason for item in details],
        ),
        details,
    )


def _technical_terms(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z][a-z0-9+#.-]{2,}", text.casefold())
        if token not in _ROLE_STOP_WORDS and not token.isdigit()
    }


def _score_role_relevance(
    profile: StructuredResumeProfile,
    job: JobProfile,
) -> MatchComponent:
    weight = MATCH_WEIGHTS["role_relevance"]
    responsibility_text = "\n".join(job.responsibilities)
    target_skills = set(extract_normalized_skills(responsibility_text))
    target_domains = set(job.domain_keywords)
    target_terms = _technical_terms(responsibility_text)
    signals = {f"skill:{item}" for item in target_skills}
    signals |= {f"domain:{item}" for item in target_domains}
    signals |= {f"term:{item}" for item in target_terms}
    if not signals:
        return MatchComponent(
            status=MatchStatus.NOT_APPLICABLE,
            base_weight=weight,
            explanation=["The job description contains no deterministic responsibility signals to compare."],
        )

    relevant_blocks = [*profile.experience, *profile.projects]
    resume_text = "\n".join(block.content for block in relevant_blocks)
    resume_skills = set(extract_normalized_skills(resume_text))
    resume_terms = _technical_terms(resume_text)
    matched: set[str] = set()
    for signal in signals:
        kind, value = signal.split(":", 1)
        if kind == "skill" and value in resume_skills:
            matched.add(signal)
        elif kind == "domain" and re.search(rf"(?<![a-z0-9]){re.escape(value)}(?![a-z0-9])", resume_text, re.IGNORECASE):
            matched.add(signal)
        elif kind == "term" and value in resume_terms:
            matched.add(signal)

    score = _clamp(100 * len(matched) / len(signals))
    status = MatchStatus.MATCHED if score == 100 else MatchStatus.PARTIAL if score > 0 else MatchStatus.NOT_DEMONSTRATED
    return MatchComponent(
        status=status,
        score=score,
        base_weight=weight,
        evidence_coverage=score,
        matched_count=len(matched),
        total_count=len(signals),
        explanation=[
            f"{len(matched)} of {len(signals)} deterministic responsibility signals appear in resume experience or projects."
        ],
    )


def _apply_weights(components: dict[str, MatchComponent]) -> tuple[float, float]:
    active = [component for component in components.values() if component.status != MatchStatus.NOT_APPLICABLE]
    active_weight = sum(component.base_weight for component in active)
    if not active or active_weight <= 0:
        return 0.0, 0.0
    overall = 0.0
    evidence_coverage = 0.0
    for component in components.values():
        if component.status == MatchStatus.NOT_APPLICABLE:
            component.effective_weight = 0.0
            component.contribution = 0.0
            continue
        component.effective_weight = component.base_weight / active_weight
        component.contribution = _clamp((component.score or 0.0) * component.effective_weight)
        overall += component.contribution
        evidence_coverage += component.evidence_coverage * component.effective_weight
    return _clamp(overall), _clamp(evidence_coverage)


def evaluate_match(
    resume_profile: StructuredResumeProfile,
    job_profile: JobProfile,
) -> MatchResult:
    """Evaluate document alignment without databases, secrets, HTTP, or LLMs."""

    required_component, required_details, matched_required, missing_required = _score_skills(
        job_profile.required_skills, resume_profile, "required_skills"
    )
    required_set = set(_canonical_skills(job_profile.required_skills))
    preferred_only = [
        skill for skill in _canonical_skills(job_profile.preferred_skills) if skill not in required_set
    ]
    preferred_component, preferred_details, matched_preferred, missing_preferred = _score_skills(
        preferred_only, resume_profile, "preferred_skills"
    )
    experience_component, experience_details = _score_experience(
        job_profile.experience_requirements,
        [item for item in resume_profile.experience_evidence if item.section == "experience"],
    )
    education_component, education_details = _score_education(
        job_profile.education_requirements,
        [item for item in resume_profile.education_evidence if item.section == "education"],
    )
    role_component = _score_role_relevance(resume_profile, job_profile)
    components = {
        "required_skills": required_component,
        "preferred_skills": preferred_component,
        "experience": experience_component,
        "education": education_component,
        "role_relevance": role_component,
    }
    overall_score, evidence_coverage = _apply_weights(components)

    strengths: list[str] = []
    gaps: list[str] = []
    if required_component.total_count:
        strengths.append(
            f"{required_component.matched_count} of {required_component.total_count} required technical skills are demonstrated."
        )
    gaps.extend(
        f"{skill} is required by the job description but was not detected in the resume."
        for skill in missing_required
    )
    if preferred_component.total_count:
        strengths.append(
            f"{preferred_component.matched_count} of {preferred_component.total_count} preferred technical skills are demonstrated."
        )
    gaps.extend(
        f"{skill} is preferred rather than required and was not detected in the resume."
        for skill in missing_preferred
    )
    if experience_component.status == MatchStatus.MATCHED:
        strengths.append("The explicit resume duration evidence satisfies the stated experience requirement.")
    elif experience_component.status == MatchStatus.NOT_DEMONSTRATED:
        gaps.append("The role asks for explicit experience duration, but no qualifying duration was detected in the resume.")
    elif experience_component.status == MatchStatus.PARTIAL:
        gaps.append("The resume's explicit duration evidence only partially aligns with the stated experience requirement.")
    if education_component.status == MatchStatus.MATCHED:
        strengths.append("The explicit education evidence satisfies the stated education requirement.")
    elif education_component.status == MatchStatus.NOT_DEMONSTRATED:
        gaps.append("The stated education requirement was not demonstrated by explicit resume education evidence.")
    elif education_component.status == MatchStatus.PARTIAL:
        gaps.append("The explicit education evidence only partially aligns with the stated degree or field requirement.")
    if role_component.status == MatchStatus.MATCHED:
        strengths.append("Resume experience/projects cover all deterministic responsibility signals.")
    elif role_component.status in {MatchStatus.PARTIAL, MatchStatus.NOT_DEMONSTRATED}:
        gaps.append("Resume experience/projects do not demonstrate all deterministic responsibility signals.")

    explanation = [
        f"{name.replace('_', ' ').title()}: "
        f"{component.score if component.score is not None else 'N/A'} with "
        f"{round(component.effective_weight * 100, 2)}% effective weight, "
        f"contributing {component.contribution} points."
        for name, component in components.items()
    ]

    return MatchResult(
        overall_score=overall_score,
        evidence_coverage=evidence_coverage,
        components=components,
        matched_required_skills=matched_required,
        missing_required_skills=missing_required,
        matched_preferred_skills=matched_preferred,
        missing_preferred_skills=missing_preferred,
        required_skill_details=required_details,
        preferred_skill_details=preferred_details,
        experience_details=experience_details,
        education_details=education_details,
        strengths=strengths,
        gaps=gaps,
        explanation=explanation,
    )
