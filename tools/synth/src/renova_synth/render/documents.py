"""Polish document templates. Two layouts (A, B) per type vary labels and positions so an
extractor cannot rely on one fixed layout."""

from __future__ import annotations

import random
from collections.abc import Callable

from renova_synth.model import DocType
from renova_synth.money import LineItem, format_pln
from renova_synth.render.canvas import PAGE_H, PAGE_W, TrackedCanvas, wrap
from renova_synth.scenario import DocSpec

LEFT = 42.0
RIGHT = PAGE_W - 42.0
CONTRACTOR_ADDRESS = {
    "sans": ("ul. Przemysłowa 7", "11-222 Wierzbin"),
    "liberation": ("ul. Rzemieślnicza 15A", "33-444 Grabowiec Nowy"),
}


def render(doc: DocSpec, rng: random.Random) -> tuple[bytes, TrackedCanvas]:
    c = TrackedCanvas(family=doc.font_family)
    RENDERERS[doc.doc_type](c, doc, rng)
    return c.finish(), c


# --------------------------------------------------------------------------- building blocks
def _v(doc: DocSpec, name: str) -> tuple[str, object, str | None]:
    value = doc.values[name]
    return value.text, value.value, value.error_id


def _field(
    c: TrackedCanvas,
    doc: DocSpec,
    name: str,
    x: float,
    y: float,
    size: float = 9,
    bold: bool = False,
    align: str = "left",
) -> float:
    text, value, error_id = _v(doc, name)
    return c.field(name, x, y, text, value, size=size, bold=bold, align=align, error_id=error_id)  # type: ignore[arg-type]


def _labelled(c: TrackedCanvas, doc: DocSpec, label: str, name: str, x: float, y: float, size: float = 9) -> None:
    after = c.text(x, y, f"{label} ", size=size)
    _field(c, doc, name, after, y, size=size)


def _address_line(c: TrackedCanvas, doc: DocSpec, x: float, y: float, size: float = 9) -> float:
    """'<street> <no>, <postal> <city>' with each part tracked; returns y of the next line."""
    after = _field(c, doc, "address_street", x, y, size)
    after = _field(c, doc, "address_building_no", after + 3, y, size)
    after = c.text(after, y, ",", size)
    after = _field(c, doc, "address_postal_code", after + 3, y, size)
    _field(c, doc, "address_city", after + 3, y, size)
    return y - size * 1.5


def _contractor_block(c: TrackedCanvas, doc: DocSpec, label: str, x: float, y: float) -> float:
    c.text(x, y, label, size=8, bold=True)
    y -= 13
    _field(c, doc, "contractor_name", x, y, 9.5, bold=True)
    street, town = CONTRACTOR_ADDRESS[doc.font_family]
    c.text(x, y - 13, street)
    c.text(x, y - 25, town)
    _labelled(c, doc, "NIP:", "contractor_nip", x, y - 37)
    return y - 52


def _investor_block(c: TrackedCanvas, doc: DocSpec, label: str, x: float, y: float) -> float:
    c.text(x, y, label, size=8, bold=True)
    y -= 13
    _field(c, doc, "investor_name", x, y, 9.5, bold=True)
    y = _address_line(c, doc, x, y - 13)
    return y - 12


def _title(c: TrackedCanvas, doc: DocSpec, title: str, centered: bool) -> float:
    y = PAGE_H - 60
    label = f"{title} nr "
    x = (PAGE_W - c.width(label + doc.number, size=15, bold=True)) / 2 if centered else LEFT
    after = c.text(x, y, label, size=15, bold=True)
    c.field("document_number", after, y, doc.number, doc.number, size=15, bold=True)
    return y - 28


def _place_date(c: TrackedCanvas, doc: DocSpec, name: str, label: str, y: float) -> None:
    text, _, _ = _v(doc, name)
    after = c.text(RIGHT - c.width(f"{label} {text}"), y, f"{label} ")
    _field(c, doc, name, after, y)


def _product_line(c: TrackedCanvas, doc: DocSpec, y: float, power_label: str) -> float:
    after = c.text(LEFT, y, "Urządzenie: pompa ciepła powietrze-woda, producent ")
    after = _field(c, doc, "product_manufacturer", after, y)
    after = c.text(after, y, ", model ")
    after = _field(c, doc, "product_model", after, y, bold=True)
    after = c.text(after, y, f", {power_label} ")
    _field(c, doc, "product_power_kw", after, y)
    return y - 16


