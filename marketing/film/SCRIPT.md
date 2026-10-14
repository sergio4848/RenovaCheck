# Senaryo – seslendirme (PL) ve altyazı (EN)

Kaynak: `script.json`. Zamanlar planlanan değerlerdir. Seslendirme kaydedildikten sonra `script.json`
gerçek zamanlara göre güncellenir, ardından `python3 tools/make_srt.py` ve `python3 tools/make_docs.py`
çalıştırılır.

Toplam konuşma ~48 sn, ~100 kelime (~2,3 kelime/sn, sakin tempo). İngilizce altyazılar ≤ 2 satır,
≤ 42 karakter/satır ve ≤ 17 karakter/sn.

| VO | Çekim | Zaman (sn) | Lehçe seslendirme | İngilizce altyazı |
|---|---|---|---|---|
| VO01 | S01 | 0.5–4.5 | Wniosek. Umowa. Faktura. Protokół odbioru. | Application. Contract. Invoice. Acceptance report. |
| VO02 | S02 | 5.0–9.8 | Każda sprawa to kilka dokumentów – każdy może różnić się jednym znakiem. | Every case means several documents – any of them can differ by one character. |
| VO03 | S03 | 10.2–14.0 | Jedna literówka w modelu – i rozliczenie wraca do poprawki. | One typo in the model – and the settlement goes back for fixes. |
| VO04 | S04 | 14.4–18.2 | RenovaCheck sprawdzi je za Ciebie – zanim zrobi to urząd. | RenovaCheck cross-checks them – before the authority does. |
| VO05 | S05 | 18.6–23.8 | Wgrywasz pliki, a system odczytuje adresy, kwoty, modele, daty i podpisy. | Upload the files – it reads addresses, amounts, models, dates and signatures. |
| VO06 | S06 | 24.0–29.6 | Rozbieżności widzisz od razu – z wagą, uzasadnieniem i regułą, która je wykryła. | Discrepancies appear at once – with severity, reason and rule. |
| VO07 | S07 | 30.0–35.6 | Każde ustalenie wskazuje dokładne miejsce na stronie dokumentu. | Every finding points to the exact spot on the document page. |
| VO08 | S08 | 36.0–40.8 | Decyzję podejmuje człowiek – z komentarzem i pełną historią: kto i kiedy. | A person makes the call – with a comment and a full who-and-when history. |
| VO09 | S09 | 41.2–45.6 | Na koniec raport kontroli – PDF lub CSV, gotowy do akt. | Then a control report – PDF or CSV, ready for the case file. |
| VO10 | S10 | 46.2–50.8 | Mniej ręcznego porównywania. Więcej czasu na klientów. | Less manual cross-checking. More time for your clients. |
| VO11 | S11 | 52.2–55.8 | RenovaCheck. Spójne dokumenty, spokojna głowa. | RenovaCheck. Consistent documents, peace of mind. |

## Ekran metinleri

| Nerede | Lehçe | İngilizce |
|---|---|---|
| S04 logo + slogan | Spójne dokumenty. Spokojna głowa. | Consistent documents. Peace of mind. |
| S06 vurgu | Rozbieżność wykryta | Discrepancy found |
| S07 vurgu | Dowód na stronie dokumentu | Evidence on the page |
| S08 vurgu | Decyzję podejmuje człowiek | A person decides |
| S09 vurgu | Raport kontroli: PDF / CSV | Control report |
| S10 güven etiketleri | Decyzję podejmuje człowiek · Pełna historia: kto i kiedy · Dane organizacji odseparowane | A person decides · Full who-and-when history · Data isolated per organisation |
| S12 kapanış | Spójne dokumenty. Spokojna głowa. · Umów prezentację → · [iletişim satırı] | Consistent documents. Peace of mind. · Book a demo |
| S12 küçük yazı | Prototyp · prezentowane dane są syntetyczne | Prototype · all data shown is synthetic |

**İletişim satırı** (web adresi ya da e-posta) henüz belirlenmedi. Premiere'de metin katmanı
olarak eklenir; uydurma bir adres kullanılmaz.

## Telaffuz notları (ElevenLabs)
- **RenovaCheck:** *re-no-VA-czek* (Lehçe vurgu sondan bir önceki hecede). Yanlış okunursa metinde
  `Renowa Czek` yazımı denenir.
- **PDF / CSV:** harf harf okunur: *pe-de-ef*, *ce-es-fał*.
