from fastapi import FastAPI

from app.api.analysis import router as analysis_router
from app.api.auth import router as auth_router
from app.api.jobs import router as jobs_router
from app.api.resume import router as resume_router
from app.core.config import settings
from app.db.database import Base, engine
from app.models import User
from app.models.analysis import Analysis

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
)

app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(resume_router)
app.include_router(analysis_router)


@app.get("/")
def home():
    return {"message": "Resume Screening API is running!"}
