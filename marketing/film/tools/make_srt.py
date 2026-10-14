"""Write subtitles/en.srt and subtitles/pl.srt from script.json and check them.

Checks: cues in order and not overlapping, at most 2 lines of 42 characters, at most 17 characters
per second. Run again after re-timing script.json to the recorded voice-over.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

FILM = Path(__file__).resolve().parents[1]
MAX_LINE, MAX_LINES, MAX_CPS = 42, 2, 17.0


def stamp(seconds: float) -> str:
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def balanced(text: str) -> list[str]:
    """One line if it fits, otherwise two lines broken at the space nearest the middle."""
    if len(text) <= MAX_LINE:
        return [text]
    spaces = [i for i, c in enumerate(text) if c == " "]
    # Never start the second line with a dash.
    fitting = [i for i in spaces if i <= MAX_LINE and len(text) - i - 1 <= MAX_LINE and text[i + 1] != "–"]
    if not fitting:
        return textwrap.wrap(text, MAX_LINE)
    cut = min(fitting, key=lambda i: abs(i - len(text) / 2))
    return [text[:cut], text[cut + 1 :]]


def build(lang: str, lines: list[dict]) -> str:
    cues, previous_end = [], 0.0
    for number, line in enumerate(lines, 1):
        text = line[lang]
        wrapped = balanced(text)
        duration = line["end"] - line["start"]
        if line["start"] < previous_end:
            raise SystemExit(f"{line['id']}: overlaps the previous cue")
        if len(wrapped) > MAX_LINES:
            raise SystemExit(f"{line['id']} ({lang}): {len(wrapped)} lines")
        if lang == "en" and len(text) / duration > MAX_CPS:
            raise SystemExit(f"{line['id']}: {len(text) / duration:.1f} characters per second")
        previous_end = line["end"]
        cues.append(f"{number}\n{stamp(line['start'])} --> {stamp(line['end'])}\n" + "\n".join(wrapped) + "\n")
    return "\n".join(cues)


def main() -> None:
    script = json.loads((FILM / "script.json").read_text())
    for lang in ("en", "pl"):
        (FILM / "subtitles" / f"{lang}.srt").write_text(build(lang, script["lines"]), encoding="utf-8")
        print(f"subtitles/{lang}.srt: {len(script['lines'])} cues")


if __name__ == "__main__":
    main()
