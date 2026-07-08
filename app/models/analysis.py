from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Analysis(Base):

    __tablename__ = "analysis"

    id: Mapped[int] = mapped_column(primary_key=True)

    candidate_name: Mapped[str] = mapped_column(String(100))

    ats_score: Mapped[int] = mapped_column(Integer)

    match_percentage: Mapped[float] = mapped_column(Float)

    matched_skills: Mapped[str] = mapped_column(Text)

    missing_skills: Mapped[str] = mapped_column(Text)

    ai_feedback: Mapped[str] = mapped_column(Text)

    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))

    recruiter_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
