from typing import List

from pydantic import BaseModel


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
