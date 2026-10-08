import json
import os
import shutil
import tempfile
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.db.database import get_db
from app.models.analysis import Analysis
from app.models.job import Job
from app.models.user import User
from app.services.ai import AIServiceError, generate_feedback
from app.services.parser import ResumeParsingError, extract_text_from_pdf
from app.services.uploads import UploadValidationError, temporary_pdf
from app.schemas.analysis import (
    AnalysisResponse,
    BulkAnalysisResponse
)
from app.services.zip_processor import extract_zip
from app.enums.candidate_status import CandidateStatus
from app.schemas.status import StatusUpdate
from app.services.status_service import is_valid_transition
from app.schemas.status_response import StatusResponse
from app.schemas.matching import MatchResult
from app.services.job_parser import parse_stored_job
from app.services.matching import evaluate_match
from app.services.resume_intelligence import build_resume_profile
from app.services.feedback_context import build_feedback_context, deterministic_feedback

router = APIRouter(prefix="/analysis", tags=["Analysis"])

def process_resume_file(
    file_path: str,
    job: Job,
    db: Session,
    current_user: User
):
    resume_text = extract_text_from_pdf(file_path)
    resume_profile = build_resume_profile(resume_text)
    job_profile = parse_stored_job(
        title=job.title,
        description=job.description,
        required_skills=job.required_skills,
        experience=job.experience,
    )
    match_result = evaluate_match(resume_profile, job_profile)
    ats_score = int(round(match_result.overall_score))
    required_component = match_result.components["required_skills"]
    match_percentage = required_component.score or 0.0
    status = CandidateStatus.NEW

    feedback_context = build_feedback_context(
        resume_profile,
        job_profile,
        match_result,
    )
    try:
        feedback = generate_feedback(feedback_context)
    except AIServiceError:
        feedback = deterministic_feedback(match_result)

    analysis = Analysis(
        candidate_name=resume_profile.candidate_name,
        ats_score=ats_score,
        status = status,
        match_percentage=match_percentage,
        matched_skills=json.dumps(match_result.matched_required_skills),
        missing_skills=json.dumps(match_result.missing_required_skills),
        ai_feedback=json.dumps(feedback),
        match_breakdown=match_result.model_dump_json(),
        job_id=job.id,
        recruiter_id=current_user.id
    )

    try:
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to save analysis.") from exc

    return {
        "analysis_id": analysis.id,
        "candidate_name": resume_profile.candidate_name,
        "ats_score": ats_score,
        "status": status,
        "match_percentage": match_percentage,
        "matched_skills": match_result.matched_required_skills,
        "missing_skills": match_result.missing_required_skills,
        "ai_feedback": feedback,
        "match_breakdown": match_result,
    }


def process_resume(
    file: UploadFile,
    job: Job,
    db: Session,
    current_user: User
):
    with temporary_pdf(file) as path:
        return process_resume_file(
            path,
            job,
            db,
            current_user
        )


@router.post("/{job_id}", response_model=AnalysisResponse)
def analyze_resume(
    job_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    job = db.scalar(
        select(Job).where(Job.id == job_id, Job.owner_id == current_user.id)
    )

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    try:
        return process_resume(
            file=file,
            job=job,
            db=db,
            current_user=current_user
        )
    except UploadValidationError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except ResumeParsingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/history", response_model=list[AnalysisResponse])
def get_analysis_history(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    analyses = db.scalars(
        select(Analysis)
        .where(Analysis.recruiter_id == current_user.id)
        .order_by(Analysis.created_at.desc())
    ).all()
    history = []

    for analysis in analyses:

        history.append(
            {
                "analysis_id": analysis.id,
                "candidate_name": analysis.candidate_name,
                "ats_score": analysis.ats_score,
                "status": analysis.status,
                "match_percentage": analysis.match_percentage,
                "matched_skills": json.loads(analysis.matched_skills),
                "missing_skills": json.loads(analysis.missing_skills),
                "ai_feedback": json.loads(analysis.ai_feedback),
                "match_breakdown": (
                    MatchResult.model_validate_json(analysis.match_breakdown)
                    if analysis.match_breakdown
                    else None
                ),
            }
        )

    return history

@router.patch(
        "/{analysis_id}/status",
        response_model=StatusResponse
)
def update_candidate_status(
    analysis_id: int,
    status_update: StatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    analysis = db.scalar(
        select(Analysis).where(
            Analysis.id == analysis_id,
            Analysis.recruiter_id == current_user.id
        )
    )

    if analysis is None:
        raise HTTPException(
            status_code=404,
            detail="Candidate not found."
        )
    if not is_valid_transition(
        analysis.status,
        status_update.status
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid status transition."
        )
    analysis.status = status_update.status
    try:
        db.commit()
        db.refresh(analysis)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to update candidate status.") from exc
    return {
        "message": "Candidate status updated successfully.",
        "candidate_name": analysis.candidate_name,
        "status": analysis.status
    }

@router.post(
    "/{job_id}/bulk",
    response_model=BulkAnalysisResponse
)
def analyze_bulk_resumes(
    job_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = db.scalar(
        select(Job).where(
            Job.id == job_id,
            Job.owner_id == current_user.id
        )
    )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found."
        )
    results = []
    successful = 0
    failed = 0
    for file in files:

        try:

            result = process_resume(
                file=file,
                job=job,
                db=db,
                current_user=current_user
            )

            results.append(result)

            successful += 1

        except (UploadValidationError, ResumeParsingError, HTTPException):
            db.rollback()
            failed += 1

    return {
        "total_processed": len(files),
        "successful": successful,
        "failed": failed,
        "results": results
    }

@router.post("/{job_id}/zip")
def analyze_zip(
    job_id: int,
    zip_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = db.scalar(
        select(Job).where(
            Job.id == job_id,
            Job.owner_id == current_user.id
        )
    )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found."
        )
    if not (zip_file.filename or "").lower().endswith(".zip"):
        raise HTTPException(status_code=415, detail="Only ZIP archives are supported here.")

    results = []
    successful = 0
    failed = 0
    zip_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_zip:
            zip_path = temp_zip.name
            shutil.copyfileobj(zip_file.file, temp_zip)
        with tempfile.TemporaryDirectory() as extract_folder:
            pdf_files = extract_zip(zip_path, extract_folder)
            for pdf in pdf_files:
                try:
                    result = process_resume_file(pdf, job, db, current_user)
                    results.append(result)
                    successful += 1
                except (ResumeParsingError, HTTPException):
                    db.rollback()
                    failed += 1
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail="Invalid ZIP archive.") from exc
    finally:
        zip_file.file.close()
        if zip_path and os.path.exists(zip_path):
            os.remove(zip_path)
    results.sort(
        key=lambda x: x["ats_score"],
        reverse=True
    )
    for i, candidate in enumerate(results, start=1):
        candidate["rank"] = i
    return {
        "total_processed": successful + failed,
        "successful": successful,
        "failed": failed,
        "results": results
    }
