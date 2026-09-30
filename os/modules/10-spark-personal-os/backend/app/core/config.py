from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central runtime configuration for Spark Personal OS.

    DEMO_MODE=true (the default) means:
      - SQLite is used instead of Postgres
      - No external LLM API key is required (MockProvider is used)
      - Seed data represents fictional demo cases only, clearly labeled
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Spark Personal OS"
    DEMO_MODE: bool = True

    DATABASE_URL: str = "sqlite:///./spark.db"

    JWT_SECRET_KEY: str = "dev-secret-change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 12

    LLM_PROVIDER: str = "mock"  # mock | openai | anthropic | groq
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]


settings = Settings()
