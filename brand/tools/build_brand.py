"""Build the RenovaCheck logo set (SVG) from one geometry definition.

python brand/tools/build_brand.py   (needs fontTools; Inter must be installed, see brand/README.md)
"""

from __future__ import annotations

from pathlib import Path

from text_to_path import outline

ROOT = Path(__file__).resolve().parents[1]
INTER_BOLD = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"

TEAL = "#0F766E"
INK = "#0B1F33"
AMBER = "#F59E0B"
WHITE = "#FFFFFF"
TEAL_LIGHT = "#5EEAD4"

# The mark on a 64 x 64 grid: a roof, the walls of a house and a check mark inside it.
ROOF = "M8 29 L32 9 L56 29"
WALLS = "M15 26 V50 Q15 54 19 54 H45 Q49 54 49 50 V26"
CHECK = "M23 39.5 L29.5 46 L41.5 33.5"
STROKE = 6


def mark(house: str, check: str, x: float = 0, y: float = 0, size: float = 64, stroke: float = STROKE) -> str:
    s = size / 64
    style = f'fill="none" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round"'
    return (
        f'<g transform="translate({x} {y}) scale({s:.4f})">'
        f'<path d="{ROOF}" stroke="{house}" {style}/>'
        f'<path d="{WALLS}" stroke="{house}" {style}/>'
        f'<path d="{CHECK}" stroke="{check}" {style}/>'
        "</g>"
    )


def svg(width: float, height: float, body: str, title: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:g} {height:g}" '
        f'width="{width:g}" height="{height:g}" role="img" aria-label="{title}">'
        f"<title>{title}</title>{body}</svg>\n"
    )


def horizontal(house: str, check: str, renova: str, check_word: str, name: str) -> None:
    size = 40
    first = outline(INTER_BOLD, "Renova", size, -0.6)
    second = outline(INTER_BOLD, "Check", size, -0.6)
    mark_size = 56
    gap = 14
    height = 64
    baseline = height / 2 + float(first["cap"]) / 2
    text_x = mark_size + gap
    width = text_x + float(first["width"]) + float(second["width"]) + 2
    body = (
        mark(house, check, 0, (height - mark_size) / 2, mark_size)
        + f'<path transform="translate({text_x} {baseline:.2f})" d="{first["d"]}" fill="{renova}"/>'
        + f'<path transform="translate({text_x + float(first["width"]):.2f} {baseline:.2f})" '
        f'd="{second["d"]}" fill="{check_word}"/>'
    )
    (ROOT / "logo" / name).write_text(svg(round(width), height, body, "RenovaCheck"))


def main() -> None:
    (ROOT / "logo").mkdir(exist_ok=True)
    horizontal(TEAL, AMBER, INK, TEAL, "logo-horizontal.svg")
    horizontal(WHITE, AMBER, WHITE, TEAL_LIGHT, "logo-inverse.svg")
    horizontal(INK, INK, INK, INK, "logo-mono.svg")
    (ROOT / "logo" / "logo-mark.svg").write_text(svg(64, 64, mark(TEAL, AMBER), "RenovaCheck"))
    # Favicon: the mark on a filled tile, so it stays legible at 16 px on any tab colour.
    tile = f'<rect width="64" height="64" rx="14" fill="{TEAL}"/>' + mark(WHITE, AMBER, 6, 6, 52, stroke=8)
    (ROOT / "logo" / "favicon.svg").write_text(svg(64, 64, tile, "RenovaCheck"))


if __name__ == "__main__":
    main()
