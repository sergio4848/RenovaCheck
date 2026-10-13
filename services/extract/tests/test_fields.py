from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from renova_extract.core.config import Settings
from renova_extract.documents.loader import load_document
from renova_extract.documents.models import Page, TextSource, Word
from renova_extract.fields import normalize as norm
from renova_extract.fields.dictionary import FieldDictionary
from renova_extract.fields.extractors import FieldExtractor
from renova_extract.fields.layout import Box, build_lines
from renova_extract.fields.signature import signature_region

FIXTURES = Path(__file__).parent / "fixtures"
DICTIONARY = FieldDictionary.from_yaml(Settings().rules_dir / "fields.yaml")


# ---------------------------------------------------------------------------- normalizers
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1 234,56 zł", "1234.56"),
        ("1234,56 PLN", "1234.56"),
        ("1.234,56 zł", "1234.56"),
        ("12 345 678,90 zł", "12345678.90"),
        ("-1 080,00 zł", "-1080.00"),
        ("\u22121 080,00 zł", "-1080.00"),
        ("1\u00a0234,56 zł", "1234.56"),
        ("Razem brutto: 49 522,27 zł", "49522.27"),
        ("1234.56", "1234.56"),
        (42498.0, "42498.00"),
        ("2026-05-10", None),
        ("brak", None),
    ],
)
def test_money(text: str | float, expected: str | None) -> None:
    assert norm.money(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [("05.06.2026", "2026-06-05"), ("2026-06-05", "2026-06-05"), ("5.6.2026", "2026-06-05"), ("31.02.2026", None)],
)
def test_dates(text: str, expected: str | None) -> None:
    assert norm.parse_date(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("10 kW", "10"),
        ("10kW", "10"),
        ("7,5 kW", "7.5"),
        ("12 KW", "12"),
        (10.0, "10"),
        ("10", "10"),
        ("dziesięć", None),
    ],
)
def test_power(text: str | float, expected: str | None) -> None:
    assert norm.power_kw(text) == expected


@pytest.mark.parametrize(
    "printed",
    ["ul. Tadeusza Kościuszki", "ul. Kościuszki", "ul. T. Kościuszki", "ul. Kosciuszki", "KOŚCIUSZKI", "Kościuszki,"],
)
def test_street_spellings_compare_equal(printed: str) -> None:
    assert norm.street(printed) == "kosciuszki"


def test_street_keeps_multi_word_names_and_never_drops_the_last_word() -> None:
    assert norm.street("al. Wojska Polskiego") == "wojska polskiego"
    assert norm.street("ul. Jana") == "jana"


@pytest.mark.parametrize("printed", ["TVX-10A", "tvx-10a", "TVX 10A", "TVX\u201310A", "TVX10A"])
def test_model_ignores_case_dashes_and_spaces(printed: str) -> None:
    assert norm.model(printed) == "TVX10A"


def test_model_variants_stay_different() -> None:
    assert norm.model("TVX-10A") != norm.model("TVX-10B")


@pytest.mark.parametrize(
    ("field_type", "raw"),
    [
        ("money", "12.345,67 zł"),
        ("date", "05.06.2026"),
        ("power_kw", "7,5 kW"),
        ("street", "ul. H. Sienkiewicza"),
        ("city", "Dębowa Wola Górna"),
        ("name", "Józef  Kozłowski"),
        ("nip", "003-089-12-45"),
        ("postal_code", "98 - 134"),
        ("model", "nw-aw 08a"),
        ("identifier", "OF/2026/708,"),
        ("building_no", "17a"),
    ],
)
def test_normalizers_are_idempotent(field_type: str, raw: str) -> None:
    once = norm.normalize(field_type, raw)
    assert once is not None
    assert norm.normalize(field_type, once) == once


def test_money_formats_are_interchangeable() -> None:
    # Metamorphic: the same amount printed in each Polish style normalizes to one value.
    styles = ["45 700,20 zł", "45700,20 PLN", "45.700,20 zł"]
    assert {norm.money(s) for s in styles} == {"45700.20"}


# ---------------------------------------------------------------------------- dictionary
def test_dictionary_covers_every_ground_truth_field() -> None:
    names = {f.name for f in DICTIONARY.fields}
    assert {"amount_net", "address_street", "product_model", "signature_investor", "zum_id"} <= names
    for spec in DICTIONARY.fields:
        assert spec.extract, spec.name
        assert spec.documents, spec.name
        for rule in spec.extract:
            if rule.method in ("label", "block", "above", "signature"):
                assert rule.anchors, f"{spec.name}: {rule.method} needs anchors"


def test_longer_anchors_are_tried_first() -> None:
    anchors = DICTIONARY.get("amount_vat").extract[0].anchors
    assert anchors[-1] == "vat"


def test_fields_follow_the_document_type() -> None:
    karta = {f.name for f in DICTIONARY.fields_for("karta_produktu")}
    assert "zum_id" in karta and "amount_net" not in karta
    assert len(DICTIONARY.fields_for(None)) == len(DICTIONARY.fields)


# ---------------------------------------------------------------------------- layout
def _w(text: str, x0: float, y0: float, x1: float, h: float = 0.01, conf: float = 1.0) -> Word:
    return Word(text, x0, y0, x1, y0 + h, conf)


