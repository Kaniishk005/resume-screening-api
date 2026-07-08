from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.models.job import Job
from app.models.user import User
from app.schemas.job import JobCreate, JobResponse

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    job: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    new_job = Job(
        title=job.title,
        company=job.company,
        description=job.description,
        required_skills=job.required_skills,
        experience=job.experience,
        location=job.location,
        owner_id=current_user.id,
    )

    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    return new_job


@router.get("/", response_model=list[JobResponse])
def get_jobs(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):

    jobs = db.scalars(select(Job).where(Job.owner_id == current_user.id)).all()

    return jobs


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    job = db.scalar(
        select(Job).where(Job.id == job_id, Job.owner_id == current_user.id)
    )

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@router.delete("/{job_id}")
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    job = db.scalar(
        select(Job).where(Job.id == job_id, Job.owner_id == current_user.id)
    )

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    db.delete(job)
    db.commit()

    return {"message": "Job deleted successfully"}


@router.get("/", response_model=list[JobResponse])
def get_jobs(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    jobs = db.scalars(
        select(Job)
        .where(Job.owner_id == current_user.id)
        .order_by(Job.created_at.desc())
    ).all()

    return jobs


@router.delete("/{job_id}")
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.scalar(
        select(Job).where(Job.id == job_id, Job.owner_id == current_user.id)
    )
    raise HTTPException(status_code=404, detail="Job not found.")
    db.delete(job)
    db.commit()

    return {"message": "Job deleted successfully."}
