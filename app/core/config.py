from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(database_url: str) -> str:
    """Return a SQLAlchemy URL that explicitly uses the Psycopg 3 driver."""

    if database_url.startswith("postgres://"):
        return "postgresql+psycopg://" + database_url[len("postgres://") :]
    if database_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + database_url[len("postgresql://") :]
    return database_url


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Resume Screening API"
    VERSION: str = "1.0.0"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_TIMEOUT_SECONDS: float = 20.0
    DATABASE_URL: str = "sqlite:///resume.db"
    MAX_UPLOAD_SIZE_BYTES: int = 5 * 1024 * 1024
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
