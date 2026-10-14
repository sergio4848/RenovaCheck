# Çekim listesi

Kaynak: `shots.json` (kurgu XML'i de buradan üretilir). Zamanlar sekans saniyesidir; 25 fps.

| Çekim | Sekans (sn) | Süre | Kaynak | Dosya (`media\` altında) | Üst katman (V2) | Giriş geçişi | VO | Not |
|---|---|---|---|---|---|---|---|---|
| S01 | 0.0–5.0 | 5.0 | AI (Seedance) | `ai/S01.mp4` (in 0.0) | — | fade from black 12f | VO01 | Hook: documents spread across the desk |
| S02 | 5.0–10.0 | 5.0 | AI (Seedance) | `ai/S02.mp4` (in 0.0) | — | cut | VO02 | Problem: late-evening cross-checking |
| S03 | 10.0–14.2 | 4.2 | AI (Seedance) | `ai/S03.mp4` (in 0.4) | — | cut | VO03 | Tension: the one-character difference |
| S04 | 14.2–18.4 | 4.2 | Grafik | `gfx/G04_title_bg.png` (in 0.0) | `gfx/G04_logo_transparent.png` | dip to black 8f + whoosh | VO04 | Logo reveal: overlay (logo + tagline) scale 92%->100% and opacity 0->100% over 15f; G04_title_card.png is the finished frame for reference |
| S05 | 18.4–24.0 | 5.6 | Arayüz kaydı | `ui/UI01_upload.mp4` (in 0.6) | — | cross dissolve 8f | VO05 | Upload six PDFs; 108% scale push-in |
| S06 | 24.0–29.5 | 5.5 | Arayüz kaydı | `ui/UI02_findings.mp4` (in 0.0) | `gfx/G06_callout_discrepancy.png` | cut | VO06 | Findings with severity; callout from 25.0 s |
| S07 | 29.5–35.8 | 6.3 | Arayüz kaydı | `ui/UI03_evidence.mp4` (in 0.6) | `gfx/G07_callout_evidence.png` | cut | VO07 | Evidence boxes on the page image; 115% zoom towards the page |
| S08 | 35.8–41.0 | 5.2 | Arayüz kaydı | `ui/UI04_decision_2x.mp4` (in 0.0) | `gfx/G08_callout_decision.png` | cut | VO08 | Decision with comment (already 2x speed) |
| S09 | 41.0–44.6 | 3.6 | Arayüz kaydı | `ui/UI05_close_report.mp4` (in 0.4) | `gfx/G09_callout_report.png` | cut | VO09 | Close the case, download the report |
| S09b | 44.6–46.0 | 1.4 | Arayüz kaydı | `ui/UI05_report_p1.png` (in 0.0) | — | cross dissolve 6f | — | PDF report page 1: scale-to-fit then slow zoom 100%->112% |
| S10 | 46.0–51.0 | 5.0 | AI (Seedance) | `ai/S10.mp4` (in 0.0) | `gfx/G10_trust_chips.png` | cross dissolve 10f | VO10 | Relief: next morning, case handed over; trust chips 46.6-50.6 s |
| S11 | 51.0–56.0 | 5.0 | AI (Seedance) | `ai/S11.mp4` (in 0.0) | — | cut | VO11 | Payoff: house with heat pump, handshake |
| S12 | 56.0–60.0 | 4.0 | Grafik | `gfx/G12_end_card.png` (in 0.0) | — | cross dissolve 12f | — | End card; add contact line as text; fade to black last 10f |

## Yedek ve ek görüntüler
- `ui/UI06_case_list.mp4`: Case list with severity badges: B-roll if an AI shot fails (e.g. under VO02 or VO10)
- `ui/UI02_findings_still.png`: 2x still for push-ins
- `ui/UI03_evidence_still.png`: 2x still, evidence row hovered
- `ui/UI05_closed_still.png`: 2x still, case closed
- `ui/UI05_report_p2.png`: PDF report page 2 (decision history)

## Dosyaların konumu
- `ui\`: `marketing/film/ui/*` olduğu gibi.
- `gfx\`: `marketing/film/graphics/*`.
- `ai\`: Dreamina'dan indirilen `S01.mp4`, `S02.mp4`, `S03.mp4`, `S10.mp4`, `S11.mp4`.
- `vo\`, `music\`, `sfx\`: ElevenLabs çıktıları (`VOICEOVER.md`).
