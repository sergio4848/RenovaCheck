"""Local OCR with Tesseract (Polish model), called as a subprocess with TSV output."""

from __future__ import annotations

import csv
import io
import shutil
import subprocess

from PIL import Image

from renova_extract.documents.models import Word
from renova_extract.ocr.base import OcrUnavailableError

WORD_LEVEL = "5"


class TesseractPol:
    name = "tesseract"

    def __init__(self, language: str = "pol", timeout_seconds: float = 60.0, binary: str = "tesseract") -> None:
        self.language = language
        self.timeout_seconds = timeout_seconds
        self.binary = binary

    def available(self) -> bool:
        return shutil.which(self.binary) is not None

    def recognize(self, image: Image.Image) -> list[Word]:
        executable = shutil.which(self.binary)
        if executable is None:
            raise OcrUnavailableError("tesseract binary not found")
        buffer = io.BytesIO()
        image.save(buffer, "PNG")
        try:
            completed = subprocess.run(  # noqa: S603 - argv is constant apart from the language code
                [executable, "stdin", "stdout", "-l", self.language, "--psm", "3", "tsv"],
                input=buffer.getvalue(),
                capture_output=True,
                timeout=self.timeout_seconds,
                check=True,
            )
        except subprocess.TimeoutExpired as exc:
            raise OcrUnavailableError("tesseract timed out") from exc
        except subprocess.CalledProcessError as exc:
            raise OcrUnavailableError(f"tesseract failed with exit code {exc.returncode}") from exc
        return parse_tsv(completed.stdout.decode("utf-8", errors="replace"), image.width, image.height)


def parse_tsv(tsv: str, width: int, height: int) -> list[Word]:
    words: list[Word] = []
    for row in csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE):
        text = (row.get("text") or "").strip()
        if row.get("level") != WORD_LEVEL or not text:
            continue
        confidence = float(row["conf"])
        if confidence < 0:
            continue
        left, top = int(row["left"]), int(row["top"])
        w, h = int(row["width"]), int(row["height"])
        words.append(
            Word(
                text=text,
                x0=left / width,
                y0=top / height,
                x1=(left + w) / width,
                y1=(top + h) / height,
                confidence=confidence / 100,
            )
        )
    return words
