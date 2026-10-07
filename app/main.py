from fastapi import FastAPI
from app.api.analysis import router as analysis_router
from app.api.auth import router as auth_router
from app.api.jobs import router as jobs_router
from app.api.resume import router as resume_router
from app.api.intelligence import router as intelligence_router
from app.api.matching import router as matching_router
from app.core.config import settings
from app.db.database import Base, engine
from app.db.migrations import upgrade_database
from app.models import User
from app.models.analysis import Analysis


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
)

upgrade_database()
Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(resume_router)
app.include_router(analysis_router)
app.include_router(intelligence_router)
app.include_router(matching_router)


@app.get("/")
def home():
    return {"message": "Resume Screening API is running!"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
