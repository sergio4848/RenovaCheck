from __future__ import annotations

import httpx
import pytest

from renova_extract.core.errors import ValidationFailedError
from renova_extract.documents.fetch import SourceTooLargeError, SourceUnavailableError, download
from tests.conftest import make_settings

SETTINGS = make_settings(s3_endpoint="http://minio:9000", max_document_bytes=2048)


def _client(handler: httpx.MockTransport) -> httpx.Client:
    return httpx.Client(transport=handler, follow_redirects=False)


@pytest.mark.parametrize(
    "url",
    [
        "http://169.254.169.254/latest/meta-data/",
        "http://minio:9001/bucket/key",
        "file:///etc/passwd",
        "http://user:pass@minio:9000/bucket/key",
        "gopher://minio:9000/x",
    ],
)
def test_only_the_object_store_can_be_fetched(url: str) -> None:
    with pytest.raises(ValidationFailedError):
        download(url, SETTINGS, _client(httpx.MockTransport(lambda r: httpx.Response(200))))


def test_download_returns_body() -> None:
    client = _client(httpx.MockTransport(lambda r: httpx.Response(200, content=b"%PDF-1.7 ok")))
    assert download("http://minio:9000/renova-documents/a.pdf?X-Amz-Signature=x", SETTINGS, client) == b"%PDF-1.7 ok"


def test_redirects_are_not_followed() -> None:
    client = _client(httpx.MockTransport(lambda r: httpx.Response(302, headers={"location": "http://evil/"})))
    with pytest.raises(SourceUnavailableError):
        download("http://minio:9000/renova-documents/a.pdf", SETTINGS, client)


def test_body_size_is_capped_even_without_content_length() -> None:
    def stream(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=iter([b"x" * 1500, b"y" * 1500]))

    with pytest.raises(SourceTooLargeError):
        download("http://minio:9000/renova-documents/a.pdf", SETTINGS, _client(httpx.MockTransport(stream)))
