"""OCR adapter interface. The text layer of a PDF is used first; an adapter is only asked to
read pages that have no usable text layer (scans, photos)."""

from __future__ import annotations

from typing import Protocol

from PIL import Image

from renova_extract.documents.models import Word


class OcrUnavailableError(RuntimeError):
    """The configured OCR engine cannot run (not installed, not configured, quota)."""


class OcrAdapter(Protocol):
    name: str

    def recognize(self, image: Image.Image) -> list[Word]:
        """Words in reading order with boxes normalized to the image."""
        ...
