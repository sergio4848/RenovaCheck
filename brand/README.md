# RenovaCheck brand kit

The mark is a house drawn as one sharp line, open at the bottom like a page corner, with a check mark
inside: documents of a renovation project, checked. The wordmark is set in Geist SemiBold and outlined,
so logo files need no installed font. Style, colours and rules for everything else: [`DESIGN.md`](DESIGN.md).

## Files

| File | Use |
|---|---|
| `logo/logo-horizontal.svg` | Default logo on light backgrounds |
| `logo/logo-inverse.svg` | On dark backgrounds (ink, photos, video) |
| `logo/logo-mono.svg` | One colour (ink); print, stamps, fax-like documents |
| `logo/logo-mark.svg` | The mark alone, when the name is already visible |
| `logo/favicon.svg` | Browser tab and app icon (mark on an ink tile, heavier strokes) |
| `logo/png/` | PNG exports: horizontal and inverse 1600 px wide, mark and app icon 512/1024 px, transparent |
| `social/social-card-1200x630.png` | Link preview (Open Graph, LinkedIn) |

Film graphics (title and end card, margin notes, trust list, hand-drawn marks; PNG and animated
ProRes 4444 overlays) are in `marketing/film/graphics/`.

`fonts/`: Geist and Geist Mono (OFL, `fonts/OFL-Geist.txt`), needed to render and edit the graphics.

## Colours

Palette, roles and contrast ratios: [`DESIGN.md` §2](DESIGN.md#2-colour-palette-and-roles). The logo
uses Ink `#111418` and Teal `#0F766E` on light backgrounds, Paper `#FAFAF7` and `#5FBFB2` on dark ones.

## Rules

* Clear space around the logo: at least the height of the mark's roof (¼ of the mark height).
* Minimum size: horizontal logo 24 px high on screen, 8 mm in print; below that use the mark or
  the favicon.
* Do not recolour, stretch, rotate, outline or add effects to the logo. Do not set "RenovaCheck"
  in another font next to the mark.
* "RenovaCheck" is one word with a capital R and C.
* Interface typography: system sans-serif (Tabler). Marketing and video: Geist and Geist Mono
  (SIL Open Font License 1.1, `fonts/`).

## Regenerating

```sh
pip install fonttools==4.60.1
python brand/tools/build_brand.py          # SVGs (wordmark font: fonts/Geist-SemiBold.ttf)
node brand/tools/render_graphics.js        # PNG exports, film graphics and animated overlays
                                           # (Playwright + Chromium, ffmpeg; install fonts/*.ttf first)
```
