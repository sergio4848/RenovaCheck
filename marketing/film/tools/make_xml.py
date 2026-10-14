"""Write edit/renovacheck_assembly.xml: a first assembly as Final Cut Pro 7 XML (xmeml), importable by Premiere Pro.

Tracks: V1 picture (AI shots, UI clips, title and end card), V2 overlays (logo, callouts, chips), A1 voice-over
segments at their script times, A2 music, A3 sound effects. Media paths point to `media_root` from shots.json;
missing files import as offline clips and are relinked in Premiere. Subtitles come from subtitles/*.srt.

python marketing/film/tools/make_xml.py [--media-root "C:/.../renovaCheck/media"]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import quote
from xml.etree import ElementTree as ET

FILM = Path(__file__).resolve().parents[1]
STILL_FRAMES = 25 * 60 * 10  # stills are "long" sources; only in/out matter


def frames(seconds: float, fps: int) -> int:
    return round(seconds * fps)


def sub(parent: ET.Element, tag: str, text: str | int | None = None, **attrs: str) -> ET.Element:
    el = ET.SubElement(parent, tag, attrs)
    if text is not None:
        el.text = str(text)
    return el


def rate(parent: ET.Element, fps: int) -> None:
    r = sub(parent, "rate")
    sub(r, "timebase", fps)
    sub(r, "ntsc", "FALSE")


class Builder:
    def __init__(self, media_root: str, fps: int, width: int, height: int) -> None:
        self.root = media_root.rstrip("/")
        self.fps, self.width, self.height = fps, width, height
        self.files: set[str] = set()
        self.count = 0

    def pathurl(self, rel: str) -> str:
        return "file://localhost/" + quote(f"{self.root}/{rel}".lstrip("/"), safe="/:")

    def file(self, parent: ET.Element, rel: str, kind: str, duration: int) -> None:
        file_id = "file-" + rel.replace("/", "-")
        if file_id in self.files:
            sub(parent, "file", id=file_id)
            return
        self.files.add(file_id)
        f = sub(parent, "file", id=file_id)
        sub(f, "name", Path(rel).name)
        sub(f, "pathurl", self.pathurl(rel))
        rate(f, self.fps)
        sub(f, "duration", duration)
        media = sub(f, "media")
        if kind == "video":
            sc = sub(sub(media, "video"), "samplecharacteristics")
            sub(sc, "width", self.width)
            sub(sc, "height", self.height)
        else:
            sc = sub(sub(media, "audio"), "samplecharacteristics")
            sub(sc, "depth", 16)
            sub(sc, "samplerate", 48000)

    def clip(self, track: ET.Element, name: str, rel: str, kind: str, start: float, end: float, src_in: float) -> None:
        self.count += 1
        item = sub(track, "clipitem", id=f"clip-{self.count}")
        length = frames(end - start, self.fps)
        still = rel.endswith(".png")
        source = STILL_FRAMES if still else frames(src_in, self.fps) + length
        sub(item, "name", name)
        sub(item, "enabled", "TRUE")
        sub(item, "duration", source)
        rate(item, self.fps)
        sub(item, "start", frames(start, self.fps))
        sub(item, "end", frames(start, self.fps) + length)
        sub(item, "in", frames(src_in, self.fps))
        sub(item, "out", frames(src_in, self.fps) + length)
        if still:
            sub(item, "stillframe", "TRUE")
        self.file(item, rel, kind, source)


def build(shots: dict, script: dict, media_root: str) -> ET.ElementTree:
    seq_info = shots["sequence"]
    fps = seq_info["fps"]
    b = Builder(media_root, fps, seq_info["width"], seq_info["height"])
    xmeml = ET.Element("xmeml", version="5")
    seq = sub(xmeml, "sequence", id="sequence-1")
    sub(seq, "name", seq_info["name"])
    sub(seq, "duration", frames(seq_info["duration_s"], fps))
    rate(seq, fps)
    media = sub(seq, "media")

    video = sub(media, "video")
    fmt = sub(sub(video, "format"), "samplecharacteristics")
    rate(fmt, fps)
    sub(fmt, "width", seq_info["width"])
    sub(fmt, "height", seq_info["height"])
    sub(fmt, "pixelaspectratio", "square")
    v1, v2 = sub(video, "track"), sub(video, "track")
    for shot in shots["shots"]:
        b.clip(v1, shot["id"], shot["file"], "video", shot["start"], shot["end"], shot["in"])
        if overlay := shot.get("overlay"):
            # Callouts appear 0.6 s after the cut and leave 0.4 s before the next one.
            start = shot["start"] if overlay.endswith("logo_transparent.png") else shot["start"] + 0.6
            b.clip(
                v2,
                f"{shot['id']} overlay",
                overlay,
                "video",
                start,
                shot["end"] - (0 if start == shot["start"] else 0.4),
                0,
            )

    audio = sub(media, "audio")
    a1, a2, a3 = sub(audio, "track"), sub(audio, "track"), sub(audio, "track")
    lines = script["lines"]
    for i, line in enumerate(lines):
        # Room for the voice's tail, but never into the next segment.
        tail = min(0.4, lines[i + 1]["start"] - line["end"]) if i + 1 < len(lines) else 0.4
        b.clip(a1, line["id"], f"vo/{line['id']}.wav", "audio", line["start"], line["end"] + tail, 0)
    b.clip(a2, "music", shots["audio"]["music"]["file"], "audio", 0, seq_info["duration_s"], 0)
    for n, fx in enumerate(sorted(shots["audio"]["sfx"], key=lambda s: s["at"]), 1):
        b.clip(a3, f"sfx {n}", fx["file"], "audio", fx["at"], fx["at"] + 1.2, 0)

    tc = sub(seq, "timecode")
    rate(tc, fps)
    sub(tc, "string", "00:00:00:00")
    sub(tc, "frame", 0)
    sub(tc, "displayformat", "NDF")
    ET.indent(xmeml)
    return ET.ElementTree(xmeml)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--media-root")
    args = parser.parse_args()
    shots = json.loads((FILM / "shots.json").read_text())
    script = json.loads((FILM / "script.json").read_text())
    tree = build(shots, script, args.media_root or shots["media_root"])
    out = FILM / "edit" / "renovacheck_assembly.xml"
    out.parent.mkdir(exist_ok=True)
    with out.open("wb") as fh:
        fh.write(b'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n')
        tree.write(fh, encoding="utf-8", xml_declaration=False)
    print(out.relative_to(FILM), f"{len(shots['shots'])} shots, {len(script['lines'])} voice-over segments")


if __name__ == "__main__":
    main()
