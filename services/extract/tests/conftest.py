from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from renova_extract.api.app import create_app
from renova_extract.core.config import Settings

# Settings the image or the compose file provide; tests must not depend on them.
_HERMETIC_KEEP = {"RENOVA_RULES_DIR"}


@pytest.fixture(autouse=True)
def _hermetic_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(os.environ):
        if name.startswith("RENOVA_") and name not in _HERMETIC_KEEP:
            monkeypatch.delenv(name)


def make_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "environment": "test",
        "json_logs": False,
        "redis_url": "redis://127.0.0.1:1/0",
        "s3_endpoint": "http://127.0.0.1:1",
        "dependency_timeout_seconds": 0.2,
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client