COLS = (
    ("Lp.", 22, "l"),
    ("Nazwa towaru / usługi", 190, "l"),
    ("Ilość", 30, "r"),
    ("J.m.", 30, "l"),
    ("Cena netto", 60, "r"),
    ("VAT", 30, "r"),
    ("Wartość netto", 62, "r"),
    ("Wartość brutto", 66, "r"),
)


def _items_table(c: TrackedCanvas, doc: DocSpec, items: list[LineItem], y: float) -> float:
    x = LEFT
    c.line(LEFT, y + 10, RIGHT, y + 10)
    for header, width, align in COLS:
        if align == "r":
            c.right(x + width - 3, y, header, size=7.5, bold=True)
        else:
            c.text(x + 2, y, header, size=7.5, bold=True)
        x += width
    c.line(LEFT, y - 4, RIGHT, y - 4)
    y -= 16
    for number, item in enumerate(items, start=1):
        name_lines = wrap(item.name, 185, c.regular, 8)
        cells = (
            str(number),
            name_lines[0],
            f"{item.quantity:g}",
            item.unit,
            format_pln(item.unit_net, doc.money_style),
            f"{item.vat_rate}%",
            format_pln(item.net, doc.money_style),
            format_pln(item.gross, doc.money_style),
        )
        x = LEFT
        for (_, width, align), cell in zip(COLS, cells, strict=True):
            if align == "r":
                c.right(x + width - 3, y, cell, size=8)
            else:
                c.text(x + 2, y, cell, size=8)
            x += width
        for extra in name_lines[1:]:
            y -= 10
            c.text(LEFT + 24, y, extra, size=8)
        y -= 14
    c.line(LEFT, y + 6, RIGHT, y + 6)
    return y - 6


def _totals(c: TrackedCanvas, doc: DocSpec, y: float, labels: tuple[str, str, str]) -> float:
    for label, name in zip(labels, ("amount_net", "amount_vat", "amount_gross"), strict=True):
        c.right(RIGHT - 110, y, label, size=9, bold=name == "amount_gross")
        _field(c, doc, name, RIGHT, y, size=9, bold=name == "amount_gross", align="right")
        y -= 14
    return y - 4


def _signatures(
    c: TrackedCanvas, doc: DocSpec, rng: random.Random, y: float, left_label: str, right_label: str
) -> None:
    boxes = (("signature_investor", LEFT, left_label), ("signature_contractor", RIGHT - 170, right_label))
    for name, x, label in boxes:
        if name not in doc.values:
            continue
        signed = bool(doc.values[name].value)
        if signed:
            c.signature(x + 5, y, rng)
        c.line(x, y - 2, x + 170, y - 2, width=0.4)
        c.text(x, y - 13, label, size=7.5)
        c.record(name, "", signed, x, y - 4, x + 170, y + 36, doc.values[name].error_id)


def _paragraphs(c: TrackedCanvas, paragraphs: list[str], y: float, size: float = 8.8) -> float:
    for paragraph in paragraphs:
        for line in wrap(paragraph, RIGHT - LEFT, c.regular, size):
            c.text(LEFT, y, line, size=size)
            y -= size * 1.45
        y -= 5
    return y


# --------------------------------------------------------------------------- documents
def _wniosek(c: TrackedCanvas, doc: DocSpec, rng: random.Random) -> None:
    y = PAGE_H - 55
    c.text(LEFT, y, "Program priorytetowy „Czyste Powietrze”", size=9, bold=True)
    c.text(LEFT, y - 12, "Wyciąg z wniosku o dofinansowanie — dane do weryfikacji dokumentacji", size=8)
    y -= 44
    c.text(LEFT, y, "WYCIĄG Z WNIOSKU O DOFINANSOWANIE", size=14, bold=True)
    y -= 26
    _labelled(c, doc, "Numer wniosku:", "application_number", LEFT, y)
    _labelled(c, doc, "Data złożenia wniosku:", "application_date", 320, y)
    y -= 26
    c.text(LEFT, y, "1. Dane wnioskodawcy", size=10, bold=True)
    y -= 16
    _labelled(c, doc, "Imię i nazwisko:", "investor_name", LEFT, y)
    y -= 16
    c.text(LEFT, y, "Adres budynku mieszkalnego jednorodzinnego objętego przedsięwzięciem:")
    y = _address_line(c, doc, LEFT + 10, y - 14)
    y -= 12
    c.text(LEFT, y, "2. Zakres rzeczowy przedsięwzięcia", size=10, bold=True)
    y -= 16
    c.text(LEFT, y, "Źródło ciepła: pompa ciepła typu powietrze-woda")
    y -= 14
    _labelled(c, doc, "Producent:", "product_manufacturer", LEFT + 10, y)
    y -= 14
    _labelled(c, doc, "Model:", "product_model", LEFT + 10, y)
    y -= 14
    _labelled(c, doc, "Moc grzewcza:", "product_power_kw", LEFT + 10, y)
    y -= 26
    c.text(LEFT, y, "3. Planowane koszty kwalifikowane", size=10, bold=True)
    y -= 18
    _totals(c, doc, y, ("Koszty netto:", "VAT:", "Koszty brutto:"))
    c.text(
        LEFT,
        90,
        "Wyciąg wygenerowany z systemu obsługi wniosków. Dokument nie stanowi decyzji o dofinansowaniu.",
        size=7,
    )


