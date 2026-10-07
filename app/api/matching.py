"""Authenticated APIs for deterministic Phase 3 document alignment."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.models.job import Job
from app.models.user import User
from app.schemas.matching import MatchResult
from app.services.job_parser import parse_job_description, parse_stored_job
from app.services.matching import evaluate_match
from app.services.parser import ResumeParsingError, extract_text_from_pdf
from app.services.resume_intelligence import build_resume_profile
from app.services.uploads import UploadValidationError, temporary_pdf


router = APIRouter(prefix="/matching", tags=["Matching"])


def _resume_profile(file: UploadFile):
    try:
        with temporary_pdf(file) as file_path:
            return build_resume_profile(
                extract_text_from_pdf(file_path), filename=file.filename
            )
    except UploadValidationError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except ResumeParsingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/evaluate", response_model=MatchResult)
def evaluate_documents(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    job_title: str | None = Form(None),
    current_user: User = Depends(get_current_user),
) -> MatchResult:
    """Evaluate an uploaded resume against supplied job-description text."""

    del current_user
    if not job_description.strip():
        raise HTTPException(status_code=422, detail="A job description is required.")
    return evaluate_match(
        _resume_profile(file),
        parse_job_description(job_description, title=job_title),
    )


@router.post("/jobs/{job_id}", response_model=MatchResult)
def evaluate_existing_job(
    job_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MatchResult:
    """Evaluate a resume against a recruiter-owned existing job."""

    job = db.scalar(
        select(Job).where(Job.id == job_id, Job.owner_id == current_user.id)
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return evaluate_match(
        _resume_profile(file),
        parse_stored_job(
            title=job.title,
            description=job.description,
            required_skills=job.required_skills,
            experience=job.experience,
        ),
    )
