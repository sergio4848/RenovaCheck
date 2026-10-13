"""Azure AI Document Intelligence (prebuilt-read) over REST.

The page image is sent to the configured endpoint (Poland Central keeps documents in the EU);
the service answers 202 with an operation URL that is polled until the result is ready.
"""

from __future__ import annotations

import io
import time
from typing import Any
from urllib.parse import urlsplit

import httpx
from PIL import Image

from renova_extract.documents.models import Word
from renova_extract.ocr.base import OcrUnavailableError

API_VERSION = "2024-11-30"
POLL_INTERVAL_SECONDS = 1.0


class AzureDocumentIntelligence:
    name = "azure"

    def __init__(
        self,
        endpoint: str,
        key: str,
        timeout_seconds: float = 60.0,
        client: httpx.Client | None = None,
        poll_interval_seconds: float = POLL_INTERVAL_SECONDS,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.key = key
        self.timeout_seconds = timeout_seconds
        self.client = client or httpx.Client(timeout=timeout_seconds, follow_redirects=False)
        self.poll_interval_seconds = poll_interval_seconds

    def recognize(self, image: Image.Image) -> list[Word]:
        buffer = io.BytesIO()
        image.save(buffer, "PNG")
        url = f"{self.endpoint}/documentintelligence/documentModels/prebuilt-read:analyze?api-version={API_VERSION}"
        headers = {"Ocp-Apim-Subscription-Key": self.key}
        try:
            started = self.client.post(url, content=buffer.getvalue(), headers={**headers, "Content-Type": "image/png"})
            if started.status_code != 202:
                raise OcrUnavailableError(f"azure analyze returned {started.status_code}")
            operation = started.headers.get("Operation-Location", "")
            # The result is fetched with the key: never send it to another host than the endpoint.
            if urlsplit(operation).netloc != urlsplit(self.endpoint).netloc:
                raise OcrUnavailableError("azure returned an operation URL on another host")
            deadline = time.monotonic() + self.timeout_seconds
            while True:
                result = self.client.get(operation, headers=headers)
                result.raise_for_status()
                body = result.json()
                status = body.get("status")
                if status == "succeeded":
                    return parse_result(body)
                if status == "failed" or time.monotonic() > deadline:
                    raise OcrUnavailableError(f"azure analysis {status or 'timed out'}")
                time.sleep(self.poll_interval_seconds)
        except (httpx.HTTPError, ValueError) as exc:
            raise OcrUnavailableError(f"azure request failed: {type(exc).__name__}") from exc


def parse_result(body: dict[str, Any]) -> list[Word]:
    pages = body.get("analyzeResult", {}).get("pages", [])
    if not pages:
        return []
    page = pages[0]
    width, height = float(page["width"]), float(page["height"])
    words: list[Word] = []
    for item in page.get("words", []):
        text = str(item.get("content", "")).strip()
        polygon = item.get("polygon") or []
        if not text or len(polygon) < 8:
            continue
        xs, ys = polygon[0::2], polygon[1::2]
        words.append(
            Word(
                text=text,
                x0=max(0.0, min(xs) / width),
                y0=max(0.0, min(ys) / height),
                x1=min(1.0, max(xs) / width),
                y1=min(1.0, max(ys) / height),
                confidence=float(item.get("confidence", 1.0)),
            )
        )
    return words
