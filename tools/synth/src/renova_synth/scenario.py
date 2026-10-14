"""Plans one case: true facts, the documents to render and the errors injected into them.

The plan is pure data; rendering happens in renova_synth.render. Every random choice comes from
a Random seeded with (seed, case number), so a case is reproducible on its own.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from renova_synth import data
from renova_synth.model import (
    CaseFacts,
    DocType,
    ErrorType,
    ExpectedFinding,
    InjectedError,
    NormalizedValue,
    Outcome,
    RuleFamily,
    Severity,
)
from renova_synth.money import LineItem, Totals, format_kw, format_pln, money, totals

E = ErrorType

# Scenario mix for 20 cases: every error type appears at least once, most twice, and three cases
# stay clean so false positives can be measured. Extra invoices (advance or correction) occur in
# 6 of 20 cases (30%).
SCENARIO_PLAN: tuple[tuple[ErrorType, ...], ...] = (
    (),
    (E.ADDRESS_NUMBER_SWAP,),
    (E.STREET_SPELLING_VARIANT,),
    (E.MODEL_SWAP,),
    (E.POWER_MISMATCH,),
    (E.MISSING_PROTOCOL,),
    (E.NET_GROSS_CONFUSION,),
    (E.ADVANCE_PAYMENT,),
    (E.AGREED_CHANGE,),
    (E.LOW_QUALITY_SCAN,),
    (E.ADDRESS_NUMBER_SWAP, E.LOW_QUALITY_SCAN),
    (E.STREET_SPELLING_VARIANT, E.MODEL_SWAP, E.CORRECTION_INVOICE),
    (E.POWER_MISMATCH, E.MISSING_SIGNATURE),
    (E.MISSING_PROTOCOL, E.ADVANCE_PAYMENT),
    (E.NET_GROSS_CONFUSION, E.LOW_QUALITY_SCAN),
    (E.ADVANCE_PAYMENT, E.STREET_SPELLING_VARIANT),
    (E.AGREED_CHANGE, E.LOW_QUALITY_SCAN),
    (E.CORRECTION_INVOICE,),
    (E.INVOICE_BEFORE_CONTRACT,),
    (E.CORRECTION_INVOICE, E.ADDRESS_NUMBER_SWAP),
)
# Building numbers whose digits can be transposed into a different, plausible number.
SWAPPABLE_NUMBERS = ("12", "13", "14", "17", "23", "25", "27", "34", "38", "45", "46", "58", "67")


@dataclass(frozen=True)
class Value:
    text: str
    value: NormalizedValue
    error_id: str | None = None


@dataclass
class DocSpec:
    doc_id: str
    doc_type: DocType
    issue_date: date
    number: str
    template: str
    font_family: str
    values: dict[str, Value] = field(default_factory=dict)
    items: list[LineItem] = field(default_factory=list)
    item_error: str | None = None
    money_style: int = 0
    kw_style: int = 0
    scan: bool = False
    extra: dict[str, str] = field(default_factory=dict)

    def put(self, name: str, text: str, value: NormalizedValue, error_id: str | None = None) -> None:
        self.values[name] = Value(text, value, error_id)


@dataclass
class CasePlan:
    case_id: str
    seed: int
    contract_kind: str
    scenario: tuple[ErrorType, ...]
    facts: CaseFacts
    documents: list[DocSpec]
    errors: list[InjectedError]
    findings: list[ExpectedFinding]


@dataclass(frozen=True)
class _Base:
    investor: str
    street_key: str
    building_no: str
    postal: str
    city: str
    contractor: str
    nip: str
    pump: data.HeatPump
    items: tuple[LineItem, ...]
    application_date: date
    contract_date: date
    acceptance_date: date
    invoice_date: date


def plan_case(seed: int, number: int) -> CasePlan:
    rng = random.Random(f"{seed}-{number}")
    scenario = SCENARIO_PLAN[(number - 1) % len(SCENARIO_PLAN)]
    case_id = f"SYN-{seed:04d}-{number:03d}"
    base = _base(rng)
    contract_kind = (
        "umowa" if {E.AGREED_CHANGE, E.INVOICE_BEFORE_CONTRACT} & set(scenario) else rng.choice(["oferta", "umowa"])
    )
    builder = _Builder(rng, case_id, base, contract_kind, scenario)
    return builder.build(seed)


def _base(rng: random.Random) -> _Base:
    pump = data.heat_pump(rng)
    city, _gmina = rng.choice(data.LOCALITIES)
    pump_price = money(Decimal(rng.randint(240, 460)) * 100 + Decimal(rng.choice([0, 50, 90])))
    items = [
        LineItem(
            f"Pompa ciepła powietrze-woda {pump.manufacturer} {pump.model('A')}",
            Decimal(1),
            "szt.",
            pump_price,
            8,
        ),
        LineItem("Montaż i uruchomienie instalacji", Decimal(1), "kpl.", money(Decimal(rng.randint(40, 90)) * 100), 8),
    ]
    if rng.random() < 0.5:
        items.append(
            LineItem("Zasobnik c.w.u. 200 l", Decimal(1), "szt.", money(Decimal(rng.randint(28, 45)) * 100), 8)
        )
    if rng.random() < 0.35:
        items.append(
            LineItem(
                "Przegląd serwisowy (pierwszy rok)", Decimal(1), "usł.", money(Decimal(rng.randint(4, 9)) * 100), 23
            )
        )
    application = date(2026, 1, 5) + timedelta(days=rng.randint(0, 150))
    contract = application + timedelta(days=rng.randint(7, 25))
    acceptance = contract + timedelta(days=rng.randint(20, 60))
    invoice = acceptance + timedelta(days=rng.randint(0, 6))
    return _Base(
        investor=data.person_name(rng),
        street_key=rng.choice(sorted(data.STREETS)),
        building_no=rng.choice(SWAPPABLE_NUMBERS),
        postal=data.postal_code(rng),
        city=city,
        contractor=data.company_name(rng),
        nip=data.nip(rng),
        pump=pump,
        items=tuple(items),
        application_date=application,
        contract_date=contract,
        acceptance_date=acceptance,
        invoice_date=invoice,
    )


def _iso(d: date) -> str:
    return d.isoformat()


def _pl_date(d: date, style: int) -> str:
    return d.strftime("%d.%m.%Y") if style == 0 else d.isoformat()


class _Builder:
    def __init__(
        self,
        rng: random.Random,
        case_id: str,
        base: _Base,
        contract_kind: str,
        scenario: tuple[ErrorType, ...],
    ) -> None:
        self.rng = rng
        self.case_id = case_id
        self.base = base
        self.contract_kind = contract_kind
        self.scenario = scenario
        self.docs: list[DocSpec] = []
        self.errors: list[InjectedError] = []
        self.findings: list[ExpectedFinding] = []
        self.contractor_font = rng.choice(["sans", "liberation"])
        self.money_style = rng.choice([0, 0, 1, 2])
        self.date_style = rng.choice([0, 0, 1])
        self.street_variant = rng.choice([0, 1, 2])
        self.nip_style = rng.choice([0, 1])
        self.serial = f"SN{rng.randint(10**7, 10**8 - 1)}"
        self.zum_id = f"ZUM/PC/{rng.randint(1000, 9999)}"

    # ------------------------------------------------------------------ helpers
    def _doc_id(self) -> str:
        return f"{self.case_id}-D{len(self.docs) + 1}"

    def _error(
        self,
        kind: ErrorType,
        doc: DocSpec | None,
        field_name: str | None,
        true_value: NormalizedValue,
        written: NormalizedValue,
        description: str,
    ) -> str:
        error_id = f"{self.case_id}-E{len(self.errors) + 1}"
        self.errors.append(
            InjectedError(
                error_id=error_id,
                type=kind,
                doc_id=doc.doc_id if doc else None,
                field=field_name,
                true_value=true_value,
                written_value=written,
                description_pl=description,
            )
        )
        return error_id

    def _finding(
        self,
        error_id: str,
        family: RuleFamily,
        outcome: Outcome,
        severity: Severity,
        fields: tuple[str, ...],
        docs: list[DocSpec],
    ) -> None:
        self.findings.append(
            ExpectedFinding(
                error_id=error_id,
                family=family,
                outcome=outcome,
                severity=severity,
                fields=fields,
                doc_ids=tuple(d.doc_id for d in docs),
            )
        )

    def _new(self, doc_type: DocType, issue: date, number: str, font: str) -> DocSpec:
        doc = DocSpec(
            doc_id=self._doc_id(),
            doc_type=doc_type,
            issue_date=issue,
            number=number,
            template=self.rng.choice(["A", "B"]),
            font_family=font,
            money_style=self.money_style,
            kw_style=self.rng.choice([0, 1]),
        )
        self.docs.append(doc)
        return doc

    def _address(self, doc: DocSpec, variant: int | None = None) -> None:
        b = self.base
        spelling = data.STREETS[b.street_key][self.street_variant if variant is None else variant]
        doc.put("address_street", spelling, b.street_key)
        doc.put("address_building_no", b.building_no, b.building_no)
        doc.put("address_postal_code", b.postal, b.postal)
        doc.put("address_city", b.city, b.city)

    def _investor(self, doc: DocSpec) -> None:
        doc.put("investor_name", self.base.investor, self.base.investor)

    def _contractor(self, doc: DocSpec) -> None:
        b = self.base
        doc.put("contractor_name", b.contractor, b.contractor)
        doc.put("contractor_nip", data.format_nip(b.nip, self.nip_style), b.nip)

    def _product(self, doc: DocSpec, variant: str = "A", power: int | None = None) -> None:
        pump = self.base.pump
        kw = power if power is not None else pump.power_kw
        doc.put("product_manufacturer", pump.manufacturer, pump.manufacturer)
        doc.put("product_model", pump.model(variant, kw), pump.model(variant, kw))
        doc.put("product_power_kw", format_kw(kw, doc.kw_style), float(kw))

    def _amounts(self, doc: DocSpec, t: Totals) -> None:
        style = doc.money_style
        doc.put("amount_net", format_pln(t.net, style), float(t.net))
        doc.put("amount_vat", format_pln(t.vat, style), float(t.vat))
        doc.put("amount_gross", format_pln(t.gross, style), float(t.gross))

    def _date(self, doc: DocSpec, name: str, d: date) -> None:
        doc.put(name, _pl_date(d, self.date_style), _iso(d))

    # ------------------------------------------------------------------ build
    def build(self, seed: int) -> CasePlan:
        b = self.base
        s = set(self.scenario)
        items = list(b.items)
        base_totals = totals(items)

        # Agreed change: an annex replaces the model by its B variant with 2 kW more power.
        changed = E.AGREED_CHANGE in s
        new_power = b.pump.power_kw + 2
        variant_after = "B" if changed else "A"
        power_after = new_power if changed else b.pump.power_kw
        items_after = items
        if changed:
            delta = money(Decimal(self.rng.randint(15, 35)) * 100)
            items_after = [
                LineItem(
                    f"Pompa ciepła powietrze-woda {b.pump.manufacturer} {b.pump.model('B', new_power)}",
                    items[0].quantity,
                    items[0].unit,
                    items[0].unit_net + delta,
                    items[0].vat_rate,
                ),
                *items[1:],
            ]
        model_after = b.pump.model(variant_after, power_after)

        # 1. Application extract (issued by the programme operator).
        app = self._new(
            DocType.WNIOSEK_EKSTRAKT,
            b.application_date,
            f"CP/{b.application_date.year}/{self.rng.randint(10000, 99999)}",
            "sans",
        )
        self._investor(app)
        self._address(app, variant=0)
        self._product(app)
        app.put("application_number", app.number, app.number)
        self._date(app, "application_date", b.application_date)
        self._amounts(app, base_totals)

        # 2. Offer or contract.
        kind = DocType.UMOWA if self.contract_kind == "umowa" else DocType.OFERTA
        prefix = "UM" if kind is DocType.UMOWA else "OF"
        con = self._new(
            kind, b.contract_date, f"{prefix}/{b.contract_date.year}/{self.rng.randint(100, 999)}", self.contractor_font
        )
        con.items = items
        self._investor(con)
        self._address(con)
        self._contractor(con)
        self._product(con)
        self._amounts(con, base_totals)
        self._date(con, "contract_date", b.contract_date)
        con.put("signature_investor", "", kind is DocType.UMOWA)
        con.put("signature_contractor", "", True)

        annex: DocSpec | None = None
        if changed:
            annex_date = b.contract_date + timedelta(days=self.rng.randint(5, 15))
            annex = self._new(DocType.ANEKS, annex_date, f"{con.number}/A1", self.contractor_font)
            annex.items = items_after
            self._investor(annex)
            self._address(annex)
            self._contractor(annex)
            annex.put("product_manufacturer", b.pump.manufacturer, b.pump.manufacturer)
            annex.put("product_model", model_after, model_after)
            annex.put("product_power_kw", format_kw(power_after, annex.kw_style), float(power_after))
            self._amounts(annex, totals(items_after))
            annex.put("related_document_number", con.number, con.number)
            self._date(annex, "contract_date", annex_date)
            annex.put("signature_investor", "", True)
            annex.put("signature_contractor", "", True)

        final_totals = totals(items_after)

        # 3a. Advance invoice before the final invoice.
        advance_doc: DocSpec | None = None
        advance_gross = Decimal(0)
        if E.ADVANCE_PAYMENT in s:
            adv_date = b.contract_date + timedelta(days=self.rng.randint(2, 10))
            advance_doc = self._new(
                DocType.FAKTURA_ZALICZKOWA,
                adv_date,
                f"FZ/{self.rng.randint(1, 99)}/{adv_date.month:02d}/{adv_date.year}",
                self.contractor_font,
            )
            share = Decimal(self.rng.choice([20, 30, 40])) / 100
            adv_item = LineItem(
                f"Zaliczka na poczet umowy {con.number}",
                Decimal(1),
                "usł.",
                money(final_totals.gross * share / Decimal("1.08")),
                8,
            )
            advance_doc.items = [adv_item]
            adv_totals = totals([adv_item])
            advance_gross = adv_totals.gross
            self._investor(advance_doc)
            self._address(advance_doc)
            self._contractor(advance_doc)
            self._amounts(advance_doc, adv_totals)
            self._date(advance_doc, "invoice_date", adv_date)
            advance_doc.put("related_document_number", con.number, con.number)

        # 3b. Final invoice.
        inv_date = b.invoice_date
        if E.INVOICE_BEFORE_CONTRACT in s:
            inv_date = b.contract_date - timedelta(days=self.rng.randint(3, 12))
        inv = self._new(
            DocType.FAKTURA,
            inv_date,
            f"FV/{self.rng.randint(1, 250)}/{inv_date.month:02d}/{inv_date.year}",
            self.contractor_font,
        )
        inv.items = items_after
        self._investor(inv)
        self._address(inv)
        self._contractor(inv)
        self._product(inv, variant_after, power_after)
        inv_totals = final_totals
        self._date(inv, "invoice_date", inv_date)
        self._date(inv, "sale_date", b.acceptance_date if inv_date >= b.acceptance_date else inv_date)

        # 4. Acceptance protocol (unless missing).
        proto: DocSpec | None = None
        if E.MISSING_PROTOCOL not in s:
            proto = self._new(
                DocType.PROTOKOL_ODBIORU,
                b.acceptance_date,
                f"PO/{self.rng.randint(1, 300)}/{b.acceptance_date.year}",
                self.contractor_font,
            )
            self._investor(proto)
            self._address(proto)
            self._contractor(proto)
            self._product(proto, variant_after, power_after)
            proto.put("serial_number", self.serial, self.serial)
            self._date(proto, "acceptance_date", b.acceptance_date)
            proto.put("related_document_number", con.number, con.number)
            proto.put("signature_investor", "", True)
            proto.put("signature_contractor", "", True)

        # 5. Product card (manufacturer).
        card = self._new(
            DocType.KARTA_PRODUKTU,
            b.application_date - timedelta(days=self.rng.randint(60, 400)),
            self.zum_id,
            "liberation" if self.contractor_font == "sans" else "sans",
        )
        card.put("product_manufacturer", b.pump.manufacturer, b.pump.manufacturer)
        card.put("product_model", model_after, model_after)
        card.put("product_power_kw", format_kw(power_after, card.kw_style), float(power_after))
        card.put("zum_id", self.zum_id, self.zum_id)
        card.extra["scop"] = f"{self.rng.uniform(3.6, 4.9):.2f}".replace(".", ",")
        card.extra["refrigerant"] = self.rng.choice(["R32", "R290"])

        # 3c. Correction invoice after the final invoice.
        corr: DocSpec | None = None
        if E.CORRECTION_INVOICE in s:
            corr_date = inv_date + timedelta(days=self.rng.randint(3, 20))
            corr = self._new(
                DocType.FAKTURA_KORYGUJACA,
                corr_date,
                f"FK/{self.rng.randint(1, 60)}/{corr_date.month:02d}/{corr_date.year}",
                self.contractor_font,
            )
            discount = LineItem(
                "Rabat udzielony po odbiorze (korekta ceny pompy ciepła)",
                Decimal(1),
                "usł.",
                -money(Decimal(self.rng.randint(5, 20)) * 100),
                8,
            )
            corr.items = [discount]
            corr_totals = totals([discount])
            self._investor(corr)
            self._address(corr)
            self._contractor(corr)
            self._amounts(corr, corr_totals)
            self._date(corr, "invoice_date", corr_date)
            corr.put("related_document_number", inv.number, inv.number)

        # Invoice amounts, possibly with net/gross confusion.
        if E.NET_GROSS_CONFUSION in s:
            # Each row's gross price from the contract is typed in as the net price.
            inv.items = [
                LineItem(i.name, i.quantity, i.unit, money(i.gross / i.quantity), i.vat_rate) for i in items_after
            ]
            inv_totals = totals(inv.items)
        self._amounts(inv, inv_totals)
        if advance_doc is not None:
            due = inv_totals.gross - advance_gross
            inv.put("advance_amount", format_pln(advance_gross, inv.money_style), float(advance_gross))
            inv.put("amount_due", format_pln(due, inv.money_style), float(due))
            inv.put("related_document_number", advance_doc.number, advance_doc.number)

        self._inject(s, app, con, annex, inv, proto, card, advance_doc, corr, final_totals)
        facts = CaseFacts(
            investor_name=b.investor,
            address_street=b.street_key,
            address_building_no=b.building_no,
            address_postal_code=b.postal,
            address_city=b.city,
            contractor_name=b.contractor,
            contractor_nip=b.nip,
            product_manufacturer=b.pump.manufacturer,
            product_model=model_after,
            product_power_kw=float(power_after),
            amount_net=float(final_totals.net),
            amount_vat=float(final_totals.vat),
            amount_gross=float(final_totals.gross),
            application_date=b.application_date,
            contract_date=b.contract_date,
            acceptance_date=b.acceptance_date,
            invoice_date=inv_date,
        )
        return CasePlan(
            self.case_id, seed, self.contract_kind, self.scenario, facts, self.docs, self.errors, self.findings
        )

    # ------------------------------------------------------------------ errors
    def _inject(
        self,
        s: set[ErrorType],
        app: DocSpec,
        con: DocSpec,
        annex: DocSpec | None,
        inv: DocSpec,
        proto: DocSpec | None,
        card: DocSpec,
        advance_doc: DocSpec | None,
        corr: DocSpec | None,
        final_totals: Totals,
    ) -> None:
        b = self.base
        rng = self.rng

        if E.ADDRESS_NUMBER_SWAP in s:
            target = rng.choice([d for d in (inv, proto) if d is not None])
            swapped = b.building_no[::-1]
            eid = self._error(
                E.ADDRESS_NUMBER_SWAP,
                target,
                "address_building_no",
                b.building_no,
                swapped,
                f"Numer domu {b.building_no} zapisany jako {swapped}.",
            )
            target.put("address_building_no", swapped, swapped, eid)
            self._finding(
                eid, RuleFamily.ADDRESS, Outcome.DISCREPANCY, Severity.CRITICAL, ("address_building_no",), [app, target]
            )

        if E.STREET_SPELLING_VARIANT in s:
            target = rng.choice([con, inv])
            variant = 3
            spelling = data.STREETS[b.street_key][variant]
            eid = self._error(
                E.STREET_SPELLING_VARIANT,
                target,
                "address_street",
                b.street_key,
                b.street_key,
                f"Ta sama ulica zapisana w innej formie: „{spelling}”.",
            )
            target.put("address_street", spelling, b.street_key, eid)
            self._finding(
                eid,
                RuleFamily.ADDRESS,
                Outcome.MATCH_AFTER_NORMALIZATION,
                Severity.INFO,
                ("address_street",),
                [app, target],
            )

        if E.MODEL_SWAP in s:
            target = rng.choice([d for d in (card, proto) if d is not None])
            right = target.values["product_model"].value
            wrong = str(right)[:-1] + ("B" if str(right).endswith("A") else "A")
            eid = self._error(
                E.MODEL_SWAP, target, "product_model", right, wrong, f"Model {right} zamieniony na {wrong}."
            )
            target.put("product_model", wrong, wrong, eid)
            self._finding(
                eid, RuleFamily.PRODUCT, Outcome.DISCREPANCY, Severity.CRITICAL, ("product_model",), [con, target]
            )

        if E.POWER_MISMATCH in s:
            target = rng.choice([con, inv])
            right_kw = float(b.pump.power_kw)
            wrong_kw = right_kw + 2
            eid = self._error(
                E.POWER_MISMATCH,
                target,
                "product_power_kw",
                right_kw,
                wrong_kw,
                f"Moc {right_kw:g} kW zapisana jako {wrong_kw:g} kW.",
            )
            target.put("product_power_kw", format_kw(wrong_kw, target.kw_style), wrong_kw, eid)
            self._finding(
                eid,
                RuleFamily.PRODUCT,
                Outcome.DISCREPANCY,
                Severity.CRITICAL,
                ("product_power_kw",),
                [app, card, target],
            )

        if E.MISSING_PROTOCOL in s:
            eid = self._error(
                E.MISSING_PROTOCOL, None, None, True, False, "Brak protokołu odbioru w dokumentacji sprawy."
            )
            self._finding(eid, RuleFamily.COMPLETENESS, Outcome.MISSING_DOCUMENT, Severity.CRITICAL, (), [])

        if E.NET_GROSS_CONFUSION in s:
            eid = self._error(
                E.NET_GROSS_CONFUSION,
                inv,
                "amount_net",
                float(final_totals.net),
                inv.values["amount_net"].value,
                "Kwota brutto z oferty/umowy wpisana na fakturze jako kwota netto.",
            )
            v = inv.values["amount_net"]
            inv.put("amount_net", v.text, v.value, eid)
            inv.item_error = eid
            self._finding(
                eid,
                RuleFamily.AMOUNT,
                Outcome.DISCREPANCY,
                Severity.WARNING,
                ("amount_net", "amount_gross"),
                [con, inv],
            )

        if E.ADVANCE_PAYMENT in s and advance_doc is not None:
            eid = self._error(
                E.ADVANCE_PAYMENT,
                inv,
                "amount_due",
                float(final_totals.gross),
                inv.values["amount_due"].value,
                "Kwota do zapłaty pomniejszona o zaliczkę z faktury zaliczkowej.",
            )
            self._finding(
                eid,
                RuleFamily.AMOUNT,
                Outcome.EXPLAINED_BY_ADVANCE,
                Severity.INFO,
                ("amount_due", "advance_amount"),
                [con, advance_doc, inv],
            )

        if E.CORRECTION_INVOICE in s and corr is not None:
            corrected = float(final_totals.gross) + float(corr.values["amount_gross"].value or 0)
            eid = self._error(
                E.CORRECTION_INVOICE,
                corr,
                "amount_gross",
                float(final_totals.gross),
                round(corrected, 2),
                "Faktura korygująca obniża kwotę faktury (rabat).",
            )
            self._finding(
                eid,
                RuleFamily.AMOUNT,
                Outcome.EXPLAINED_BY_CORRECTION,
                Severity.INFO,
                ("amount_gross",),
                [con, inv, corr],
            )

        if E.AGREED_CHANGE in s and annex is not None:
            eid = self._error(
                E.AGREED_CHANGE,
                annex,
                "product_model",
                b.pump.model("A"),
                annex.values["product_model"].value,
                "Aneks do umowy zmienia model i moc pompy ciepła.",
            )
            self._finding(
                eid,
                RuleFamily.PRODUCT,
                Outcome.AGREED_CHANGE,
                Severity.WARNING,
                ("product_model", "product_power_kw"),
                [con, annex, inv],
            )

        if E.INVOICE_BEFORE_CONTRACT in s:
            eid = self._error(
                E.INVOICE_BEFORE_CONTRACT,
                inv,
                "invoice_date",
                b.invoice_date.isoformat(),
                inv.values["invoice_date"].value,
                "Faktura wystawiona przed datą zawarcia umowy.",
            )
            v = inv.values["invoice_date"]
            inv.put("invoice_date", v.text, v.value, eid)
            self._finding(
                eid,
                RuleFamily.COMPLETENESS,
                Outcome.DISCREPANCY,
                Severity.WARNING,
                ("invoice_date", "contract_date"),
                [con, inv],
            )

        if E.MISSING_SIGNATURE in s and proto is not None:
            eid = self._error(
                E.MISSING_SIGNATURE,
                proto,
                "signature_investor",
                True,
                False,
                "Brak podpisu inwestora na protokole odbioru.",
            )
            proto.put("signature_investor", "", False, eid)
            self._finding(
                eid, RuleFamily.COMPLETENESS, Outcome.DISCREPANCY, Severity.CRITICAL, ("signature_investor",), [proto]
            )

        if E.LOW_QUALITY_SCAN in s:
            candidates = [d for d in (inv, proto, con) if d is not None]
            for target in rng.sample(candidates, k=min(2, len(candidates))):
                target.scan = True
                eid = self._error(
                    E.LOW_QUALITY_SCAN,
                    target,
                    None,
                    None,
                    None,
                    "Dokument dostępny tylko jako słabej jakości skan (szum, pochylenie).",
                )
                self._finding(eid, RuleFamily.NONE, Outcome.UNREADABLE_SOURCE, Severity.INFO, (), [target])
