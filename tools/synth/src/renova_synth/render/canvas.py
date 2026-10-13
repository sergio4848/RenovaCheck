"""A reportlab canvas that records where each tagged value is drawn.

Coordinates passed in are PDF points with the origin at the bottom-left (reportlab's convention).
Recorded boxes are normalized to [0, 1] with the origin at the top-left, matching page images.
"""

from __future__ import annotations

import io
import random
from dataclasses import dataclass, field
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from renova_synth.model import BBox, NormalizedValue

FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"
FONTS = {
    "sans": ("DejaVu", "DejaVuSans.ttf", "DejaVu-Bold", "DejaVuSans-Bold.ttf"),
    "liberation": ("Liberation", "LiberationSans-Regular.ttf", "Liberation-Bold", "LiberationSans-Bold.ttf"),
}
ASCENT = 0.80
DESCENT = 0.24
PAGE_W, PAGE_H = A4


def register_fonts() -> None:
    registered = set(pdfmetrics.getRegisteredFontNames())
    for regular, regular_file, bold, bold_file in FONTS.values():
        for name, file in ((regular, regular_file), (bold, bold_file)):
            if name not in registered:
                pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / file)))


@dataclass(frozen=True)
class Placed:
    name: str
    text: str
    value: NormalizedValue
    page: int
    bbox: BBox
    error_id: str | None


@dataclass
class TrackedCanvas:
    family: str = "sans"
    placed: list[Placed] = field(default_factory=list)
    page: int = 1

    def __post_init__(self) -> None:
        register_fonts()
        self._buffer = io.BytesIO()
        # invariant=1 omits timestamps and random ids so identical input gives identical bytes.
        self.canvas = Canvas(self._buffer, pagesize=A4, invariant=1, pageCompression=1)
        self.regular, _, self.bold, _ = FONTS[self.family]

    def font(self, size: float, bold: bool = False) -> None:
        self.canvas.setFont(self.bold if bold else self.regular, size)

    def width(self, text: str, size: float = 9, bold: bool = False) -> float:
        return float(pdfmetrics.stringWidth(text, self.bold if bold else self.regular, size))

    def text(self, x: float, y: float, text: str, size: float = 9, bold: bool = False) -> float:
        """Draw untracked text; returns the x coordinate after it."""
        self.font(size, bold)
        self.canvas.drawString(x, y, text)
        return x + pdfmetrics.stringWidth(text, self.bold if bold else self.regular, size)

    def right(self, x_right: float, y: float, text: str, size: float = 9, bold: bool = False) -> None:
        self.font(size, bold)
        self.canvas.drawRightString(x_right, y, text)

    def field(
        self,
        name: str,
        x: float,
        y: float,
        text: str,
        value: NormalizedValue,
        size: float = 9,
        bold: bool = False,
        align: str = "left",
        error_id: str | None = None,
    ) -> float:
        """Draw a value and record its box; returns the x coordinate after it."""
        face = self.bold if bold else self.regular
        width = pdfmetrics.stringWidth(text, face, size)
        x0 = x - width if align == "right" else x
        self.font(size, bold)
        self.canvas.drawString(x0, y, text)
        self.record(name, text, value, x0, y - DESCENT * size, x0 + width, y + ASCENT * size, error_id)
        return x0 + width

    def record(
        self,
        name: str,
        text: str,
        value: NormalizedValue,
        x0: float,
        y_bottom: float,
        x1: float,
        y_top: float,
        error_id: str | None = None,
    ) -> None:
        bbox = BBox(
            x0=_clamp(x0 / PAGE_W),
            y0=_clamp((PAGE_H - y_top) / PAGE_H),
            x1=_clamp(x1 / PAGE_W),
            y1=_clamp((PAGE_H - y_bottom) / PAGE_H),
        )
        self.placed.append(Placed(name, text, value, self.page, bbox, error_id))

    def line(self, x0: float, y0: float, x1: float, y1: float, width: float = 0.5) -> None:
        self.canvas.setLineWidth(width)
        self.canvas.line(x0, y0, x1, y1)

    def rect(self, x: float, y: float, w: float, h: float, width: float = 0.5) -> None:
        self.canvas.setLineWidth(width)
        self.canvas.rect(x, y, w, h)

    def signature(self, x: float, y: float, rng: random.Random) -> None:
        """A handwritten-looking scribble inside a 150x30 pt area starting at (x, y)."""
        self.canvas.setLineWidth(1.1)
        path = self.canvas.beginPath()
        px, py = x + 8, y + 10 + rng.uniform(-3, 3)
        path.moveTo(px, py)
        for step in range(6):
            nx = px + rng.uniform(14, 24)
            ny = y + 6 + rng.uniform(0, 18)
            path.curveTo(px + 5, py + rng.uniform(-12, 12), nx - 5, ny + rng.uniform(-12, 12), nx, ny)
            px, py = nx, ny
            if step == 3:
                path.lineTo(px + 4, py - 6)
        self.canvas.drawPath(path, stroke=1, fill=0)

    def synthetic_marker(self) -> None:
        self.canvas.saveState()
        self.font(6.5)
        self.canvas.setFillGray(0.45)
        self.canvas.drawString(36, 22, "DOKUMENT SYNTETYCZNY — dane fikcyjne, wygenerowane do testów RenovaCheck")
        self.canvas.drawRightString(PAGE_W - 36, 22, f"str. {self.page}")
        self.canvas.restoreState()

    def next_page(self) -> None:
        self.synthetic_marker()
        self.canvas.showPage()
        self.page += 1

    def finish(self) -> bytes:
        self.synthetic_marker()
        self.canvas.showPage()
        self.canvas.save()
        return self._buffer.getvalue()


def _clamp(v: float) -> float:
    return min(1.0, max(0.0, round(v, 5)))


def wrap(text: str, width_pt: float, face: str, size: float) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if pdfmetrics.stringWidth(candidate, face, size) <= width_pt:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines
