from __future__ import annotations

import random
from decimal import Decimal

import numpy as np
import pytest
from PIL import Image

from renova_synth import data
from renova_synth.model import BBox
from renova_synth.money import LineItem, format_kw, format_pln, totals
from renova_synth.scan import transform_bbox


def test_nip_is_checksum_valid_and_uses_unassigned_prefix() -> None:
    rng = random.Random(1)
    for _ in range(200):
        value = data.nip(rng)
        assert value.startswith("00")
        assert data.nip_is_valid(value)
    assert not data.nip_is_valid("0012345670")


@pytest.mark.parametrize(
    ("value", "style", "expected"),
    [
        (Decimal("45700.2"), 0, "45 700,20 zł"),
        (Decimal("45700.2"), 1, "45700,20 PLN"),
        (Decimal("1234567.5"), 2, "1.234.567,50 zł"),
        (Decimal("-1000"), 0, "-1 000,00 zł"),
        (Decimal("999"), 0, "999,00 zł"),
    ],
)
def test_polish_money_formats(value: Decimal, style: int, expected: str) -> None:
    assert format_pln(value, style) == expected


def test_kw_formats() -> None:
    assert format_kw(8.0, 0) == "8 kW"
    assert format_kw(10.0, 1) == "10kW"


def test_totals_round_per_line_and_mix_vat_rates() -> None:
    items = [
        LineItem("a", Decimal(1), "szt.", Decimal("100.05"), 8),
        LineItem("b", Decimal(1), "usł.", Decimal("50.00"), 23),
    ]
    t = totals(items)
    assert t.net == Decimal("150.05")
    assert t.vat == Decimal("8.00") + Decimal("11.50")
    assert t.gross == t.net + t.vat


def test_feminine_surnames() -> None:
    assert data.feminine_surname("Wiśniewski") == "Wiśniewska"
    assert data.feminine_surname("Mazur") == "Mazur"


@pytest.mark.parametrize("angle", [-1.5, -0.4, 0.7, 1.6])
def test_bbox_transform_follows_pil_rotation(angle: float) -> None:
    w, h = 600, 800
    image = Image.new("L", (w, h), 255)
    image.paste(0, (100, 150, 140, 170))  # a dark block
    rotated = np.asarray(image.rotate(angle, resample=Image.Resampling.NEAREST, fillcolor=255))
    ys, xs = np.nonzero(rotated < 128)
    box = transform_bbox(BBox(x0=100 / w, y0=150 / h, x1=140 / w, y1=170 / h), angle, w, h)
    assert abs(xs.min() / w - box.x0) < 0.005
    assert abs(xs.max() / w - box.x1) < 0.005
    assert abs(ys.min() / h - box.y0) < 0.005
    assert abs(ys.max() / h - box.y1) < 0.005


def test_bbox_rejects_empty_boxes() -> None:
    with pytest.raises(ValueError):
        BBox(x0=0.5, y0=0.1, x1=0.5, y1=0.2)
