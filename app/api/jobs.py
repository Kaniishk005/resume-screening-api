from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.constants import SHORTLIST_THRESHOLD
from app.enums.candidate_status import CandidateStatus
from app.core.security import get_current_user
from app.db.database import get_db
from app.models.analysis import Analysis
from app.models.job import Job
from app.models.user import User
from app.schemas.dashboard import DashboardResponse
from app.schemas.job import JobCreate, JobResponse
from app.schemas.leaderboard import (
    LeaderboardCandidate,
    LeaderboardResponse
)
from typing import Optional

router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"]
)


# Create Job
@router.post(
    "/",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED
)
def create_job(
    job: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    new_job = Job(
        title=job.title,
        company=job.company,
        description=job.description,
        required_skills=job.required_skills,
        experience=job.experience,
        location=job.location,
        owner_id=current_user.id
    )

    try:
        db.add(new_job)
        db.commit()
        db.refresh(new_job)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to create job.") from exc

    return new_job


# Get All Jobs
@router.get(
    "/",
    response_model=list[JobResponse]
)
def get_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    jobs = db.scalars(
        select(Job)
        .where(Job.owner_id == current_user.id)
        .order_by(Job.created_at.desc())
    ).all()

    return jobs


# Get Single Job
@router.get(
    "/{job_id}",
    response_model=JobResponse
)
def get_job(
    job_id: int,
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

    return job


# Dashboard
@router.get(
    "/{job_id}/dashboard",
    response_model=DashboardResponse
)
def job_dashboard(
    job_id: int,
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

    total = db.scalar(
        select(func.count())
        .select_from(Analysis)
        .where(Analysis.job_id == job.id)
    ) or 0

    highest = db.scalar(
        select(func.max(Analysis.ats_score))
        .where(Analysis.job_id == job.id)
    ) or 0

    lowest = db.scalar(
        select(func.min(Analysis.ats_score))
        .where(Analysis.job_id == job.id)
    ) or 0

    average = db.scalar(
        select(func.avg(Analysis.ats_score))
        .where(Analysis.job_id == job.id)
    ) or 0

    qualified = db.scalar(
        select(func.count())
        .select_from(Analysis)
        .where(
            Analysis.job_id == job.id,
            Analysis.ats_score >= SHORTLIST_THRESHOLD
        )
    ) or 0

    rejected = total - qualified

    return {
        "job_title": job.title,
        "total_resumes": total,
        "highest_ats": highest,
        "lowest_ats": lowest,
        "average_ats": round(average, 2),
        "qualified": qualified,
        "rejected": rejected
    }


# Leaderboard
@router.get(
    "/{job_id}/leaderboard",
    response_model=LeaderboardResponse
)
def get_leaderboard(
    job_id: int,

    candidate: Optional[str] = None,

    status: Optional[CandidateStatus] = None,

    min_score: Optional[int] = None,

    max_score: Optional[int] = None,

    page: int = 1,

    page_size: int = 10,

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

    analyses = db.scalars(
        select(Analysis)
        .where(
            Analysis.job_id == job.id
        )
        .order_by(
            Analysis.ats_score.desc(),
            Analysis.match_percentage.desc()
        )
    ).all()

    leaderboard = []

    for rank, analysis in enumerate(analyses, start=1):

        leaderboard.append(
            LeaderboardCandidate(
                rank=rank,
                candidate_name=analysis.candidate_name,
                ats_score=analysis.ats_score,
                status=analysis.status,
                match_percentage=analysis.match_percentage
            )
        )

    return LeaderboardResponse(
        job_title=job.title,
        total_candidates=len(leaderboard),
        leaderboard=leaderboard
    )


# Delete Job
@router.delete("/{job_id}")
def delete_job(
    job_id: int,
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

    try:
        db.delete(job)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to delete job.") from exc

    return {
        "message": "Job deleted successfully."
    }
