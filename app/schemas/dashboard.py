from pydantic import BaseModel

class DashboardResponse(BaseModel):
    job_title: str
    total_resumes: int
    highest_ats: int
    lowest_ats: int
    average_ats: float
    qualified: int
    rejected: int