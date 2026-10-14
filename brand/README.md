# RenovaCheck brand kit

The mark is a house whose interior holds a check mark: documents of a renovation project, checked.
The wordmark is set in Inter Bold. All logo files are vector outlines and need no installed font.

## Files

| File | Use |
|---|---|
| `logo/logo-horizontal.svg` | Default logo on light backgrounds |
| `logo/logo-inverse.svg` | On dark backgrounds (ink, photos, video) |
| `logo/logo-mono.svg` | One colour (ink); print, stamps, fax-like documents |
| `logo/logo-mark.svg` | The mark alone, when the name is already visible |
| `logo/favicon.svg` | Browser tab and app icon (mark on a teal tile, heavier strokes) |
| `logo/png/` | PNG exports: horizontal and inverse 1600 px wide, mark and app icon 512/1024 px, transparent |
| `social/social-card-1200x630.png` | Link preview (Open Graph, LinkedIn) |

Film graphics (title card, end card, callouts, cursor) are in `marketing/film/graphics/`.

## Colours

| Name | Hex | Role |
|---|---|---|
| Teal | `#0F766E` | Primary: the mark, "Check", links, primary actions |
| Ink | `#0B1F33` | Text, dark backgrounds |
| Amber | `#F59E0B` | Accent: the check mark, highlights, call to action |
| Teal light | `#5EEAD4` | "Check" on dark backgrounds |
| Paper | `#F6F8FB` | Light surfaces |

WCAG contrast (normal text needs 4.5, large text and graphics 3.0):

| Foreground | Background | Ratio | Use |
|---|---|---|---|
| Ink | White | 16.7 | any text |
| Teal | White | 5.5 | text and icons |
| White | Teal | 5.5 | button labels |
| Teal light | Ink | 11.3 | text on dark |
| Amber | Ink | 7.8 | text and graphics on dark |
| Ink | Amber | 7.8 | call-to-action label |
| Amber | White | 2.2 | **decoration only**: never text, never the only carrier of meaning on white |

## Rules

* Clear space around the logo: at least the height of the mark's roof (¼ of the mark height).
* Minimum size: horizontal logo 24 px high on screen, 8 mm in print; below that use the mark or
  the favicon.
* Do not recolour, stretch, rotate, outline or add effects to the logo. Do not set "RenovaCheck"
  in another font next to the mark.
* "RenovaCheck" is one word with a capital R and C.
* Interface typography: system sans-serif (Tabler). Marketing and video: Inter (SIL Open Font
  License 1.1).

## Regenerating

```sh
pip install fonttools==4.60.1
python brand/tools/build_brand.py          # SVGs (needs Inter: /usr/share/fonts/opentype/inter)
node brand/tools/render_graphics.js        # PNG exports and film graphics (Playwright + Chromium)
```
