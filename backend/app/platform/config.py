"""Application configuration, loaded from environment variables."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: str = "development"
    log_level: str = "INFO"
    # MongoDB connection. Local default is the docker/dev mongo container; in the
    # cloud this is a MongoDB Atlas SRV string (mongodb+srv://...), supplied via
    # .env or a deployment secret — never committed.
    mongo_url: str = "mongodb://localhost:27017"
    mongo_db: str = "voltedge"


settings = Settings()
