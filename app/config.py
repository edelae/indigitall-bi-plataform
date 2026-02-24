"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Flask / Dash
    FLASK_SECRET_KEY: str = "dev-secret-change-in-production"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/postgres"

    # Supabase
    SUPABASE_URL: str = "http://localhost:8000"

    # Anthropic AI
    ANTHROPIC_API_KEY: str = ""

    # Sentry
    SENTRY_DSN: str = ""

    # Default tenant for dev mode (no JWT)
    DEFAULT_TENANT: str = "visionamos"

    # Auth mode: "dev" (no auth, query-param tenant) or "jwt" (indigitall JWT)
    AUTH_MODE: str = "dev"

    # JWT settings (used when AUTH_MODE=jwt)
    JWT_SECRET_KEY: str = "change-me-jwt-secret"
    JWT_COOKIE_NAME: str = "indigitall_token"

    @property
    def has_ai_key(self) -> bool:
        return bool(self.ANTHROPIC_API_KEY) and self.ANTHROPIC_API_KEY != "sk-ant-your-key-here"


settings = Settings()
