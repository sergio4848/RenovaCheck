"""Exact money arithmetic and the Polish formats it is printed in."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def money(value: Decimal | int | str) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class LineItem:
    name: str
    quantity: Decimal
    unit: str
    unit_net: Decimal
    vat_rate: int

    @property
    def net(self) -> Decimal:
        return money(self.quantity * self.unit_net)

    @property
    def vat(self) -> Decimal:
        return money(self.net * self.vat_rate / 100)

    @property
    def gross(self) -> Decimal:
        return self.net + self.vat


@dataclass(frozen=True)
class Totals:
    net: Decimal
    vat: Decimal
    gross: Decimal


def totals(items: list[LineItem]) -> Totals:
    net = sum((i.net for i in items), Decimal(0))
    vat = sum((i.vat for i in items), Decimal(0))
    return Totals(money(net), money(vat), money(net + vat))


def format_pln(value: Decimal, style: int) -> str:
    """Formats seen on Polish invoices: '12 345,67 zł', '12345,67 PLN', '12.345,67 zł'."""
    sign = "-" if value < 0 else ""
    whole, frac = f"{abs(value):.2f}".split(".")
    if style == 1:
        return f"{sign}{whole},{frac} PLN"
    groups: list[str] = []
    while len(whole) > 3:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    groups.insert(0, whole)
    separator = "." if style == 2 else " "
    return f"{sign}{separator.join(groups)},{frac} zł"


def format_kw(value: float, style: int) -> str:
    text = f"{value:g}".replace(".", ",")
    return f"{text} kW" if style == 0 else f"{text}kW"
