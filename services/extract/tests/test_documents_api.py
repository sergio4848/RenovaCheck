from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from renova_extract.api import documents as documents_api
from renova_extract.api.app import create_app
from renova_extract.documents.storage import MemoryObjectStore
from tests.conftest import make_settings

FIXTURES = Path(__file__).parent / "fixtures"
TOKEN = "test-token-0123456789"
ORG, CASE, DOC = (str(uuid.uuid4()) for _ in range(3))
PREFIX = f"org/{ORG}/cases/{CASE}/documents/{DOC}/"
URL = f"http://minio:9000/renova-documents/{PREFIX}original.pdf?X-Amz-Signature=abc"


@pytest.fixture
def store() -> MemoryObjectStore:
    return MemoryObjectStore()


@pytest.fixture
def api(store: MemoryObjectStore, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    settings = make_settings(internal_token=TOKEN, s3_endpoint="http://minio:9000")
    payload = {"bytes": (FIXTURES / "faktura_clean.pdf").read_bytes()}
    monkeypatch.setattr(documents_api, "download", lambda url, settings: payload["bytes"])
    with TestClient(create_app(settings, store=store)) as client:
        client.payload = payload  # type: ignore[attr-defined]
        yield client


def _post(api: TestClient, token: str | None = TOKEN, **overrides: str) -> object:
    body = {"document_id": DOC, "source_url": URL, "output_prefix": PREFIX, **overrides}
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return api.post("/v1/documents/analyze", json=body, headers=headers)


@pytest.mark.parametrize("token", [None, "wrong-token", TOKEN + "x"])
def test_requires_the_internal_token(api: TestClient, token: str | None) -> None:
    response = _post(api, token)
    assert response.status_code == 401  # type: ignore[attr-defined]


def test_analyzes_classifies_and_stores_page_images(api: TestClient, store: MemoryObjectStore) -> None:
    response = _post(api)
    assert response.status_code == 200  # type: ignore[attr-defined]
    body = response.json()  # type: ignore[attr-defined]
    assert body["mime"] == "application/pdf"
    assert body["page_count"] == 1
    assert body["classification"]["doc_type"] == "faktura"
    assert body["pages"][0]["text_source"] == "text_layer"
    key = body["pages"][0]["image_key"]
    assert key == f"{PREFIX}pages/001.png"
    image, content_type = store.objects[key]
    assert content_type == "image/png" and image.startswith(b"\x89PNG")


@pytest.mark.parametrize(
    "prefix",
    [
        PREFIX + "\n",
        "org/../../etc/",
        f"org/{ORG}/cases/{CASE}/documents/{uuid.uuid4()}/",
        f"other/{ORG}/cases/{CASE}/documents/{DOC}/",
    ],
)
def test_output_prefix_must_belong_to_the_document(api: TestClient, prefix: str) -> None:
    response = _post(api, output_prefix=prefix)
    assert response.status_code == 422  # type: ignore[attr-defined]


def test_unsupported_content_is_rejected_without_echoing_it(api: TestClient) -> None:
    api.payload["bytes"] = b"<script>alert(1)</script>"  # type: ignore[attr-defined]
    response = _post(api)
    assert response.status_code == 422  # type: ignore[attr-defined]
    body = response.json()  # type: ignore[attr-defined]
    assert body["error"]["code"] == "unsupported_document"
    assert "script" not in response.text  # type: ignore[attr-defined]


def test_source_must_live_under_the_output_prefix(api: TestClient) -> None:
    other = f"http://minio:9000/renova-documents/org/{uuid.uuid4()}/cases/{CASE}/documents/{DOC}/original.pdf"
    response = _post(api, source_url=other)
    assert response.status_code == 422  # type: ignore[attr-defined]


def test_busy_service_answers_503_so_the_caller_retries(api: TestClient) -> None:
    analyzer = api.app.state.analyzer  # type: ignore[attr-defined]
    analyzer.slot_timeout_seconds = 0.01
    for _ in range(2):
        analyzer.slots.acquire()
    try:
        response = _post(api)
    finally:
        for _ in range(2):
            analyzer.slots.release()
    assert response.status_code == 503  # type: ignore[attr-defined]
    assert response.json()["error"]["code"] == "dependency_unavailable"  # type: ignore[attr-defined]
