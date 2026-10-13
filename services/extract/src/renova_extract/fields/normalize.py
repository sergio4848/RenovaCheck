"""Parsing printed values into comparable ones.

Every parser takes the text as printed and returns the normalized value, or ``None`` when the
text is not a value of that type. Normalizers are idempotent: a normalized value parses to
itself, so the ground truth (already normalized) and extracted text compare with the same code.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from renova_extract.text.normalize import fold

Normalized = str | bool

# 1 234,56 zł · 1234,56 PLN · 1.234,56 zł · -1 080,00 zł · 1234.56 (already normalized)
MONEY = re.compile(
    r"(?<![\d,.])(?P<sign>[-\u2212\u2013])?\s?(?P<int>\d{1,3}(?:[ \u00a0.]\d{3})+|\d+)(?:[,.](?P<frac>\d{2}))?"
    r"(?:\s?(?P<cur>zł|zl|PLN|pln))?(?![\d])"
)
DATE = re.compile(
    r"(?<!\d)(?:(?P<d>\d{1,2})[.\-/](?P<m>\d{1,2})[.\-/](?P<y>\d{4})|(?P<iy>\d{4})-(?P<im>\d{2})-(?P<id>\d{2}))(?!\d)"
)
POWER = re.compile(r"(?<![\d,.])(?P<num>\d{1,3}(?:[.,]\d{1,2})?)\s?kW\b", re.IGNORECASE)
POSTAL = re.compile(r"(?<!\d)(\d{2})\s?-\s?(\d{3})(?!\d)")
NIP_DIGITS = re.compile(r"(?<!\d)(?:\d[\s-]?){9}\d(?!\d)")
BUILDING = re.compile(r"^\d{1,4}[A-Za-z]?(?:/\d{1,4}[A-Za-z]?)?$")
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9/._-]*[A-Za-z0-9]$|^[A-Za-z0-9]$")

CENT = Decimal("0.01")
_SPACES = re.compile(r"\s+")
_TRAILING_PUNCT = ".,;:"

# Street-name prefixes (ulica, aleja, plac, osiedle, rondo, skwer) and patron first names in the
# genitive, which addresses print or omit at will ("ul. Tadeusza Kościuszki" = "Kościuszki").
_STREET_PREFIXES = {"ul", "ulica", "al", "aleja", "aleje", "pl", "plac", "os", "osiedle", "rondo", "skwer"}
_PATRON_FIRST_NAMES = {
    "adama",
    "andrzeja",
    "antoniego",
    "boleslawa",
    "czeslawa",
    "emilii",
    "fryderyka",
    "henryka",
    "ignacego",
    "jana",
    "jozefa",
    "juliana",
    "juliusza",
    "kazimierza",
    "krola",
    "ks",
    "ksiedza",
    "marii",
    "mikolaja",
    "pawla",
    "piotra",
    "romualda",
    "stanislawa",
    "stefana",
    "tadeusza",
    "wincentego",
    "wladyslawa",
    "wojciecha",
    "zygmunta",
    "gen",
    "generala",
    "kardynala",
    "sw",
    "swietego",
}
_INITIAL = re.compile(r"^[a-z]\.?$")


def collapse(text: str) -> str:
    return _SPACES.sub(" ", text.replace("\u00a0", " ")).strip()


def strip_punct(token: str) -> str:
    return token.rstrip(_TRAILING_PUNCT)


def money(text: str | float | int) -> str | None:
    """'1 234,56 zł' -> '1234.56'; amounts are exact decimals, never floats."""
    if isinstance(text, bool):
        return None
    if isinstance(text, int | float):
        return str(Decimal(str(text)).quantize(CENT, rounding=ROUND_HALF_UP))
    match = MONEY.search(collapse(text))
    if match is None or (match.group("frac") is None and match.group("cur") is None):
        return None
    whole = re.sub(r"[ \u00a0.]", "", match.group("int"))
    try:
        value = Decimal(f"{whole}.{match.group('frac') or '00'}")
    except InvalidOperation:
        return None
    if match.group("sign"):
        value = -value
    return str(value.quantize(CENT))


def money_in(text: str) -> re.Match[str] | None:
    """First amount with a currency or two decimals, for locating values in a line."""
    for match in MONEY.finditer(text):
        if match.group("frac") is not None or match.group("cur") is not None:
            return match
    return None


def parse_date(text: str | float | int) -> str | None:
    """'05.06.2026' or '2026-06-05' -> '2026-06-05' (ISO); impossible dates are not dates."""
    match = DATE.search(str(text))
    if match is None:
        return None
    if match.group("y"):
        y, m, d = int(match.group("y")), int(match.group("m")), int(match.group("d"))
    else:
        y, m, d = int(match.group("iy")), int(match.group("im")), int(match.group("id"))
    try:
        return date(y, m, d).isoformat()
    except ValueError:
        return None


def power_kw(text: str | float | int) -> str | None:
    """'10 kW', '10kW', '7,5 kW' -> '10', '7.5' (decimal string without trailing zeros)."""
    if isinstance(text, bool):
        return None
    if isinstance(text, int | float):
        number = Decimal(str(text))
    else:
        match = POWER.search(text)
        if match is None:
            # Already normalized ('10', '7.5') or a bare number next to a 'kW' label.
            bare = text.strip()
            if not re.fullmatch(r"\d{1,3}(?:[.,]\d{1,2})?", bare):
                return None
            number = Decimal(bare.replace(",", "."))
        else:
            number = Decimal(match.group("num").replace(",", "."))
    normalized = number.normalize()
    return f"{normalized:f}"


def nip(text: str | float | int) -> str | None:
    match = NIP_DIGITS.search(str(text))
    return re.sub(r"\D", "", match.group(0)) if match else None


def postal_code(text: str | float | int) -> str | None:
    match = POSTAL.search(str(text))
    return f"{match.group(1)}-{match.group(2)}" if match else None


def building_no(text: str | float | int) -> str | None:
    value = strip_punct(collapse(str(text))).upper()
    return value if BUILDING.match(value) else None


def street(text: str | float | int) -> str | None:
    """'ul. T. Kościuszki' / 'Tadeusza Kościuszki' / 'KOSCIUSZKI' -> 'kosciuszki'."""
    tokens = fold(str(text)).replace(".", ". ").split()
    tokens = [t for t in tokens if t not in (".",)]
    while tokens and strip_punct(tokens[0]) in _STREET_PREFIXES:
        tokens.pop(0)
    # Drop patron first names and initials, but never the last word (the street name itself).
    while len(tokens) > 1 and (strip_punct(tokens[0]) in _PATRON_FIRST_NAMES or _INITIAL.match(tokens[0])):
        tokens.pop(0)
    value = " ".join(strip_punct(t) for t in tokens).strip()
    return value or None


def city(text: str | float | int) -> str | None:
    value = fold(strip_punct(str(text)))
    return value or None


def name(text: str | float | int) -> str | None:
    """People and company names compare without case, diacritics and punctuation spacing."""
    value = fold(strip_punct(str(text)))
    return value or None


def model(text: str | float | int) -> str | None:
    """'tvx-10a', 'TVX 10A', 'TVX_10A' or any dash -> 'TVX10A'."""
    value = re.sub(r"[\s\-\u2010\u2011\u2012\u2013\u2014_]+", "", strip_punct(str(text))).upper()
    return value if value and IDENTIFIER.match(value) else None


def identifier(text: str | float | int) -> str | None:
    value = strip_punct(collapse(str(text))).upper()
    return value if IDENTIFIER.match(value) else None


def boolean(text: str | float | int | bool) -> bool | None:
    if isinstance(text, bool):
        return text
    folded = fold(str(text))
    if folded in ("true", "tak", "1", "yes"):
        return True
    if folded in ("false", "nie", "0", "no"):
        return False
    return None


def text_value(text: str | float | int) -> str | None:
    value = collapse(strip_punct(str(text)))
    return value or None


NORMALIZERS: dict[str, Callable[..., Normalized | None]] = {
    "text": name,
    "name": name,
    "street": street,
    "building_no": building_no,
    "postal_code": postal_code,
    "city": city,
    "nip": nip,
    "money": money,
    "power_kw": power_kw,
    "date": parse_date,
    "identifier": identifier,
    "model": model,
    "bool": boolean,
}


def normalize(field_type: str, raw: str | float | int | bool | None) -> Normalized | None:
    if raw is None:
        return None
    return NORMALIZERS[field_type](raw)
