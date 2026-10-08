"""Schemas for privacy-reduced, grounded resume feedback."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


BoundedText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
]


class GroundedFact(BaseModel):
    fact_id: str
    category: str
    fact: str
    section: str | None = None
    evidence: list[str] = Field(default_factory=list, max_length=2)


class GroundedFeedbackContext(BaseModel):
    grounding_version: str = "1.0"
    job_title: str | None = None
    overall_score: float
    evidence_coverage: float
    required_skills_demonstrated: list[str] = Field(default_factory=list)
    required_skills_not_demonstrated: list[str] = Field(default_factory=list)
    preferred_skills_demonstrated: list[str] = Field(default_factory=list)
    preferred_skills_not_demonstrated: list[str] = Field(default_factory=list)
    experience_results: list[str] = Field(default_factory=list)
    education_results: list[str] = Field(default_factory=list)
    role_relevance_result: str
    deterministic_strengths: list[str] = Field(default_factory=list)
    deterministic_gaps: list[str] = Field(default_factory=list)
    facts: list[GroundedFact] = Field(default_factory=list)


class GroundedFeedbackItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: BoundedText
    fact_ids: list[str] = Field(default_factory=list, max_length=5)


class GroundedAIResponse(BaseModel):
    """Strict provider-only response. Numeric or decision fields are forbidden."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=1000)
    strengths: list[GroundedFeedbackItem] = Field(default_factory=list, max_length=5)
    weaknesses: list[GroundedFeedbackItem] = Field(default_factory=list, max_length=5)
    recommendation: str = Field(min_length=1, max_length=1000)
    limitations: list[BoundedText] = Field(default_factory=list, max_length=5)


FeedbackSource = Literal["groq", "deterministic_fallback", "legacy"]
FeedbackStatus = Literal["generated", "unavailable"]
