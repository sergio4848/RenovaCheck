"""Regenerate SCRIPT.md and SHOTLIST.md from script.json and shots.json (run after changing either)."""

from __future__ import annotations

import json
from pathlib import Path

FILM = Path(__file__).resolve().parents[1]
KIND = {"ai": "AI (Seedance)", "ui": "Arayüz kaydı", "gfx": "Grafik"}


def script_md(script: dict) -> str:
    rows = "\n".join(
        f"| {l['id']} | {l['shot']} | {l['start']:.1f}–{l['end']:.1f} | {l['pl']} | {l['en']} |"
        for l in script["lines"]
    )
    t, c, p = script["tagline"], script["cta"], script["small_print"]
    return f"""# Senaryo – seslendirme (PL) ve altyazı (EN)

Kaynak: `script.json`. Zamanlar planlanan değerlerdir. Seslendirme kaydedildikten sonra `script.json`
gerçek zamanlara göre güncellenir, ardından `python3 tools/make_srt.py` ve `python3 tools/make_docs.py`
çalıştırılır.

Toplam konuşma ~48 sn, ~100 kelime (~2,3 kelime/sn, sakin tempo). İngilizce altyazılar ≤ 2 satır,
≤ 42 karakter/satır ve ≤ 17 karakter/sn.

| VO | Çekim | Zaman (sn) | Lehçe seslendirme | İngilizce altyazı |
|---|---|---|---|---|
{rows}

## Ekran metinleri

| Nerede | Lehçe | İngilizce |
|---|---|---|
| S04 logo + slogan | {t["pl"]} | {t["en"]} |
| S06 vurgu | Rozbieżność wykryta | Discrepancy found |
| S07 vurgu | Dowód na stronie dokumentu | Evidence on the page |
| S08 vurgu | Decyzję podejmuje człowiek | A person decides |
| S09 vurgu | Raport kontroli: PDF / CSV | Control report |
| S10 güven etiketleri | Decyzję podejmuje człowiek · Pełna historia: kto i kiedy · Dane organizacji odseparowane | A person decides · Full who-and-when history · Data isolated per organisation |
| S12 kapanış | {t["pl"]} · {c["pl"]} → · [iletişim satırı] | {t["en"]} · {c["en"]} |
| S12 küçük yazı | {p["pl"]} | {p["en"]} |

**İletişim satırı** (web adresi ya da e-posta) henüz belirlenmedi. Premiere'de metin katmanı
olarak eklenir; uydurma bir adres kullanılmaz.

## Telaffuz notları (ElevenLabs)
- **RenovaCheck:** *re-no-VA-czek* (Lehçe vurgu sondan bir önceki hecede). Yanlış okunursa metinde
  `Renowa Czek` yazımı denenir.
- **PDF / CSV:** harf harf okunur: *pe-de-ef*, *ce-es-fał*.
"""


def shotlist_md(shots: dict, script: dict) -> str:
    rows = []
    for s in shots["shots"]:
        o = s.get("overlay")
        overlay = f"`{o['build_in']}` → `{o['hold']}` (+{o['offset']:.1f} sn)" if o else "—"
        rows.append(
            f"| {s['id']} | {s['start']:.1f}–{s['end']:.1f} | {s['end'] - s['start']:.1f} | {KIND[s['source']]} | "
            f"`{s['file']}` (in {s['in']:.1f}) | {overlay} | {s['transition_in']} | {s['vo'] or '—'} | {s['note']} |"
        )
    alts = "\n".join(f"- `{a['file']}`: {a['note']}" for a in shots["alternates"])
    return f"""# Çekim listesi

Kaynak: `shots.json` (kurgu XML'i de buradan üretilir). Zamanlar sekans saniyesidir; 25 fps.

| Çekim | Sekans (sn) | Süre | Kaynak | Dosya (`media\\` altında) | Üst katman (V2) | Giriş geçişi | VO | Not |
|---|---|---|---|---|---|---|---|---|
{chr(10).join(rows)}

## Yedek ve ek görüntüler
{alts}

## Dosyaların konumu
- `ui\\`: `marketing/film/ui/*` olduğu gibi.
- `gfx\\`: `marketing/film/graphics/*`.
- `ai\\`: Dreamina'dan indirilen `S01.mp4`, `S02.mp4`, `S03.mp4`, `S10.mp4`, `S11.mp4`.
- `vo\\`, `music\\`, `sfx\\`: ElevenLabs çıktıları (`VOICEOVER.md`).
"""


def main() -> None:
    script = json.loads((FILM / "script.json").read_text())
    shots = json.loads((FILM / "shots.json").read_text())
    (FILM / "SCRIPT.md").write_text(script_md(script))
    (FILM / "SHOTLIST.md").write_text(shotlist_md(shots, script))
    print("SCRIPT.md, SHOTLIST.md")


if __name__ == "__main__":
    main()
