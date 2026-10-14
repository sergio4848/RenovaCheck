"""Build preview/animatic.mp4: the 60 s cut with real UI clips and graphics at their final times, a placeholder card
for each AI shot (its description), the overlays, and burned-in English subtitles. No audio.

python marketing/film/tools/make_animatic.py   (ffmpeg with libass; Inter font installed)
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

FILM = Path(__file__).resolve().parents[1]
FONT = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
W, H, FPS = 1280, 720, 25


def run(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%")


def media(rel: str) -> Path:
    """Paths in shots.json are relative to the Premiere media folder; map them to this package."""
    folder, name = rel.split("/", 1)
    return FILM / {"ui": "ui", "gfx": "graphics"}[folder] / name


def segment(shot: dict, out: Path) -> None:
    duration = shot["end"] - shot["start"]
    base = ["-t", f"{duration:.3f}"]
    if shot["source"] == "ai":
        title = escape(f"{shot['id']}  ·  AI (Seedance 2.5)")
        note = escape(shot["note"])
        draw = (
            f"drawtext=fontfile={FONT}:text='{title}':fontcolor=0xF59E0B:fontsize=34:x=(w-tw)/2:y=h/2-50,"
            f"drawtext=fontfile={FONT}:text='{note}':fontcolor=0xCFE9E5:fontsize=28:x=(w-tw)/2:y=h/2+10"
        )
        run("-f", "lavfi", "-i", f"color=c=0x0B1F33:s={W}x{H}:r={FPS}", *base, "-vf", draw, *encode(out))
    elif (source := media(shot["file"])).suffix == ".png":
        # Stills: fit the frame; the report page gets a slow zoom like in the edit plan.
        zoom = "zoompan=z='min(1+0.0009*on,1.12)':d=1:s=1280x720:fps=25," if "report" in source.name else ""
        fit = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=white,"
        run("-loop", "1", "-i", str(source), *base, "-vf", f"{fit}{zoom}fps={FPS},format=yuv420p", *encode(out))
    else:
        run(
            "-ss",
            f"{shot['in']:.3f}",
            "-i",
            str(source),
            *base,
            "-vf",
            f"fps={FPS},format=yuv420p",
            "-an",
            *encode(out),
        )
    if overlay := shot.get("overlay"):
        start = 0 if overlay.endswith("logo_transparent.png") else 0.6
        end = duration - (0 if start == 0 else 0.4)
        layered = out.with_suffix(".o.mp4")
        run(
            "-i",
            str(out),
            "-loop",
            "1",
            "-i",
            str(media(overlay)),
            "-filter_complex",
            f"[0][1]overlay=0:0:enable='between(t,{start},{end:.2f})':shortest=1,format=yuv420p",
            "-t",
            f"{duration:.3f}",
            *encode(layered),
        )
        layered.replace(out)


def encode(out: Path) -> list[str]:
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", str(FPS), "-pix_fmt", "yuv420p", str(out)]


def main() -> None:
    shots = json.loads((FILM / "shots.json").read_text())["shots"]
    out = FILM / "preview" / "animatic.mp4"
    out.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        parts = []
        for shot in shots:
            part = Path(tmp) / f"{shot['id']}.mp4"
            segment(shot, part)
            parts.append(part)
        listing = Path(tmp) / "parts.txt"
        listing.write_text("".join(f"file '{p}'\n" for p in parts))
        joined = Path(tmp) / "joined.mp4"
        run("-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(joined))
        style = "FontName=Inter SemiBold,FontSize=16,PrimaryColour=&H00FFFFFF,BackColour=&H4D331F0B,BorderStyle=4,Outline=6,Shadow=0,MarginV=34"
        srt = FILM / "subtitles" / "en.srt"
        run(
            "-i",
            str(joined),
            "-vf",
            f"subtitles={srt}:force_style='{style}'",
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(out),
        )
    print(out.relative_to(FILM))


if __name__ == "__main__":
    main()
