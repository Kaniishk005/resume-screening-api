from pydantic import BaseModel


class JobCreate(BaseModel):
    title: str
    company: str
    description: str
    required_skills: str
    experience: str
    location: str


class JobResponse(JobCreate):
    id: int
    owner_id: int

    model_config = {"from_attributes": True}