def _oferta(c: TrackedCanvas, doc: DocSpec, rng: random.Random) -> None:
    centered = doc.template == "B"
    y = _title(c, doc, "OFERTA", centered)
    _place_date(c, doc, "contract_date", "Data oferty:", y)
    y -= 26
    if doc.template == "A":
        _contractor_block(c, doc, "WYKONAWCA", LEFT, y)
        y = _investor_block(c, doc, "ZAMAWIAJĄCY / INWESTOR", 320, y)
        y -= 30
    else:
        y = _contractor_block(c, doc, "Oferent", LEFT, y)
        y = _investor_block(c, doc, "Dla", LEFT, y - 6)
    y = _paragraphs(
        c,
        [
            "Szanowni Państwo,",
            "w odpowiedzi na zapytanie przedstawiamy ofertę na dostawę i montaż pompy ciepła w budynku "
            "mieszkalnym jednorodzinnym, z uwzględnieniem wymagań programu „Czyste Powietrze”.",
        ],
        y,
    )
    y = _product_line(c, doc, y, "moc grzewcza" if doc.template == "A" else "moc nominalna")
    y = _items_table(c, doc, doc.items, y - 6)
    y = _totals(c, doc, y, ("Razem netto:", "Podatek VAT:", "Razem brutto:"))
    y = _paragraphs(
        c,
        ["Oferta ważna 30 dni od daty sporządzenia. Termin realizacji: do 6 tygodni od akceptacji.", "Z poważaniem"],
        y - 4,
    )
    _signatures(c, doc, rng, max(y - 40, 80), "Akceptacja Zamawiającego", "Wykonawca")


def _umowa(c: TrackedCanvas, doc: DocSpec, rng: random.Random) -> None:
    y = _title(c, doc, "UMOWA", centered=True)
    after = c.text(LEFT, y, "zawarta w dniu ")
    _field(c, doc, "contract_date", after, y)
    y -= 24
    y = _investor_block(c, doc, "pomiędzy Zamawiającym:", LEFT, y)
    y = _contractor_block(c, doc, "a Wykonawcą:", LEFT, y)
    c.text(LEFT, y, "§ 1. Przedmiot umowy", size=10, bold=True)
    y = _paragraphs(
        c,
        [
            "Wykonawca zobowiązuje się do dostawy i montażu pompy ciepła w budynku Zamawiającego "
            "wskazanym powyżej, zgodnie z zestawieniem poniżej."
        ],
        y - 15,
    )
    y = _product_line(c, doc, y, "moc grzewcza")
    c.text(LEFT, y - 6, "§ 2. Wynagrodzenie", size=10, bold=True)
    y = _items_table(c, doc, doc.items, y - 26)
    y = _totals(c, doc, y, ("Wynagrodzenie netto:", "VAT:", "Wynagrodzenie brutto:"))
    c.next_page()
    y = PAGE_H - 60
    y = _paragraphs(
        c,
        [
            "§ 3. Termin realizacji. Wykonawca zakończy prace w terminie 60 dni od dnia zawarcia umowy. "
            "Odbiór końcowy zostanie potwierdzony protokołem odbioru podpisanym przez obie strony.",
            "§ 4. Gwarancja. Wykonawca udziela 24 miesięcy gwarancji na wykonane prace montażowe; gwarancja na "
            "urządzenie zgodnie z kartą gwarancyjną producenta.",
            "§ 5. Zmiany umowy wymagają formy pisemnej w postaci aneksu pod rygorem nieważności.",
            "§ 6. W sprawach nieuregulowanych stosuje się przepisy Kodeksu cywilnego. Umowę sporządzono w dwóch "
            "jednobrzmiących egzemplarzach, po jednym dla każdej ze stron.",
        ],
        y,
    )
    _signatures(c, doc, rng, y - 50, "Zamawiający", "Wykonawca")


