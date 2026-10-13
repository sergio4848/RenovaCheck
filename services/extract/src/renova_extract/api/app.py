"""ASGI application factory for the extraction service."""

from __future__ import annotations

from fastapi import FastAPI

from renova_extract import __version__
from renova_extract.api.documents import router as documents_router
from renova_extract.api.exception_handlers import register_exception_handlers
from renova_extract.api.health import router as health_router
from renova_extract.api.middleware import (
    BodySizeLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from renova_extract.core.config import Settings, get_settings
from renova_extract.core.logging import configure_logging
from renova_extract.documents.analyze import Analyzer
from renova_extract.documents.storage import ObjectStore, S3ObjectStore


def create_app(settings: Settings | None = None, store: ObjectStore | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.json_logs)

    is_production = settings.environment == "production"
    app = FastAPI(
        title="RenovaCheck extract",
        version=__version__,
        docs_url=None if is_production else "/docs",
        redoc_url=None,
        openapi_url=None if is_production else "/openapi.json",
    )
    app.state.settings = settings
    app.state.analyzer = Analyzer.build(settings, store or S3ObjectStore(settings))

    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(documents_router)

    # Starlette applies middleware in reverse order of registration: request context is outermost.
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_body_bytes)
    app.add_middleware(SecurityHeadersMiddleware, hsts=is_production)
    app.add_middleware(RequestContextMiddleware)
    return app
