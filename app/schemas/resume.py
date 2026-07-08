from typing import List

from pydantic import BaseModel


class ResumeResponse(BaseModel):

    filename: str

    candidate_name: str

    email: str

    phone: str

    skills: List[str]

    extracted_text: str
