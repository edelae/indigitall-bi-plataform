"""Extraction settings — mirrors app/config.py pattern with pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class ExtractionSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Indigitall API
    INDIGITALL_API_BASE_URL: str = "https://am1.api.indigitall.com"
    INDIGITALL_SERVER_KEY: str = ""
    INDIGITALL_APP_TOKEN: str = ""
    INDIGITALL_EMAIL: str = ""
    INDIGITALL_PASSWORD: str = ""

    # Database (needed by app.models.database)
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/postgres"

    # Extraction limits — keep small for Phase 1 discovery
    EXTRACTION_DAYS_BACK: int = 7
    EXTRACTION_PAGE_LIMIT: int = 1
    EXTRACTION_MAX_RECORDS: int = 100

    # Rate-limiting / resilience
    API_REQUEST_DELAY_SECONDS: float = 0.5
    API_MAX_RETRIES: int = 3
    API_TIMEOUT_SECONDS: int = 30


extraction_settings = ExtractionSettings()
