# Adapted from careos/apps/backend/src/careos/core/config.py — Copyright (c) 2026 Sergen Şahin.
"""Service settings, read once from ``RENOVA_*`` environment variables.

Secrets are ``SecretStr`` so they never appear in reprs or logs. In production the service
refuses to start with development defaults.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "production"]
OcrProvider = Literal["text_layer", "tesseract", "azure", "google"]
LlmProvider = Literal["off", "fake", "anthropic", "openai"]

_DEV_TOKEN = "dev-internal-token-change-me"  # noqa: S105 - development default, rejected in production
_DEV_S3_SECRET = "renova-extract-secret-dev"  # noqa: S105 - development default, rejected in production


def _default_rules_dir() -> Path:
    # Repository layout: services/extract/src/renova_extract/core/config.py -> packages/rules.
    return Path(__file__).resolve().parents[5] / "packages" / "rules"


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
    s3_access_key: SecretStr = SecretStr("renova-extract")
    s3_secret_key: SecretStr = SecretStr(_DEV_S3_SECRET)

    ocr_provider: OcrProvider = "text_layer"
    llm_provider: LlmProvider = "off"

    # Document analysis limits and inputs.
    max_document_bytes: int = Field(default=25 * 1024 * 1024, ge=1024)
    max_pages: int = Field(default=50, ge=1, le=500)
    download_timeout_seconds: float = Field(default=20.0, gt=0, le=120)
    # Total OCR time per document; keeps a request well under the web job's HTTP timeout.
    ocr_budget_seconds: float = Field(default=120.0, gt=0, le=600)
    # Hosts (host:port) the service may download documents from, besides the S3 endpoint itself.
    extra_source_hosts: tuple[str, ...] = ()
    rules_dir: Path = Field(default_factory=_default_rules_dir)

    dependency_timeout_seconds: float = Field(default=2.0, gt=0, le=30)
    worker_poll_timeout_seconds: int = Field(default=5, ge=1, le=60)

    @model_validator(mode="after")
    def _reject_insecure_production_defaults(self) -> Settings:
        if self.environment != "production":
            return self
        insecure = []
        if self.internal_token.get_secret_value() in ("", _DEV_TOKEN) or len(self.internal_token) < 24:
            insecure.append("RENOVA_INTERNAL_TOKEN")
        if self.s3_secret_key.get_secret_value() in ("", _DEV_S3_SECRET):
            insecure.append("RENOVA_S3_SECRET_KEY")
        if insecure:
            raise ValueError(f"insecure production settings: {', '.join(insecure)}")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
