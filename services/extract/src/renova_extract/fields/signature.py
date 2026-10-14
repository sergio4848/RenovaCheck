"""Signature presence: ink in the box above a signature caption.

Documents print a caption ("Wykonawca", "Zamawiający", ...) under a line; a signature is drawn
above the line. The check measures dark pixels in the page image between the line and roughly
three lines of text above it, which works the same for text-layer PDFs and scans.
"""

from __future__ import annotations

from PIL import Image

from renova_extract.documents.models import Page
from renova_extract.fields.layout import Box

# Geometry in PDF points relative to the caption's top edge (y grows downwards).
BOX_WIDTH_PT = 170.0
BOX_TOP_PT = 44.0  # top of the signature area above the caption
BOX_BOTTOM_PT = 3.5  # just above the caption, including the signature line
INK_BOTTOM_PT = 8.0  # ink is measured above the signature line
DARK = 128
# Share of dark pixels: a blank area stays near 0, a handwritten signature well above 1%.
SIGNED_RATIO = 0.004
UNSIGNED_RATIO = 0.0015


def region_box(page: Page, caption: Box) -> Box:
    return Box(
        caption.x0,
        caption.y0 - BOX_TOP_PT / page.height_pt,
        caption.x0 + BOX_WIDTH_PT / page.width_pt,
        caption.y0 - BOX_BOTTOM_PT / page.height_pt,
    )


def ink_ratio(image: Image.Image, box: Box) -> float | None:
    left, right = int(box.x0 * image.width), int(box.x1 * image.width)
    top, bottom = int(box.y0 * image.height), int(box.y1 * image.height)
    left, top = max(0, left), max(0, top)
    right, bottom = min(image.width, right), min(image.height, bottom)
    if right - left < 4 or bottom - top < 4:
        return None
    crop = image.crop((left, top, right, bottom)).convert("L")
    histogram = crop.histogram()
    dark = sum(histogram[:DARK])
    return dark / (crop.width * crop.height)


def signature_region(page: Page, caption: Box) -> tuple[bool, float] | None:
    """(signed, certainty) or None when the area is outside the page."""
    box = region_box(page, caption)
    ink_box = Box(box.x0, box.y0, box.x1, caption.y0 - INK_BOTTOM_PT / page.height_pt)
    ratio = ink_ratio(page.image, ink_box)
    if ratio is None:
        return None
    if ratio >= SIGNED_RATIO:
        return True, 1.0
    if ratio <= UNSIGNED_RATIO:
        return False, 1.0
    # Between the thresholds: decide by the nearer one, with lower certainty.
    signed = ratio - UNSIGNED_RATIO > SIGNED_RATIO - ratio
    return signed, 0.5