def _aneks(c: TrackedCanvas, doc: DocSpec, rng: random.Random) -> None:
    y = _title(c, doc, "ANEKS", centered=True)
    after = c.text(LEFT, y, "do umowy nr ")
    after = _field(c, doc, "related_document_number", after, y)
    after = c.text(after, y, ", sporządzony w dniu ")
    _field(c, doc, "contract_date", after, y)
    y -= 24
    y = _investor_block(c, doc, "Zamawiający:", LEFT, y)
    y = _contractor_block(c, doc, "Wykonawca:", LEFT, y)
    y = _paragraphs(
        c,
        [
            "Strony zgodnie postanawiają zmienić § 1 i § 2 umowy w zakresie urządzenia oraz "
            "wynagrodzenia. Zmiana wynika z niedostępności pierwotnie oferowanego modelu."
        ],
        y,
    )
    y = _product_line(c, doc, y, "moc grzewcza")
    y = _items_table(c, doc, doc.items, y - 6)
    y = _totals(c, doc, y, ("Wynagrodzenie netto po zmianie:", "VAT:", "Wynagrodzenie brutto po zmianie:"))
    y = _paragraphs(c, ["Pozostałe postanowienia umowy pozostają bez zmian."], y)
    _signatures(c, doc, rng, y - 50, "Zamawiający", "Wykonawca")


def _invoice_header(c: TrackedCanvas, doc: DocSpec, title: str) -> float:
    y = _title(c, doc, title, centered=doc.template == "B")
    _place_date(c, doc, "invoice_date", "Data wystawienia:", y)
    if "sale_date" in doc.values:
        _place_date(c, doc, "sale_date", "Data sprzedaży:", y - 13)
    y -= 34
    if doc.template == "A":
        _contractor_block(c, doc, "SPRZEDAWCA", LEFT, y)
        y = _investor_block(c, doc, "NABYWCA", 320, y)
        return y - 30
    y = _contractor_block(c, doc, "Sprzedawca:", LEFT, y)
    return _investor_block(c, doc, "Nabywca (adres inwestycji):", LEFT, y - 4)


def _faktura(c: TrackedCanvas, doc: DocSpec, rng: random.Random) -> None:
    y = _invoice_header(c, doc, "Faktura VAT")
    y = _product_line(c, doc, y, "moc")
    y = _items_table(c, doc, doc.items, y - 4)
    y = _totals(c, doc, y, ("Razem netto:", "Razem VAT:", "Razem brutto:"))
    if "advance_amount" in doc.values:
        after = c.text(LEFT, y, "Zaliczka otrzymana na podstawie faktury ")
        _field(c, doc, "related_document_number", after, y)
        _field(c, doc, "advance_amount", RIGHT, y, align="right")
        y -= 14
        c.right(RIGHT - 110, y, "Pozostało do zapłaty:", bold=True)
        _field(c, doc, "amount_due", RIGHT, y, bold=True, align="right")
        y -= 18
    _paragraphs(
        c,
        [
            "Sposób płatności: przelew, termin płatności 14 dni.",
            "Stawka VAT 8% zgodnie z art. 41 ust. 12 ustawy o VAT (budownictwo objęte społecznym "
            "programem mieszkaniowym).",
        ],
        y - 6,
        size=8,
    )


def _faktura_zaliczkowa(c: TrackedCanvas, doc: DocSpec, rng: random.Random) -> None:
    y = _invoice_header(c, doc, "Faktura zaliczkowa")
    after = c.text(LEFT, y, "Dotyczy umowy nr ")
    _field(c, doc, "related_document_number", after, y)
    y = _items_table(c, doc, doc.items, y - 20)
    _totals(c, doc, y, ("Zaliczka netto:", "VAT:", "Zaliczka brutto:"))


