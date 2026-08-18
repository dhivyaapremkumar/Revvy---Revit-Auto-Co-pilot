"""Application settings.

Reads configuration from environment variables (and a local `.env` file in
development). No secrets are hardcoded here — every sensitive value is
sourced via `pydantic_settings.BaseSettings` from the environment, per
CLAUDE.md.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings.

    Values are read from environment variables first, falling back to a
    `.env` file (see PRPs/revvy-prp.md > ENVIRONMENT VARIABLES for the full
    list expected in production).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- App metadata ---
    APP_NAME: str = "REVVY"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"

    # --- Database (DATABASE-AGENT is the source of truth for the URL shape) ---
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/revvy"

    # --- Auth / JWT ---
    SECRET_KEY: str = Field(
        default="INSECURE-DEV-ONLY-CHANGE-ME",
        description="Must be overridden via env var in any non-local environment.",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- OpenAI / LLM ---
    OPENAI_API_KEY: str = ""
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # --- Email service ---
    EMAIL_SERVICE_API_KEY: str = ""
    EMAIL_FROM_ADDRESS: str = "no-reply@revvy.app"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True

    # --- CORS / frontend ---
    VITE_API_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:5173"
    ALLOWED_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",  # Vite dev server default
            "http://127.0.0.1:5173",
            "http://localhost",  # docker-compose nginx frontend (port 80)
            "http://127.0.0.1",
        ]
    )

    # --- REVVY-specific ---
    REVVY_BACKEND_URL: str = "http://localhost:8000"

    # --- Code-RAG (Tamil Nadu Building Code ingestion + search) ---
    CODE_DOCUMENT_UPLOAD_DIR: str = "uploads/code_documents"
    # Calibrated against the real TNCDBR-2019 PDF (pypdf-extracted text is
    # noisier than clean prose, so absolute cosine similarity runs lower
    # even for correct matches): genuinely irrelevant queries scored
    # ~0.13-0.16, genuinely correct matches scored ~0.48-0.65+. 0.75 was
    # discarding correct answers as "not found" -- 0.4 keeps a wide safety
    # margin above the observed noise floor while no longer rejecting them.
    CODE_RAG_SIMILARITY_THRESHOLD: float = 0.4
    CODE_RAG_TOP_K: int = 5
    CODE_RAG_CHUNK_SIZE_CHARS: int = 1200
    CODE_RAG_CHUNK_OVERLAP_CHARS: int = 150
    CODE_RAG_MAX_UPLOAD_BYTES: int = 20 * 1024 * 1024  # 20 MB
    # Deliberately lower/wider than the Q&A path above: a compliance check
    # embeds a JSON-heavy generated_spec description, not a natural-language
    # question, which structurally scores lower cosine similarity even
    # against the genuinely correct chunk (observed ~0.48 for a clearly
    # on-topic match vs. ~0.27 for an unrelated one on real TNCDBR text) --
    # reusing the Q&A threshold here caused correct compliance checks to
    # fall back to "pending" (unverified) instead of actually running.
    CODE_RAG_COMPLIANCE_SIMILARITY_THRESHOLD: float = 0.35
    CODE_RAG_COMPLIANCE_TOP_K: int = 8


@lru_cache
def get_settings() -> Settings:
    """Return a cached `Settings` instance.

    Cached via `lru_cache` so environment variables are read once per
    process; tests can call `get_settings.cache_clear()` to force a reload.
    """
    return Settings()


settings = get_settings()
