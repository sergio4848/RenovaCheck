# Adapted from careos/apps/backend/src/careos/core/config.py — Copyright (c) 2026 Sergen Şahin.
"""Service settings, read once from ``RENOVA_*`` environment variables.

Secrets are ``SecretStr`` so they never appear in reprs or logs. In production the service
refuses to start with development defaults.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "production"]
OcrProvider = Literal["text_layer", "tesseract", "azure", "google"]
LlmProvider = Literal["off", "fake", "anthropic", "openai"]

_DEV_TOKEN = "dev-internal-token-change-me"  # noqa: S105 - development default, rejected in production
_DEV_S3_SECRET = "renova-minio-secret"  # noqa: S105 - development default, rejected in production


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RENOVA_", extra="ignore", frozen=True)

    environment: Environment = "development"
    log_level: str = "INFO"
    json_logs: bool = True
    max_body_bytes: int = Field(default=1_048_576, ge=1024)

    # Shared secret for calls from the web application (Authorization: Bearer ...).
    internal_token: SecretStr = SecretStr(_DEV_TOKEN)

    redis_url: str = "redis://redis:6379/0"
    extract_queue: str = "renova:extract:jobs"

    s3_endpoint: str = "http://minio:9000"
    s3_bucket: str = "renova-documents"
    s3_access_key: SecretStr = SecretStr("renova")
    s3_secret_key: SecretStr = SecretStr(_DEV_S3_SECRET)

    ocr_provider: OcrProvider = "text_layer"
    llm_provider: LlmProvider = "off"

    dependency_timeout_seconds: float = Field(default=2.0, gt=0, le=30)
    worker_poll_timeout_seconds: int = Field(default=5, ge=1, le=60)

    @model_validator(mode="after")
    def _reject_insecure_production_defaults(self) -> Settings:
        if self.environment != "production":
            return self
        insecure = []
        if self.internal_token.get_secret_value() in ("", _DEV_TOKEN):
            insecure.append("RENOVA_INTERNAL_TOKEN")
        if self.s3_secret_key.get_secret_value() in ("", _DEV_S3_SECRET):
            insecure.append("RENOVA_S3_SECRET_KEY")
        if insecure:
            raise ValueError(f"insecure production settings: {', '.join(insecure)}")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
