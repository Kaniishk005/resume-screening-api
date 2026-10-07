from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Resume Screening API"
    VERSION: str = "1.0.0"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    GROQ_API_KEY: str | None = None
    GROQ_TIMEOUT_SECONDS: float = 20.0
    DATABASE_URL: str = "sqlite:///resume.db"
    MAX_UPLOAD_SIZE_BYTES: int = 5 * 1024 * 1024

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
