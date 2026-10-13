"""Turns a clean PDF into a low-quality scan: rasterize, skew, add noise and blur, JPEG-compress,
and wrap the images back into a PDF without a text layer.

Bounding boxes move with the skew; transform_bbox() maps a clean-page box to the scanned page.
"""

from __future__ import annotations

import io
import math
import time
from dataclasses import dataclass

import numpy as np
import pypdfium2 as pdfium
from PIL import Image, ImageFilter

from renova_synth.model import BBox

DPI = 150
FIXED_DATE = time.gmtime(1767225600)  # 2026-01-01T00:00:00Z, keeps output byte-identical


@dataclass(frozen=True)
class ScanResult:
    pdf: bytes
    angles: tuple[float, ...]


def degrade(pdf: bytes, seed: int) -> ScanResult:
    rng = np.random.default_rng(seed)
    document = pdfium.PdfDocument(pdf)
    pages: list[Image.Image] = []
    angles: list[float] = []
    try:
        for index in range(len(document)):
            bitmap = document[index].render(scale=DPI / 72, grayscale=True)
            image = bitmap.to_pil().convert("L")
            angle = float(rng.uniform(-1.6, 1.6))
            angles.append(angle)
            pages.append(_degrade_page(image, angle, rng))
    finally:
        document.close()

    out = io.BytesIO()
    first, rest = pages[0], pages[1:]
    first.save(
        out, "PDF", save_all=True, append_images=rest, resolution=DPI, creationDate=FIXED_DATE, modDate=FIXED_DATE
    )
    return ScanResult(out.getvalue(), tuple(angles))


def _degrade_page(image: Image.Image, angle: float, rng: np.random.Generator) -> Image.Image:
    rotated = image.rotate(angle, resample=Image.Resampling.BICUBIC, fillcolor=255)
    pixels = np.asarray(rotated, dtype=np.float32)
    pixels = pixels * rng.uniform(0.88, 0.97) + rng.uniform(4, 14)  # grey paper, faded ink
    pixels += rng.normal(0, 14, pixels.shape)  # sensor noise
    speckles = rng.random(pixels.shape) < 0.0015  # dust
    pixels[speckles] = rng.uniform(0, 90, int(speckles.sum()))
    noisy = Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8), mode="L")
    blurred = noisy.filter(ImageFilter.GaussianBlur(radius=float(rng.uniform(0.5, 0.9))))
    buffer = io.BytesIO()
    blurred.save(buffer, "JPEG", quality=int(rng.integers(35, 55)))
    return Image.open(io.BytesIO(buffer.getvalue())).convert("L")


def transform_bbox(bbox: BBox, angle_deg: float, page_w: float, page_h: float) -> BBox:
    """Box of a region after PIL's counter-clockwise rotation by angle_deg about the page centre."""
    theta = math.radians(angle_deg)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    cx, cy = page_w / 2, page_h / 2
    xs, ys = [], []
    for nx, ny in ((bbox.x0, bbox.y0), (bbox.x1, bbox.y0), (bbox.x0, bbox.y1), (bbox.x1, bbox.y1)):
        dx, dy = nx * page_w - cx, ny * page_h - cy
        xs.append((cx + dx * cos_t + dy * sin_t) / page_w)
        ys.append((cy - dx * sin_t + dy * cos_t) / page_h)
    return BBox(
        x0=max(0.0, round(min(xs), 5)),
        y0=max(0.0, round(min(ys), 5)),
        x1=min(1.0, round(max(xs), 5)),
        y1=min(1.0, round(max(ys), 5)),
    )
