"""File type detection by content (magic bytes), never by name or declared type."""

from __future__ import annotations

PDF = "application/pdf"
PNG = "image/png"
JPEG = "image/jpeg"


def sniff_mime(data: bytes) -> str | None:
    head = data[:1024]
    if head.lstrip(b"\x00\t\r\n\x0c ").startswith(b"%PDF-"):
        return PDF
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return PNG
    if head.startswith(b"\xff\xd8\xff"):
        return JPEG
    return None
