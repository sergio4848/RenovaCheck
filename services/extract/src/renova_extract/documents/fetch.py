"""Downloads a source document from object storage.

Only URLs on the configured S3 endpoint (or an explicit extra host) are fetched, redirects are
not followed and the body is capped, so the endpoint cannot be used to reach other services.
"""

from __future__ import annotations

from urllib.parse import urlsplit

import httpx

from renova_extract.core.config import Settings
from renova_extract.core.errors import RenovaError, ValidationFailedError


class SourceUnavailableError(RenovaError):
    status_code = 502
    code = "source_unavailable"
    default_message = "The source document could not be downloaded."


class SourceTooLargeError(RenovaError):
    status_code = 413
    code = "document_too_large"
    default_message = "The source document exceeds the size limit."


def _host_port(url: str) -> str:
    parts = urlsplit(url)
    port = parts.port or (443 if parts.scheme == "https" else 80)
    return f"{(parts.hostname or '').lower()}:{port}"


def allowed_hosts(settings: Settings) -> set[str]:
    return {_host_port(settings.s3_endpoint), *(h.lower() for h in settings.extra_source_hosts)}


def check_source_url(url: str, settings: Settings) -> None:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
        raise ValidationFailedError("source_url must be a plain http(s) URL.")
    if _host_port(url) not in allowed_hosts(settings):
        raise ValidationFailedError("source_url host is not allowed.")


def download(url: str, settings: Settings, client: httpx.Client | None = None) -> bytes:
    check_source_url(url, settings)
    owned = client is None
    http = client or httpx.Client(timeout=settings.download_timeout_seconds, follow_redirects=False)
    try:
        with http.stream("GET", url) as response:
            if response.status_code != 200:
                raise SourceUnavailableError(details={"status": response.status_code})
            declared = response.headers.get("content-length")
            if declared and declared.isdigit() and int(declared) > settings.max_document_bytes:
                raise SourceTooLargeError(details={"max_bytes": settings.max_document_bytes})
            chunks, received = [], 0
            for chunk in response.iter_bytes():
                received += len(chunk)
                if received > settings.max_document_bytes:
                    raise SourceTooLargeError(details={"max_bytes": settings.max_document_bytes})
                chunks.append(chunk)
            return b"".join(chunks)
    except httpx.HTTPError as exc:
        raise SourceUnavailableError() from exc
    finally:
        if owned:
            http.close()
