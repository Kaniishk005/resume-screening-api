from pydantic import BaseModel
from app.enums.candidate_status import CandidateStatus


class StatusUpdate(BaseModel):
    status: CandidateStatus