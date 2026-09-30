"""
Central configuration for Hearing Readiness Engine backend.
All values are overridable via environment variables so the same
codebase runs identically in dev, CI, and (later) production.
"""
from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent  # backend/


class Settings:
    # --- App ---
    APP_NAME: str = "Hearing Readiness Engine"
    ENV: str = os.getenv("HRE_ENV", "development")

    # --- Storage ---
    DATA_DIR: Path = Path(os.getenv("HRE_DATA_DIR", BASE_DIR / "var"))
    DB_PATH: Path = DATA_DIR / "hre.db"
    UPLOAD_DIR: Path = DATA_DIR / "uploads"
    DATABASE_URL: str = os.getenv("HRE_DATABASE_URL", f"sqlite:///{DB_PATH}")

    # --- Uploads / security ---
    MAX_UPLOAD_BYTES: int = int(os.getenv("HRE_MAX_UPLOAD_BYTES", 15 * 1024 * 1024))  # 15MB
    ALLOWED_EXTENSIONS: tuple = (".pdf", ".docx", ".txt", ".json", ".csv")

    # --- LLM provider abstraction ---
    # Never hard-code to a single vendor. DEMO_MODE=1 (default) forces the
    # deterministic MockProvider so the whole product runs with zero API keys.
    LLM_API_KEY: str | None = os.getenv("LLM_API_KEY")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "mock-deterministic-v1")
    LLM_BASE_URL: str | None = os.getenv("LLM_BASE_URL")
    DEMO_MODE: bool = os.getenv("HRE_DEMO_MODE", "1") == "1" or not os.getenv("LLM_API_KEY")

    # --- CORS ---
    CORS_ORIGINS: list = os.getenv("HRE_CORS_ORIGINS", "http://localhost:5173").split(",")


settings = Settings()
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
