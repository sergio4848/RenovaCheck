from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from renova_extract.api import health
from renova_extract.api.app import create_app
from tests.conftest import make_settings


def test_health_is_ok_without_dependencies(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_responses_carry_request_id_and_security_headers(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "abc12345-req"})
    assert response.headers["X-Request-ID"] == "abc12345-req"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_ready_reports_unavailable_dependencies_with_503(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["redis"] == "unavailable"
    assert body["object_storage"] == "unavailable"
    assert body["ocr_provider"] == "text_layer"
    assert body["llm_provider"] == "off"


def test_ready_is_ready_when_dependencies_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    async def ok(_: object) -> str:
        return "ok"

    monkeypatch.setattr(health, "check_redis", ok)
    monkeypatch.setattr(health, "check_object_storage", ok)
    with TestClient(create_app(make_settings())) as client:
        response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_unknown_route_uses_error_envelope(client: TestClient) -> None:
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_oversized_body_is_rejected(client: TestClient) -> None:
    response = client.post("/health", content=b"x" * 2_000_000)
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


@pytest.mark.parametrize("path", ["/docs", "/openapi.json"])
def test_docs_disabled_in_production(path: str) -> None:
    app = create_app(make_settings(environment="production", internal_token="x" * 32, s3_secret_key="y" * 32))
    with TestClient(app) as client:
        assert client.get(path).status_code == 404
