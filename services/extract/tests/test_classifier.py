from __future__ import annotations

from pathlib import Path

import pytest

from renova_extract.classify.classifier import DocTypeClassifier
from renova_extract.core.config import Settings
from renova_extract.text.normalize import fold

RULES = Settings().rules_dir / "doc_types.yaml"


@pytest.fixture(scope="module")
def classifier() -> DocTypeClassifier:
    return DocTypeClassifier.from_yaml(RULES)


def test_fold_removes_polish_diacritics_and_spacing() -> None:
    assert fold("PROTOKÓŁ   ODBIORU Końcowego") == "protokol odbioru koncowego"
    assert fold("Zaliczka\nbrutto") == "zaliczka brutto"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Faktura VAT nr FV/1/05/2026 Razem brutto: 10 000,00 zł", "faktura"),
        ("Faktura zaliczkowa nr FZ/3/05/2026 Dotyczy umowy nr UM/1", "faktura_zaliczkowa"),
        ("Faktura korygująca nr FK/2 Korekta do faktury nr FV/1", "faktura_korygujaca"),
        ("UMOWA nr UM/2026/1 zawarta w dniu 01.02.2026", "umowa"),
        ("ANEKS nr UM/2026/1/A1 do umowy nr UM/2026/1", "aneks"),
        ("OFERTA nr OF/2026/9 Oferta ważna 30 dni", "oferta"),
        ("PROTOKÓŁ ODBIORU KOŃCOWEGO nr PO/1 Data odbioru", "protokol_odbioru"),
        ("Termavix KARTA PRODUKTU — pompa ciepła SCOP 4,1", "karta_produktu"),
        ("WYCIĄG Z WNIOSKU O DOFINANSOWANIE Numer wniosku: CP/2026/1", "wniosek_ekstrakt"),
    ],
)
def test_titles_decide_the_type(classifier: DocTypeClassifier, text: str, expected: str) -> None:
    result = classifier.classify(text)
    assert result.doc_type == expected
    assert result.evidence


def test_mentions_in_body_text_do_not_change_the_type(classifier: DocTypeClassifier) -> None:
    text = "UMOWA nr UM/1 zawarta w dniu ... Odbiór potwierdzony protokołem odbioru, faktura po odbiorze."
    assert classifier.classify(text).doc_type == "umowa"


def test_unknown_or_ambiguous_text_is_left_for_a_person(classifier: DocTypeClassifier) -> None:
    assert classifier.classify("Lorem ipsum dolor sit amet").doc_type is None
    ambiguous = classifier.classify("Faktura VAT nr 1 oraz Oferta nr 2")
    assert ambiguous.doc_type is None
    assert set(ambiguous.scores) == {"faktura", "oferta"}


def test_rules_file_is_where_settings_point(tmp_path: Path) -> None:
    assert RULES.is_file()
