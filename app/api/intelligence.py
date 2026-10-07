"""Authenticated endpoints for deterministic Phase 2 intelligence."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.security import get_current_user
from app.models.user import User
from app.schemas.intelligence import JobDescriptionRequest, JobProfile, StructuredResumeProfile
from app.services.job_parser import parse_job_description
from app.services.parser import ResumeParsingError, extract_text_from_pdf
from app.services.resume_intelligence import build_resume_profile
from app.services.uploads import UploadValidationError, temporary_pdf


router = APIRouter(prefix="/intelligence", tags=["Intelligence"])


@router.post("/resume", response_model=StructuredResumeProfile)
def parse_resume_intelligence_endpoint(
    file: UploadFile = File(...), current_user: User = Depends(get_current_user)
) -> StructuredResumeProfile:
    """Parse a PDF into a structured profile without calling Groq."""

    del current_user  # Authentication is intentional; no user data is persisted.
    try:
        with temporary_pdf(file) as file_path:
            text = extract_text_from_pdf(file_path)
            return build_resume_profile(text, filename=file.filename)
    except UploadValidationError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except ResumeParsingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/job-description", response_model=JobProfile)
def parse_job_intelligence_endpoint(
    request: JobDescriptionRequest, current_user: User = Depends(get_current_user)
) -> JobProfile:
    """Parse a job description into deterministic requirements."""

    del current_user
    description = request.description or request.job_description or request.text
    if not description or not description.strip():
        raise HTTPException(status_code=422, detail="A job description is required.")
    return parse_job_description(description, title=request.title)

