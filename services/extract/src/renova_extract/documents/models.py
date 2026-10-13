"""In-memory representation of an analysed document: pages, their image and positioned words.

Word boxes are normalized to the page ([0, 1], origin top-left), the same convention as the
synthetic ground truth and the page images shown in the review screen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from PIL import Image


class TextSource(StrEnum):
    TEXT_LAYER = "text_layer"
    OCR = "ocr"
    NONE = "none"


@dataclass(frozen=True)
class Word:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    confidence: float = 1.0


@dataclass
class Page:
    number: int
    width_pt: float
    height_pt: float
    image: Image.Image
    words: list[Word] = field(default_factory=list)
    source: TextSource = TextSource.NONE

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)


@dataclass
class LoadedDocument:
    mime: str
    pages: list[Page]

    @property
    def text(self) -> str:
        return "\n".join(p.text for p in self.pages)
