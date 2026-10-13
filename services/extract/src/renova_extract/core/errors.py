# Adapted from careos/apps/backend/src/careos/core/errors.py — Copyright (c) 2026 Sergen Şahin.
"""Domain error hierarchy, mapped to HTTP responses in ``renova_extract.api.exception_handlers``.

Messages are returned to callers and logged, so they must never contain document content
or personal data.
"""

from __future__ import annotations

from typing import Any


class RenovaError(Exception):
    status_code: int = 500
    code: str = "internal_error"
    default_message: str = "An internal error occurred."

    def __init__(self, message: str | None = None, *, details: dict[str, Any] | None = None):
        self.message = message or self.default_message
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationRequiredError(RenovaError):
    status_code = 401
    code = "authentication_required"
    default_message = "Authentication is required."


class NotFoundError(RenovaError):
    status_code = 404
    code = "not_found"
    default_message = "Resource not found."


class ValidationFailedError(RenovaError):
    status_code = 422
    code = "validation_failed"
    default_message = "The request could not be validated."


class UnsupportedDocumentError(RenovaError):
    status_code = 422
    code = "unsupported_document"
    default_message = "The document type or content is not supported."


class DependencyUnavailableError(RenovaError):
    status_code = 503
    code = "dependency_unavailable"
    default_message = "A required dependency is unavailable."


class RateLimitedError(RenovaError):
    status_code = 429
    code = "rate_limited"
    default_message = "Too many requests. Please retry later."

    def __init__(self, retry_after_seconds: int, message: str | None = None):
        super().__init__(message, details={"retry_after_seconds": retry_after_seconds})
        self.retry_after_seconds = retry_after_seconds
