import os


class Settings:
    APP_NAME: str = "Undertrial Liberty Sentinel"
    DEMO_MODE: bool = os.environ.get("DEMO_MODE", "true").lower() == "true"
    LLM_PROVIDER: str = os.environ.get("LLM_PROVIDER", "mock")  # mock | openai | anthropic | groq
    OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
    GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")
    MAX_UPLOAD_BYTES: int = int(os.environ.get("MAX_UPLOAD_BYTES", 15 * 1024 * 1024))  # 15 MB
    ALLOWED_MIME_TYPES = {
        "application/pdf",
        "text/plain",
        "application/json",
        "text/csv",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    ALLOWED_EXTENSIONS = {".pdf", ".txt", ".json", ".csv", ".docx"}
    STALE_CASE_DAYS: int = int(os.environ.get("STALE_CASE_DAYS", 30))
    UPCOMING_DATE_WINDOW_DAYS: int = int(os.environ.get("UPCOMING_DATE_WINDOW_DAYS", 14))
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-only-insecure-key-change-in-prod")


settings = Settings()
