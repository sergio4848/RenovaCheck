# Adapted from careos/apps/backend/src/careos/worker/runner.py — Copyright (c) 2026 Sergen Şahin.
"""Batch worker: consumes JSON jobs from a Redis list.

Jobs are ``{"type": "<name>", ...}``. Handlers are registered per type; unknown types are
logged and dropped so a bad message cannot wedge the queue. The loop stops cleanly on
SIGTERM/SIGINT after the job in progress, and touches a heartbeat file that the container
healthcheck reads.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import signal
import time
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import Any

from redis.asyncio import Redis

from renova_extract.core.config import Settings, get_settings
from renova_extract.core.logging import configure_logging, get_logger

log = get_logger("renova_extract.worker")

HEARTBEAT_FILE = Path(
    os.environ.get("RENOVA_WORKER_HEARTBEAT_FILE", "/tmp/renova-worker-heartbeat")  # noqa: S108
)

Job = Mapping[str, Any]
Handler = Callable[[Job], Awaitable[None]]


async def _ping(job: Job) -> None:
    log.info("worker.ping", job_id=job.get("id"))


HANDLERS: dict[str, Handler] = {"ping": _ping}


def touch_heartbeat(path: Path | None = None) -> None:
    with contextlib.suppress(OSError):
        (path or HEARTBEAT_FILE).write_text(str(int(time.time())))


def decode_job(raw: bytes | str) -> Job | None:
    try:
        job = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(job, dict) or not isinstance(job.get("type"), str):
        return None
    return job


async def process_one(job: Job, handlers: Mapping[str, Handler] = HANDLERS) -> bool:
    handler = handlers.get(str(job["type"]))
    if handler is None:
        log.warning("worker.unknown_job_type", job_type=job["type"])
        return False
    await handler(job)
    return True


def queue_client(settings: Settings) -> Redis:
    # The socket must outlive a blocking BLPOP; redis-py's default socket timeout (5 s) would
    # otherwise abort every idle poll with TimeoutError.
    return Redis.from_url(settings.redis_url, socket_timeout=settings.worker_poll_timeout_seconds + 10)


async def run(settings: Settings, stop: asyncio.Event, redis: Redis | None = None) -> None:
    client = redis or queue_client(settings)
    backoff = 1.0
    log.info("worker.started", queue=settings.extract_queue)
    try:
        while not stop.is_set():
            touch_heartbeat()
            try:
                item = await client.blpop([settings.extract_queue], timeout=settings.worker_poll_timeout_seconds)
                backoff = 1.0
            except Exception as exc:
                log.warning("worker.queue_unavailable", error=type(exc).__name__)
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(stop.wait(), timeout=backoff)
                backoff = min(backoff * 2, 30.0)
                continue
            if item is None:
                continue
            job = decode_job(item[1])
            if job is None:
                log.warning("worker.malformed_job")
                continue
            try:
                await process_one(job)
            except Exception:
                log.exception("worker.job_failed", job_type=job["type"])
    finally:
        if redis is None:
            await client.aclose()
        log.info("worker.stopped")


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.json_logs)
    stop = asyncio.Event()

    async def _runner() -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stop.set)
        await run(settings, stop)

    asyncio.run(_runner())
