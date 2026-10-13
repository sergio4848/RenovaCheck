from __future__ import annotations

import asyncio
import json
from pathlib import Path

import fakeredis
import pytest

from renova_extract.worker import runner
from renova_extract.worker.healthcheck import main as healthcheck
from tests.conftest import make_settings


@pytest.mark.parametrize("raw", [b"not json", b"[]", b'{"no_type": 1}', b'{"type": 5}'])
def test_malformed_jobs_are_rejected(raw: bytes) -> None:
    assert runner.decode_job(raw) is None


async def test_unknown_job_type_is_dropped() -> None:
    assert await runner.process_one({"type": "does-not-exist"}) is False


async def test_run_processes_queue_and_stops(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "HEARTBEAT_FILE", tmp_path / "beat")
    seen: list[str] = []

    async def record(job: runner.Job) -> None:
        seen.append(str(job["id"]))
        stop.set()

    monkeypatch.setitem(runner.HANDLERS, "record", record)
    settings = make_settings(worker_poll_timeout_seconds=1)
    redis = fakeredis.FakeAsyncRedis()
    await redis.rpush(settings.extract_queue, b"garbage", json.dumps({"type": "record", "id": "j1"}))
    stop = asyncio.Event()

    await asyncio.wait_for(runner.run(settings, stop, redis=redis), timeout=5)

    assert seen == ["j1"]
    assert (tmp_path / "beat").exists()


def test_healthcheck_follows_heartbeat(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import renova_extract.worker.healthcheck as hc

    beat = tmp_path / "beat"
    monkeypatch.setattr(hc, "HEARTBEAT_FILE", beat)
    assert healthcheck() == 1
    runner.touch_heartbeat(beat)
    assert healthcheck() == 0
