"""Text normalization shared by classification and (later) field matching."""

from __future__ import annotations

import re
import unicodedata

_POLISH = str.maketrans({"ł": "l", "Ł": "L"})  # ł has no Unicode decomposition
_SPACES = re.compile(r"\s+")


def fold(text: str) -> str:
    """Lower case, without diacritics, with single spaces: 'Protokół  ODBIORU' -> 'protokol odbioru'."""
    decomposed = unicodedata.normalize("NFKD", text.translate(_POLISH))
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return _SPACES.sub(" ", stripped.casefold()).strip()
