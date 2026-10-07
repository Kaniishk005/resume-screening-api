from pydantic import BaseModel
from app.enums.candidate_status import CandidateStatus

class StatusResponse(BaseModel):
    message: str
    candidate_name: str
    status: CandidateStatus