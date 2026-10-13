"""Reading structure over positioned words: lines, column segments and text spans with boxes.

Words come from the PDF text layer or OCR with boxes normalized to the page (origin top-left).
A *line* groups words whose vertical centres are close; a *segment* is a run of words in a line
without a wide horizontal gap, which separates columns and right-aligned values.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from statistics import median

from renova_extract.documents.models import Page, Word
from renova_extract.text.normalize import fold

# Gap (in multiples of the word height) that ends a segment: wider than any word space.
SEGMENT_GAP = 1.6


@dataclass(frozen=True)
class Box:
    x0: float
    y0: float
    x1: float
    y1: float

    @staticmethod
    def around(words: list[Word]) -> Box:
        return Box(
            min(w.x0 for w in words), min(w.y0 for w in words), max(w.x1 for w in words), max(w.y1 for w in words)
        )

    def as_dict(self) -> dict[str, float]:
        return {
            k: round(max(0.0, min(1.0, v)), 5)
            for k, v in (("x0", self.x0), ("y0", self.y0), ("x1", self.x1), ("y1", self.y1))
        }


@dataclass
class Span:
    """A run of words joined by single spaces, mapping character offsets back to word boxes."""

    words: list[Word]

    def __post_init__(self) -> None:
        self.text = " ".join(w.text for w in self.words)
        self.folded = fold(self.text)
        self._starts: list[int] = []
        offset = 0
        for word in self.words:
            self._starts.append(offset)
            offset += len(word.text) + 1

    @property
    def box(self) -> Box:
        return Box.around(self.words)

    @property
    def x0(self) -> float:
        return self.words[0].x0

    @property
    def confidence(self) -> float:
        return min(w.confidence for w in self.words)

    def sub(self, start: int, end: int) -> tuple[Box, float]:
        """Box and confidence of characters [start, end); partial words are cut proportionally."""
        boxes: list[Box] = []
        confidence = 1.0
        for word, word_start in zip(self.words, self._starts, strict=True):
            word_end = word_start + len(word.text)
            lo, hi = max(start, word_start), min(end, word_end)
            if lo >= hi:
                continue
            width = (word.x1 - word.x0) / max(1, len(word.text))
            boxes.append(
                Box(word.x0 + (lo - word_start) * width, word.y0, word.x0 + (hi - word_start) * width, word.y1)
            )
            confidence = min(confidence, word.confidence)
        if not boxes:
            return self.box, self.confidence
        return Box(
            min(b.x0 for b in boxes), min(b.y0 for b in boxes), max(b.x1 for b in boxes), max(b.y1 for b in boxes)
        ), confidence

    def after(self, index: int) -> Span | None:
        rest = self.words[index:]
        return Span(rest) if rest else None


@dataclass
class Line:
    words: list[Word]
    segments: list[Span]

    @property
    def y0(self) -> float:
        return min(w.y0 for w in self.words)

    @property
    def y1(self) -> float:
        return max(w.y1 for w in self.words)

    @property
    def span(self) -> Span:
        return Span(self.words)


@dataclass
class PageLayout:
    page: Page
    lines: list[Line]


def build_lines(words: list[Word]) -> list[Line]:
    if not words:
        return []
    heights = [w.y1 - w.y0 for w in words if w.y1 > w.y0]
    line_height = median(heights) if heights else 0.01
    rows: list[list[Word]] = []
    for word in sorted(words, key=lambda w: ((w.y0 + w.y1) / 2, w.x0)):
        centre = (word.y0 + word.y1) / 2
        if rows:
            last = rows[-1]
            last_centre = median((w.y0 + w.y1) / 2 for w in last)
            if abs(centre - last_centre) <= line_height * 0.5:
                last.append(word)
                continue
        rows.append([word])
    lines = []
    for row in rows:
        row.sort(key=lambda w: w.x0)
        lines.append(Line(row, _segments(row)))
    return lines


def _segments(row: list[Word]) -> list[Span]:
    segments: list[list[Word]] = [[row[0]]]
    for previous, word in pairwise(row):
        # Relative to the neighbouring words' height: a space in a large title is wide too.
        height = max(previous.y1 - previous.y0, word.y1 - word.y0)
        if word.x0 - previous.x1 > height * SEGMENT_GAP:
            segments.append([word])
        else:
            segments[-1].append(word)
    return [Span(s) for s in segments]


def layout(pages: list[Page]) -> list[PageLayout]:
    return [PageLayout(page, build_lines(page.words)) for page in pages]


def anchor_tokens(phrase: str) -> list[str]:
    return [_key(t) for t in fold(phrase).split()]


def _key(token: str) -> str:
    return fold(token).rstrip(".,;:")


def find_anchor(words: list[Word], tokens: list[str], start: int = 0) -> int | None:
    """Index just past the first occurrence of the token sequence in words[start:]."""
    keys = [_key(w.text) for w in words]
    n = len(tokens)
    for i in range(start, len(keys) - n + 1):
        if keys[i : i + n] == tokens:
            return i + n
    return None


def segment_is(segment: Span, tokens: list[str]) -> bool:
    return [_key(w.text) for w in segment.words] == tokens