def test_lines_split_into_column_segments() -> None:
    words = [
        _w("WYKONAWCA", 0.07, 0.20, 0.17),
        _w("NABYWCA", 0.54, 0.201, 0.62),
        _w("Energo-Montaż", 0.07, 0.22, 0.19),
        _w("Józef", 0.54, 0.22, 0.58),
        _w("Kozłowski", 0.585, 0.221, 0.66),
    ]
    lines = build_lines(words)
    assert [[s.text for s in line.segments] for line in lines] == [
        ["WYKONAWCA", "NABYWCA"],
        ["Energo-Montaż", "Józef Kozłowski"],
    ]


def test_span_boxes_cut_partial_words() -> None:
    line = build_lines([_w("25,", 0.10, 0.5, 0.13)])[0]
    box, _ = line.span.sub(0, 2)
    assert box.x0 == pytest.approx(0.10) and box.x1 == pytest.approx(0.12)


# ---------------------------------------------------------------------------- extraction
def _page(words: list[Word]) -> Page:
    return Page(1, 595.0, 842.0, Image.new("L", (100, 100), 255), words, TextSource.OCR)


def test_extracts_the_fixture_invoice_with_provenance() -> None:
    doc = load_document((FIXTURES / "faktura_clean.pdf").read_bytes(), 50, None)
    fields = {f.name: f for f in FieldExtractor(DICTIONARY).extract(doc.pages, "faktura")}
    assert fields["document_number"].value == "FV/145/05/2026"
    assert fields["amount_gross"].value == "49522.27"
    assert fields["amount_gross"].text == "49 522,27 zł"
    assert fields["address_street"].value == "kwiatowa"
    assert fields["contractor_name"].text == "EkoTerm Instalacje Sp. j."
    assert fields["contractor_nip"].value == "0011211137"
    assert fields["invoice_date"].value == "2026-05-29"
    for f in fields.values():
        assert f.page == 1 and f.status == "ok" and 0 < f.confidence <= 1
        assert 0 <= f.bbox.x0 < f.bbox.x1 <= 1 and 0 <= f.bbox.y0 < f.bbox.y1 <= 1
    # Only invoice fields are read from an invoice.
    assert "zum_id" not in fields and "signature_investor" not in fields


def test_label_without_a_readable_value_is_unreadable_not_guessed() -> None:
    words = [_w("Razem", 0.6, 0.3, 0.65), _w("netto:", 0.66, 0.3, 0.71), _w("4S 7OO,2O", 0.80, 0.3, 0.9, conf=0.4)]
    fields = {f.name: f for f in FieldExtractor(DICTIONARY).extract([_page(words)], "faktura")}
    assert fields["amount_net"].status == "unreadable"
    assert fields["amount_net"].value is None
    assert fields["amount_net"].confidence == 0


def test_ocr_confidence_lowers_field_confidence() -> None:
    words = [_w("Razem", 0.6, 0.3, 0.65), _w("netto:", 0.66, 0.3, 0.71), _w("100,00", 0.80, 0.3, 0.86, conf=0.6)]
    words.append(_w("zł", 0.865, 0.3, 0.88, conf=0.9))
    field = next(f for f in FieldExtractor(DICTIONARY).extract([_page(words)], "faktura") if f.name == "amount_net")
    assert field.value == "100.00"
    assert field.confidence == pytest.approx(0.98 * 0.6)


def test_value_continues_on_a_skewed_neighbour_line() -> None:
    # A long scanned line drifts; the value after "model" lands on its own line.
    words = [
        _w("producent", 0.10, 0.300, 0.18),
        _w("Termavix,", 0.19, 0.301, 0.26),
        _w("model", 0.27, 0.302, 0.31),
        _w("TVX-10A,", 0.32, 0.308, 0.38),
    ]
    fields = {f.name: f for f in FieldExtractor(DICTIONARY).extract([_page(words)], "faktura")}
    assert fields["product_model"].value == "TVX10A"


def test_unknown_type_reads_every_field() -> None:
    words = [_w("Pozycja", 0.1, 0.3, 0.16), _w("na", 0.17, 0.3, 0.19), _w("liście", 0.2, 0.3, 0.25)]
    words += [_w("ZUM", 0.26, 0.3, 0.29), _w("ZUM/PC/1818", 0.5, 0.3, 0.6)]
    names = {f.name for f in FieldExtractor(DICTIONARY).extract([_page(words)], None)}
    assert "zum_id" in names


# ---------------------------------------------------------------------------- signatures
def _signature_page(signed: bool) -> tuple[Page, Box]:
    image = Image.new("L", (1240, 1754), 255)
    caption = Box(0.1, 0.8, 0.2, 0.81)
    if signed:
        draw = ImageDraw.Draw(image)
        y = int(0.8 * 1754) - 40
        draw.line([(140, y), (200, y - 30), (260, y + 5), (330, y - 25)], fill=0, width=3)
    return Page(1, 595.0, 842.0, image, [], TextSource.TEXT_LAYER), caption


@pytest.mark.parametrize("signed", [True, False])
def test_signature_is_ink_above_the_caption(signed: bool) -> None:
    page, caption = _signature_page(signed)
    assert signature_region(page, caption) == (signed, 1.0)
