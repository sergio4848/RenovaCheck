# ElevenLabs – seslendirme, müzik ve efektler

## Seslendirme (Lehçe)
**Ses seçimi:** Voice Library'de dil filtresi *Polish*.
- **Ara:** anadili Lehçe, 30–45 yaş, sıcak ve güven veren, orta tempo; „narration / commercial"
  etiketli bir ses. Kadın ya da erkek fark etmez; filmin karakteri Marta olduğu için sıcak bir
  kadın sesi önerilir.
- **Kaçın:** aşırı „reklam spikeri", nefesli/fısıltılı ya da yabancı aksanlı sesler.
- **Seçim yöntemi:** 2–3 adayla VO04'ü (marka adı geçen satır) deneyip en doğal „RenovaCheck"
  telaffuzunu seç.

**Model ve ayarlar**
| Ayar | Değer |
|---|---|
| Model | Eleven Multilingual v2 (tutarlılık); v3 daha canlıysa o, ama tüm segmentler aynı modelle |
| Stability | 50 % |
| Similarity | 75 % |
| Style exaggeration | 10–20 % |
| Speaker boost | açık |
| Speed | 1.0 (segment süreye sığmazsa 0.95–1.08 arası) |
| Çıktı | WAV 48 kHz varsa, yoksa MP3 44.1 kHz 192 kbps |

**Segmentler:** her satır ayrı üretilir ve `media\vo\VO01.wav` … `VO11.wav` olarak kaydedilir.
Metinler `SCRIPT.md`'deki tabloda; aynen kopyalanır, tırnak ve tireler dahil.

| Segment | Hedef süre (sn) | Not |
|---|---|---|
| VO01 | 4.0 | Dört kelime, her biri ayrı ve vurgulu; aralarda kısa duraklar |
| VO02 | 4.8 | Tireden sonra hafif yavaşla |
| VO03 | 3.8 | „literówka" vurgulu, sonda hafif düşüş |
| VO04 | 3.8 | Dönüm noktası: daha aydınlık ve kendinden emin |
| VO05–VO09 | 4.4–5.6 | Akıcı, açıklayıcı, gülümseyen ton |
| VO10 | 4.6 | İki kısa cümle, rahatlamış |
| VO11 | 3.6 | Slogan: yavaş, sıcak, kapanış |

**Telaffuz:** „RenovaCheck" = *re-no-VA-czek*. Yanlış okunursa metinde `Renowa Czek` yazımı ya da
bir pronunciation dictionary alias'ı kullanılır. PDF = *pe-de-ef*, CSV = *ce-es-fał*.

**Hedef süreye uydurma:** segment hedeften > %10 uzunsa önce speed 1.05, sonra metindeki tireleri
virgüle çevir. Kısaysa sorun yok, kurgu boşluğu müzikle dolar.

## Müzik (opsiyonel: ElevenLabs Music)
**Prompt**
> 60-second warm modern corporate underscore for a B2B software film, no vocals, 96 BPM. 0–14 s: minimal and slightly tense, a single soft piano motif over a muted pulse. At 14 s a gentle lift with soft plucked synths and light percussion (logo reveal). 18–46 s: steady, confident, optimistic groove that stays under a voice-over. From 46 s: uplifting resolve with warm pads, final cadence at 56–60 s ending cleanly on the last beat.

Dosya: `media\music\music.mp3`. Alternatif: Premiere/Adobe Stock lisanslı bir parça (lisans
notu `PRODUCTION.md`'ye yazılır).

## Efektler (ElevenLabs Sound Effects)
| Dosya | Prompt | Nerede |
|---|---|---|
| `media\sfx\paper.wav` | soft paper shuffle, several sheets sliding on a wooden desk, close, quiet room | S01 (0:00) |
| `media\sfx\whoosh.wav` | soft cinematic whoosh with a subtle shimmer, short, clean tail | S04 logo (0:14.2) |
| `media\sfx\click.wav` | soft modern UI click, short, muted, no reverb | 19.6 s, 37.3 s ve 41.6 s civarı tıklamalar |

Efekt seviyeleri düşük tutulur (−24 ile −30 dB); konuşmanın önüne geçmez.
