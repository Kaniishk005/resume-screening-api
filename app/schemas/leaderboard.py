from pydantic import BaseModel
from app.enums.candidate_status import CandidateStatus


class LeaderboardCandidate(BaseModel):
    rank: int
    candidate_name: str
    ats_score: int
    status: CandidateStatus
    match_percentage: float


class LeaderboardResponse(BaseModel):
    job_title: str
    total_candidates: int
    leaderboard: list[LeaderboardCandidate]