from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import normalize_database_url, settings


def engine_options(database_url: str) -> tuple[str, dict[str, object]]:
    """Build a normalized URL and dialect-specific engine options."""

    normalized_url = normalize_database_url(database_url)
    options = {"check_same_thread": False} if normalized_url.startswith("sqlite") else {}
    return normalized_url, options


DATABASE_URL, connect_args = engine_options(settings.DATABASE_URL)
engine = create_engine(DATABASE_URL, connect_args=connect_args)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Base class for all Models
class Base(DeclarativeBase):
    pass


# Dependency for Database Session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
