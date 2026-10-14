"""Turn a line of text set in a given font into an SVG path (outlines), so logos do not depend on installed fonts.

python text_to_path.py FONT TEXT SIZE  ->  prints JSON {"d": ..., "width": ..., "ascent": ..., "descent": ...}
"""

from __future__ import annotations

import json
import sys

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont


def outline(font_path: str, text: str, size: float, tracking: float = 0.0) -> dict[str, float | str]:
    font = TTFont(font_path)
    scale = size / font["head"].unitsPerEm
    cmap = font.getBestCmap()
    glyphs = font.getGlyphSet()
    hmtx = font["hmtx"]
    pen = SVGPathPen(glyphs)
    x = 0.0
    for char in text:
        name = cmap[ord(char)]
        # Font units have y up; SVG has y down: flip around the baseline.
        glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, x, 0)))
        x += hmtx[name][0] * scale + tracking
    os2 = font["OS/2"]
    return {
        "d": pen.getCommands(),
        "width": round(x - tracking, 2),
        "ascent": round(os2.sTypoAscender * scale, 2),
        "descent": round(-os2.sTypoDescender * scale, 2),
        "cap": round(getattr(os2, "sCapHeight", 0) * scale, 2),
    }


if __name__ == "__main__":
    print(
        json.dumps(
            outline(sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]) if len(sys.argv) > 4 else 0.0)
        )
    )