def _faktura_korygujaca(c: TrackedCanvas, doc: DocSpec, rng: random.Random) -> None:
    y = _invoice_header(c, doc, "Faktura korygująca")
    after = c.text(LEFT, y, "Korekta do faktury nr ")
    _field(c, doc, "related_document_number", after, y)
    c.text(LEFT, y - 14, "Przyczyna korekty: rabat udzielony po odbiorze końcowym.")
    y = _items_table(c, doc, doc.items, y - 34)
    _totals(c, doc, y, ("Korekta netto:", "Korekta VAT:", "Korekta brutto:"))


def _protokol(c: TrackedCanvas, doc: DocSpec, rng: random.Random) -> None:
    y = _title(c, doc, "PROTOKÓŁ ODBIORU KOŃCOWEGO", centered=True)
    _labelled(c, doc, "Data odbioru:", "acceptance_date", LEFT, y)
    _labelled(c, doc, "Dotyczy umowy/oferty nr:", "related_document_number", 300, y)
    y -= 26
    c.text(LEFT, y, "Miejsce wykonania prac:", bold=True)
    y = _address_line(c, doc, LEFT, y - 14) - 8
    if doc.template == "A":
        _investor_block(c, doc, "Inwestor:", LEFT, y)
        y = _contractor_block(c, doc, "Wykonawca:", 320, y) - 10
    else:
        y = _investor_block(c, doc, "Inwestor:", LEFT, y)
        y = _contractor_block(c, doc, "Wykonawca:", LEFT, y)
    c.text(LEFT, y, "Zakres odebranych prac:", bold=True)
    y = _product_line(c, doc, y - 16, "moc grzewcza")
    _labelled(c, doc, "Numer seryjny urządzenia:", "serial_number", LEFT, y)
    y = _paragraphs(
        c,
        [
            "Komisja stwierdza, że prace zostały wykonane zgodnie z umową, sztuką budowlaną i dokumentacją "
            "producenta. Instalację uruchomiono i przekazano do eksploatacji. Odbiór bez zastrzeżeń.",
        ],
        y - 22,
    )
    _signatures(c, doc, rng, y - 50, "Inwestor (odbierający)", "Wykonawca (przekazujący)")


def _karta(c: TrackedCanvas, doc: DocSpec, rng: random.Random) -> None:
    y = PAGE_H - 60
    _field(c, doc, "product_manufacturer", LEFT, y, size=16, bold=True)
    c.text(LEFT, y - 18, "KARTA PRODUKTU — pompa ciepła powietrze-woda", size=11, bold=True)
    y -= 50
    rows: list[tuple[str, Callable[[float, float], object]]] = [
        ("Model", lambda x, yy: _field(c, doc, "product_model", x, yy, bold=True)),
        ("Typ urządzenia", lambda x, yy: c.text(x, yy, "pompa ciepła powietrze-woda, monoblok")),
        (
            "Moc grzewcza nominalna (A7/W35)" if doc.template == "A" else "Znamionowa moc cieplna",
            lambda x, yy: _field(c, doc, "product_power_kw", x, yy),
        ),
        ("SCOP (klimat umiarkowany, 35°C)", lambda x, yy: c.text(x, yy, doc.extra["scop"])),
        ("Klasa efektywności energetycznej", lambda x, yy: c.text(x, yy, "A+++")),
        ("Czynnik chłodniczy", lambda x, yy: c.text(x, yy, doc.extra["refrigerant"])),
        ("Pozycja na liście ZUM", lambda x, yy: _field(c, doc, "zum_id", x, yy)),
    ]
    for label, draw in rows:
        c.rect(LEFT, y - 6, RIGHT - LEFT, 20, width=0.3)
        c.text(LEFT + 6, y, label, size=9)
        draw(300, y)
        y -= 20
    _paragraphs(c, ["Dane techniczne według deklaracji producenta. Karta ma charakter informacyjny."], y - 20)


RENDERERS: dict[DocType, Callable[[TrackedCanvas, DocSpec, random.Random], None]] = {
    DocType.WNIOSEK_EKSTRAKT: _wniosek,
    DocType.OFERTA: _oferta,
    DocType.UMOWA: _umowa,
    DocType.ANEKS: _aneks,
    DocType.FAKTURA: _faktura,
    DocType.FAKTURA_ZALICZKOWA: _faktura_zaliczkowa,
    DocType.FAKTURA_KORYGUJACA: _faktura_korygujaca,
    DocType.PROTOKOL_ODBIORU: _protokol,
    DocType.KARTA_PRODUKTU: _karta,
}
