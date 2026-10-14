"""Build the RenovaCheck logo set (SVG) from one geometry definition.

python brand/tools/build_brand.py   (needs fontTools; the wordmark font is brand/fonts/Geist-SemiBold.ttf)
"""

from __future__ import annotations

from pathlib import Path

from text_to_path import outline

ROOT = Path(__file__).resolve().parents[1]
WORDMARK_FONT = str(ROOT / "fonts" / "Geist-SemiBold.ttf")

INK = "#111418"
PAPER = "#FAFAF7"
TEAL = "#0F766E"
TEAL_ON_INK = "#5FBFB2"

# The mark on a 64 x 64 grid: a house drawn as one sharp line (roof and walls, open at the bottom
# right like a page corner) and a check mark inside it. Square caps and mitred joins, one weight.
HOUSE = "M12 54 V27 L32 10 L52 27 V54 H30"
CHECK = "M21 39 L29 47 L44 31"
STROKE = 5.5


def mark(house: str, check: str, x: float = 0, y: float = 0, size: float = 64, stroke: float = STROKE) -> str:
    s = size / 64
    style = (
        f'fill="none" stroke-width="{stroke}" stroke-linecap="square" stroke-linejoin="miter" stroke-miterlimit="10"'
    )
    return (
        f'<g transform="translate({x} {y}) scale({s:.4f})">'
        f'<path d="{HOUSE}" stroke="{house}" {style}/>'
        f'<path d="{CHECK}" stroke="{check}" {style}/>'
        "</g>"
    )


def svg(width: float, height: float, body: str, title: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:g} {height:g}" '
        f'width="{width:g}" height="{height:g}" role="img" aria-label="{title}">'
        f"<title>{title}</title>{body}</svg>\n"
    )


def horizontal(house: str, check: str, word: str, name: str) -> None:
    text = outline(WORDMARK_FONT, "RenovaCheck", 40, -1.0)
    mark_size = 56
    gap = 12
    height = 64
    baseline = height / 2 + float(text["cap"]) / 2
    text_x = mark_size + gap
    width = text_x + float(text["width"]) + 2
    body = mark(house, check, 0, (height - mark_size) / 2, mark_size) + (
        f'<path transform="translate({text_x} {baseline:.2f})" d="{text["d"]}" fill="{word}"/>'
    )
    (ROOT / "logo" / name).write_text(svg(round(width), height, body, "RenovaCheck"))


def main() -> None:
    (ROOT / "logo").mkdir(exist_ok=True)
    horizontal(INK, TEAL, INK, "logo-horizontal.svg")
    horizontal(PAPER, TEAL_ON_INK, PAPER, "logo-inverse.svg")
    horizontal(INK, INK, INK, "logo-mono.svg")
    (ROOT / "logo" / "logo-mark.svg").write_text(svg(64, 64, mark(INK, TEAL), "RenovaCheck"))
    # Favicon: the mark in paper on an ink tile with square corners; heavier strokes for 16 px.
    tile = f'<rect width="64" height="64" rx="3" fill="{INK}"/>' + mark(PAPER, TEAL_ON_INK, 5, 5, 54, stroke=8)
    (ROOT / "logo" / "favicon.svg").write_text(svg(64, 64, tile, "RenovaCheck"))


if __name__ == "__main__":
    main()
