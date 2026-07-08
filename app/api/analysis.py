import json
import os
import shutil

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.models.analysis import Analysis
from app.models.job import Job
from app.models.user import User
from app.schemas.analysis import AnalysisResponse
from app.services.ai import generate_feedback
from app.services.ats import calculate_ats_score, calculate_skill_match
from app.services.parser import parse_resume

router = APIRouter(prefix="/analysis", tags=["Analysis"])

UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


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

    path = os.path.join(UPLOAD_FOLDER, file.filename)

    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    parsed = parse_resume(path)
    os.remove(path)

    result = calculate_skill_match(job.required_skills, parsed["skills"])

    ats_score = calculate_ats_score(result["match_percentage"])

    feedback = generate_feedback(
        parsed["extracted_text"],
        result["matched_skills"],
        result["missing_skills"],
        ats_score,
    )
    analysis = Analysis(
        candidate_name=parsed["candidate_name"],
        ats_score=ats_score,
        match_percentage=result["match_percentage"],
        matched_skills=json.dumps(result["matched_skills"]),
        missing_skills=json.dumps(result["missing_skills"]),
        ai_feedback=json.dumps(feedback),
        job_id=job.id,
        recruiter_id=current_user.id,
    )

    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return {
        "candidate_name": parsed["candidate_name"],
        "ats_score": ats_score,
        "match_percentage": result["match_percentage"],
        "matched_skills": result["matched_skills"],
        "missing_skills": result["missing_skills"],
        "ai_feedback": feedback,
    }


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
                "candidate_name": analysis.candidate_name,
                "ats_score": analysis.ats_score,
                "match_percentage": analysis.match_percentage,
                "matched_skills": json.loads(analysis.matched_skills),
                "missing_skills": json.loads(analysis.missing_skills),
                "ai_feedback": json.loads(analysis.ai_feedback),
            }
        )

    return history
