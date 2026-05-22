"""Application configuration, loaded from environment variables."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql://voltedge:voltedge@localhost:5432/voltedge"
    run_migrations_on_startup: bool = True
    seed_on_startup: bool = True


settings = Settings()
