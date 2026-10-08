from typing import List
from pydantic import BaseModel, Field
from app.enums.candidate_status import CandidateStatus
from app.schemas.matching import MatchResult
from app.schemas.feedback import FeedbackSource, FeedbackStatus

class AIFeedback(BaseModel):

    summary: str

    strengths: List[str]

    weaknesses: List[str]

    recommendation: str

    evidence_references: dict[str, List[str]] = Field(default_factory=dict)

    limitations: List[str] = Field(default_factory=list)

    feedback_source: FeedbackSource = "legacy"

    feedback_status: FeedbackStatus = "generated"

    grounding_version: str | None = None


class AnalysisResponse(BaseModel):

    analysis_id: int

    candidate_name: str

    ats_score: int

    match_percentage: float

    matched_skills: List[str]

    missing_skills: List[str]

    ai_feedback: AIFeedback

    status: CandidateStatus

    match_breakdown: MatchResult | None = None

class BulkAnalysisResponse(BaseModel):
    total_processed: int
    successful: int
    failed: int
    results: list[AnalysisResponse]
