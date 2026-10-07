"""Public schemas for deterministic resume and job-description intelligence."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SkillEvidence(BaseModel):
    canonical_skill: str
    matched_text: str
    section: str | None = None
    context: str | None = None


class ResumeBlock(BaseModel):
    heading: str | None = None
    content: str
    skills: list[str] = Field(default_factory=list)
    section: str | None = None


class ExperienceEvidence(BaseModel):
    minimum_years: float | None = None
    maximum_years: float | None = None
    raw_text: str
    section: str | None = None


class EducationEvidence(BaseModel):
    degree: str | None = None
    field: str | None = None
    raw_text: str
    section: str | None = None


class StructuredResumeProfile(BaseModel):
    filename: str | None = None
    candidate_name: str
    email: str
    phone: str
    skills: list[str] = Field(default_factory=list)
    skill_evidence: list[SkillEvidence] = Field(default_factory=list)
    experience: list[ResumeBlock] = Field(default_factory=list)
    experience_evidence: list[ExperienceEvidence] = Field(default_factory=list)
    projects: list[ResumeBlock] = Field(default_factory=list)
    education: list[ResumeBlock] = Field(default_factory=list)
    education_evidence: list[EducationEvidence] = Field(default_factory=list)
    certifications: list[ResumeBlock] = Field(default_factory=list)
    achievements: list[ResumeBlock] = Field(default_factory=list)
    leadership: list[ResumeBlock] = Field(default_factory=list)
    sections: dict[str, str] = Field(default_factory=dict)
    extracted_text: str


class JobDescriptionRequest(BaseModel):
    description: str | None = None
    job_description: str | None = None
    text: str | None = None
    title: str | None = None


class JobProfile(BaseModel):
    job_title: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    experience_requirements: list[ExperienceEvidence] = Field(default_factory=list)
    education_requirements: list[EducationEvidence] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    qualifications: list[str] = Field(default_factory=list)
    preferred_qualifications: list[str] = Field(default_factory=list)
    domain_keywords: list[str] = Field(default_factory=list)
    sections: dict[str, str] = Field(default_factory=dict)
    raw_description: str

