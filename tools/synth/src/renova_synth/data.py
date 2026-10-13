"""Fictitious vocabularies for synthetic documents.

Nothing here identifies a real person, company or address: localities and product brands are
invented, NIP numbers start with the unassigned tax-office prefix "00", and every document
carries a "DOKUMENT SYNTETYCZNY" marker.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

FIRST_NAMES = (
    "Anna",
    "Maria",
    "Katarzyna",
    "Małgorzata",
    "Agnieszka",
    "Barbara",
    "Ewa",
    "Zofia",
    "Jan",
    "Piotr",
    "Krzysztof",
    "Andrzej",
    "Tomasz",
    "Paweł",
    "Józef",
    "Łukasz",
)
SURNAMES_M = (
    "Wiśniewski",
    "Wójcik",
    "Kamiński",
    "Lewandowski",
    "Zieliński",
    "Szymański",
    "Woźniak",
    "Dąbrowski",
    "Kozłowski",
    "Jankowski",
    "Mazur",
    "Krawczyk",
    "Grabowski",
    "Pawłowski",
)
FEMININE = {"Anna", "Maria", "Katarzyna", "Małgorzata", "Agnieszka", "Barbara", "Ewa", "Zofia"}

# Invented localities (with an invented gmina) for the investment address.
LOCALITIES = (
    ("Jarzębinowo", "Gmina Jarzębinowo"),
    ("Kalinowa Struga", "Gmina Strużyce"),
    ("Modrzewiowo", "Gmina Modrzewie"),
    ("Brzozówka Mała", "Gmina Brzozów Leśny"),
    ("Dębowa Wola Górna", "Gmina Dębowa Wola"),
    ("Zielonowo", "Gmina Zielonowo"),
    ("Cisowa Polana", "Gmina Cisówek"),
    ("Jaworzyn Stary", "Gmina Jaworzyn"),
)

# street key -> spelling variants (full patron name, short, initial, without diacritics)
STREETS: dict[str, tuple[str, ...]] = {
    "kosciuszki": ("ul. Tadeusza Kościuszki", "ul. Kościuszki", "ul. T. Kościuszki", "ul. Kosciuszki"),
    "mickiewicza": ("ul. Adama Mickiewicza", "ul. Mickiewicza", "ul. A. Mickiewicza", "Mickiewicza"),
    "slowackiego": ("ul. Juliusza Słowackiego", "ul. Słowackiego", "ul. J. Słowackiego", "ul. Slowackiego"),
    "lesna": ("ul. Leśna", "ul. Lesna", "Leśna", "ul. Leśna"),
    "polna": ("ul. Polna", "Polna", "ul. Polna", "ul. POLNA"),
    "sienkiewicza": ("ul. Henryka Sienkiewicza", "ul. Sienkiewicza", "ul. H. Sienkiewicza", "Sienkiewicza"),
    "kwiatowa": ("ul. Kwiatowa", "Kwiatowa", "ul. Kwiatowa", "ul. KWIATOWA"),
    "zeromskiego": ("ul. Stefana Żeromskiego", "ul. Żeromskiego", "ul. S. Żeromskiego", "ul. Zeromskiego"),
}

COMPANY_STEMS = (
    "EkoTerm Instalacje",
    "Ciepłomistrz",
    "Termo-Dom Serwis",
    "Zielone Ciepło",
    "Instal-Pomp",
    "AquaTermik",
    "Domowy Klimat",
    "Energo-Montaż",
)
COMPANY_FORMS = ("Sp. z o.o.", "s.c.", "Sp. j.", "")
CONTRACTOR_TOWNS = ("Wierzbin", "Olszanka Duża", "Grabowiec Nowy", "Lipowa Góra")


@dataclass(frozen=True)
class HeatPump:
    manufacturer: str
    family: str
    power_kw: int

    def model(self, variant: str, power_kw: int | None = None) -> str:
        return f"{self.family}-{power_kw or self.power_kw:02d}{variant}"


# Invented brands. Each model exists as an "A" and "B" variant of the same power.
MANUFACTURERS = ("Termavix", "Nordwarm Eko", "Polarion Heat", "Cieplik Systems")
FAMILIES = {"Termavix": "TVX", "Nordwarm Eko": "NW-AW", "Polarion Heat": "PH", "Cieplik Systems": "CS-PC"}
POWERS_KW = (6, 8, 10, 12)


def person_name(rng: random.Random) -> str:
    first = rng.choice(FIRST_NAMES)
    surname = rng.choice(SURNAMES_M)
    if first in FEMININE:
        surname = feminine_surname(surname)
    return f"{first} {surname}"


def feminine_surname(surname: str) -> str:
    for suffix, replacement in (("ski", "ska"), ("cki", "cka"), ("dzki", "dzka")):
        if surname.endswith(suffix):
            return surname[: -len(suffix)] + replacement
    return surname


def postal_code(rng: random.Random) -> str:
    return f"{rng.randint(10, 99):02d}-{rng.randint(100, 999):03d}"


def nip(rng: random.Random) -> str:
    """A checksum-valid NIP with the unassigned prefix 00x, so it cannot belong to a taxpayer."""
    weights = (6, 5, 7, 2, 3, 4, 5, 6, 7)
    while True:
        digits = [0, 0, rng.randint(1, 9)] + [rng.randint(0, 9) for _ in range(6)]
        check = sum(d * w for d, w in zip(digits, weights, strict=True)) % 11
        if check != 10:
            return "".join(map(str, [*digits, check]))


def nip_is_valid(value: str) -> bool:
    if len(value) != 10 or not value.isdigit():
        return False
    weights = (6, 5, 7, 2, 3, 4, 5, 6, 7)
    digits = [int(c) for c in value]
    return sum(d * w for d, w in zip(digits[:9], weights, strict=True)) % 11 == digits[9]


def format_nip(value: str, style: int) -> str:
    if style == 0:
        return f"{value[:3]}-{value[3:6]}-{value[6:8]}-{value[8:]}"
    return value


def company_name(rng: random.Random) -> str:
    form = rng.choice(COMPANY_FORMS)
    return f"{rng.choice(COMPANY_STEMS)} {form}".strip()


def heat_pump(rng: random.Random) -> HeatPump:
    manufacturer = rng.choice(MANUFACTURERS)
    return HeatPump(manufacturer, FAMILIES[manufacturer], rng.choice(POWERS_KW))
