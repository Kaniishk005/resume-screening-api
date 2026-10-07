from typing import List
from pydantic import BaseModel
from app.enums.candidate_status import CandidateStatus
from app.schemas.matching import MatchResult

class AIFeedback(BaseModel):

    summary: str

    strengths: List[str]

    weaknesses: List[str]

    recommendation: str


class AnalysisResponse(BaseModel):

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
