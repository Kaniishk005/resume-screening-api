"""Schemas for deterministic, evidence-backed resume/job alignment."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class MatchStatus(str, Enum):
    MATCHED = "MATCHED"
    PARTIAL = "PARTIAL"
    NOT_DEMONSTRATED = "NOT_DEMONSTRATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class EvidenceReference(BaseModel):
    section: str | None = None
    context: str
    matched_text: str | None = None


class SkillMatchDetail(BaseModel):
    skill: str
    status: MatchStatus
    evidence: list[EvidenceReference] = Field(default_factory=list)
    reason: str


class ExperienceMatchDetail(BaseModel):
    required_minimum_years: float | None = None
    required_maximum_years: float | None = None
    demonstrated_minimum_years: float | None = None
    demonstrated_maximum_years: float | None = None
    status: MatchStatus
    score: float
    evidence: list[EvidenceReference] = Field(default_factory=list)
    reason: str


class EducationMatchDetail(BaseModel):
    required_degree: str | None = None
    required_field: str | None = None
    demonstrated_degree: str | None = None
    demonstrated_field: str | None = None
    status: MatchStatus
    score: float
    evidence: list[EvidenceReference] = Field(default_factory=list)
    reason: str


class MatchComponent(BaseModel):
    status: MatchStatus
    score: float | None = None
    base_weight: float
    effective_weight: float = 0.0
    contribution: float = 0.0
    evidence_coverage: float = 0.0
    matched_count: int = 0
    total_count: int = 0
    explanation: list[str] = Field(default_factory=list)


class MatchResult(BaseModel):
    overall_score: float
    evidence_coverage: float
    components: dict[str, MatchComponent]
    matched_required_skills: list[str] = Field(default_factory=list)
    missing_required_skills: list[str] = Field(default_factory=list)
    matched_preferred_skills: list[str] = Field(default_factory=list)
    missing_preferred_skills: list[str] = Field(default_factory=list)
    required_skill_details: list[SkillMatchDetail] = Field(default_factory=list)
    preferred_skill_details: list[SkillMatchDetail] = Field(default_factory=list)
    experience_details: list[ExperienceMatchDetail] = Field(default_factory=list)
    education_details: list[EducationMatchDetail] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    explanation: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "This score measures alignment demonstrated in the supplied documents. "
        "It is not an employment decision or proof of a candidate's capabilities."
    )
