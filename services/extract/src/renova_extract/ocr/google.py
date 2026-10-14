"""Google Document AI (OCR processor) over REST, synchronous `process` call."""

from __future__ import annotations

import base64
import io
from typing import Any

import httpx
from PIL import Image

from renova_extract.documents.models import Word
from renova_extract.ocr.base import OcrUnavailableError


class GoogleDocumentAI:
    name = "google"

    def __init__(
        self,
        project_id: str,
        location: str,
        processor_id: str,
        access_token: str,
        timeout_seconds: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.url = (
            f"https://{location}-documentai.googleapis.com/v1/projects/{project_id}"
            f"/locations/{location}/processors/{processor_id}:process"
        )
        self.access_token = access_token
        self.client = client or httpx.Client(timeout=timeout_seconds, follow_redirects=False)

    def recognize(self, image: Image.Image) -> list[Word]:
        buffer = io.BytesIO()
        image.save(buffer, "PNG")
        body = {
            "rawDocument": {"content": base64.b64encode(buffer.getvalue()).decode("ascii"), "mimeType": "image/png"},
            "skipHumanReview": True,
        }
        try:
            response = self.client.post(self.url, json=body, headers={"Authorization": f"Bearer {self.access_token}"})
            response.raise_for_status()
            return parse_document(response.json().get("document", {}))
        except (httpx.HTTPError, KeyError, TypeError, ValueError, AttributeError) as exc:
            raise OcrUnavailableError(f"google request failed: {type(exc).__name__}") from exc


def parse_document(document: dict[str, Any]) -> list[Word]:
    text = str(document.get("text", ""))
    pages = document.get("pages", [])
    if not pages:
        return []
    words: list[Word] = []
    for token in pages[0].get("tokens", []):
        layout = token.get("layout", {})
        segments = layout.get("textAnchor", {}).get("textSegments", [])
        content = "".join(text[int(s.get("startIndex", 0)) : int(s.get("endIndex", 0))] for s in segments).strip()
        vertices = layout.get("boundingPoly", {}).get("normalizedVertices", [])
        if not content or not vertices:
            continue
        xs = [float(v.get("x", 0.0)) for v in vertices]
        ys = [float(v.get("y", 0.0)) for v in vertices]
        words.append(
            Word(
                text=content,
                x0=max(0.0, min(xs)),
                y0=max(0.0, min(ys)),
                x1=min(1.0, max(xs)),
                y1=min(1.0, max(ys)),
                confidence=float(layout.get("confidence", 1.0)),
            )
        )
    return words
