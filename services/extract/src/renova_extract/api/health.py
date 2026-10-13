# Adapted from careos/apps/backend/src/careos/api/health.py — Copyright (c) 2026 Sergen Şahin.
"""Liveness and readiness endpoints.

* ``/health`` — liveness: the process runs and can serve HTTP. Never touches dependencies,
  so a Redis or object-storage outage does not make an orchestrator restart healthy processes.
* ``/ready`` — can this instance process documents? Requires Redis (job queue) and the
  object store (document source) to answer within the dependency timeout.
"""

from __future__ import annotations

import asyncio
from typing import Literal

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from redis.asyncio import Redis

from renova_extract.core.config import Settings
from renova_extract.core.logging import get_logger

router = APIRouter(tags=["health"])
log = get_logger(__name__)

DependencyState = Literal["ok", "unavailable"]


class HealthStatus(BaseModel):
    status: Literal["ok"]


class ReadinessStatus(BaseModel):
    status: Literal["ready", "not_ready"]
    redis: DependencyState
    object_storage: DependencyState
    ocr_provider: str
    llm_provider: str


@router.get("/health", response_model=HealthStatus)
async def health() -> HealthStatus:
    return HealthStatus(status="ok")


async def check_redis(settings: Settings) -> DependencyState:
    client: Redis = Redis.from_url(settings.redis_url, socket_timeout=settings.dependency_timeout_seconds)
    try:
        await asyncio.wait_for(client.ping(), timeout=settings.dependency_timeout_seconds)
        return "ok"
    except Exception as exc:
        log.warning("ready.redis_unavailable", error=type(exc).__name__)
        return "unavailable"
    finally:
        await client.aclose()


async def check_object_storage(settings: Settings) -> DependencyState:
    url = f"{settings.s3_endpoint.rstrip('/')}/minio/health/live"
    try:
        async with httpx.AsyncClient(timeout=settings.dependency_timeout_seconds) as client:
            response = await client.get(url)
        return "ok" if response.status_code == 200 else "unavailable"
    except httpx.HTTPError as exc:
        log.warning("ready.object_storage_unavailable", error=type(exc).__name__)
        return "unavailable"


@router.get("/ready", response_model=ReadinessStatus)
async def ready(request: Request) -> JSONResponse:
    settings: Settings = request.app.state.settings
    redis_state, storage_state = await asyncio.gather(check_redis(settings), check_object_storage(settings))
    is_ready = redis_state == "ok" and storage_state == "ok"
    body = ReadinessStatus(
        status="ready" if is_ready else "not_ready",
        redis=redis_state,
        object_storage=storage_state,
        ocr_provider=settings.ocr_provider,
        llm_provider=settings.llm_provider,
    )
    return JSONResponse(status_code=200 if is_ready else 503, content=body.model_dump())
