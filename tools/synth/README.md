# renova-synth

Generates synthetic RenovaCheck cases ("sprawy"): Polish documents for one single-family
heat-pump project (application extract, offer or contract, invoice, acceptance protocol,
product card) plus a ground-truth JSON per case with every field value, its page and bounding
box, and the errors that were deliberately injected.

All names, companies, NIP numbers and addresses are fictitious (see docs/ASSUMPTIONS.md B1–B3).

```bash
make synth                      # 20 cases into data/synth/, validated against the schema
renova-synth generate --out data/synth --cases 20 --seed 2026
renova-synth validate data/synth
```

## Output

```
data/synth/
  manifest.json                      counts per document type and injected error type
  SYN-2026-001/
    ground_truth.json                schema: packages/rules/schema/ground_truth.schema.json
    documents/01_wniosek_ekstrakt.pdf
    documents/02_umowa.pdf | 02_oferta.pdf
    documents/03_aneks.pdf           only with agreed_change
    documents/04_faktura_zaliczkowa.pdf, 05_faktura.pdf, 06_faktura_korygujaca.pdf
    documents/07_protokol_odbioru.pdf   absent with missing_protocol
    documents/08_karta_produktu.pdf
```

`ground_truth.json` holds the true facts of the case, every printed field per document
(`text` as printed, canonical `value`, `page`, normalized `bbox` with origin top-left), the
injected errors and the findings a correct reviewer would reach (`outcome`: discrepancy,
match_after_normalization, explained_by_advance, explained_by_correction, agreed_change,
missing_document, unreadable_source).

## Scenarios (seed-independent plan, 20 cases)

| Error type | What changes | Expected outcome |
|---|---|---|
| `address_number_swap` | building number 12 → 21 on the invoice or protocol | discrepancy, critical |
| `street_spelling_variant` | same street written differently (`ul. Tadeusza Kościuszki` / `ul. Kosciuszki`) | match after normalization |
| `model_swap` | model A ↔ B on product card or protocol | discrepancy, critical |
| `power_mismatch` | power +2 kW on offer/contract or invoice | discrepancy, critical |
| `missing_protocol` | no acceptance protocol | missing document, critical |
| `net_gross_confusion` | contract gross prices typed as invoice net prices | discrepancy, warning |
| `advance_payment` | advance invoice + final invoice with "pozostało do zapłaty" | explained by advance |
| `correction_invoice` | correction invoice with a discount | explained by correction |
| `agreed_change` | annex to the contract changes model and power | agreed change, warning |
| `invoice_before_contract` | invoice dated before the contract | discrepancy, warning |
| `missing_signature` | protocol without the investor's signature | discrepancy, critical |
| `low_quality_scan` | 1–2 documents as noisy, skewed image-only scans | unreadable source (measured, no threshold) |

Three cases stay clean to measure false positives. Each document type has two layouts (A/B),
two font families, three money formats and two date formats.

Output is byte-for-byte reproducible for a given seed (`invariant` PDFs, seeded noise, fixed
PDF dates), on the host and in the container.
