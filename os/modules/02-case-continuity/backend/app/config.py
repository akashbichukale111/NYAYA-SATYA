"""
Central configuration for the Case Continuity Engine.

Nothing here hard-codes secrets. Everything is read from environment
variables (see .env.example at the repo root). The frontend never sees
any of these values directly - it only talks to our own API.
"""
import os
from dataclasses import dataclass


def _bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./case_continuity.db")
    upload_dir: str = os.getenv("UPLOAD_DIR", "./uploads")
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "15"))

    llm_provider: str = os.getenv("LLM_PROVIDER", "mock")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "claude-sonnet-4-6")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.anthropic.com")

    app_env: str = os.getenv("APP_ENV", "demo")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    cors_origins: str = os.getenv("CORS_ORIGINS", "*")


settings = Settings()
