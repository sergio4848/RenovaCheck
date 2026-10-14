# Premiere Pro kurgu planı

Proje: `renovaCheck`, konum `C:\Users\serge\OneDrive\Documents\Adobe\Premiere Pro\26.0\renovaCheck\`.
Medya: aynı klasörde `media\` (yapı için `SHOTLIST.md`).

## 1. Sekans
| Ayar | Değer |
|---|---|
| Çözünürlük | 1280×720, kare piksel |
| Kare hızı | 25 fps (Polonya/PAL) |
| Ses | 48 kHz, stereo |
| Süre | 00:00:60:00 (1500 kare) |
| Ad | `RenovaCheck_promo_60s` |

**İlk montaj:** `edit\renovacheck_assembly.xml` dosyası *File → Import* ile içe aktarılır. Bu
FCP7 XML'i:
- sekansı;
- V1/V2 ve A1–A3 izlerini;
- her klibin giriş/çıkışını

kurar. Eksik medya „offline" gelir. *Link Media* ile `media\` klasörüne bağlanır; dosya adları
birebir aynıdır.

## 2. İzler
| İz | İçerik |
|---|---|
| V1 | Ana görüntü: AI çekimleri, arayüz klipleri, logo arka planı, kapanış kartı |
| V2 | Üst katmanlar: logo+slogan (S04), vurgu balonları (S06–S09), güven etiketleri (S10) |
| V3 | Altyazı (Captions): `subtitles\en.srt` |
| V4 | Opsiyonel: imleç/halka efektleri (`gfx\FX_*`). Kayıtlarda imleç zaten var; yalnızca vurgu için |
| A1 | Seslendirme `vo\VO01…VO11.wav` |
| A2 | Müzik `music\music.mp3` |
| A3 | Efektler `sfx\*.wav` |

## 3. Çekim çekim yapılacaklar
| Çekim | Hareket / efekt |
|---|---|
| S01 | Siyahtan açılış 12 kare. Kâğıt efekti 0:00'da |
| S02–S03 | Düz kesme. S03'te kalem durduğu an VO03'teki „literówka" kelimesine denk gelsin; gerekirse klibin girişini ±10 kare kaydır |
| S04 | V1 `G04_title_bg.png`; V2 `G04_logo_transparent.png`: Scale 92→100 % ve Opacity 0→100 %, 15 kare, ease-out. 14.2 sn'de whoosh. Girişte 8 karelik siyaha dip |
| S05 | Cross dissolve 8 kare. Scale 100→108 %, tüm çekim boyunca yavaş push-in (anchor üst-orta). 19.6 sn civarı tık sesi, „Wgraj" tıklamasıyla eşleşir |
| S06 | Vurgu balonu 25.0 sn'de girer (Opacity 0→100 %, 8 kare); 0.4 sn önce çıkar. Push-in hedefi „krytyczne" satırı |
| S07 | Scale 100→115 %, anchor sol yarı (sayfa görüntüsü), kanıt kutusu vurgusu kadrajda kalsın |
| S08 | Klip zaten 2× hızlı (`UI04_decision_2x.mp4`). Tık sesi radyo seçiminde |
| S09 | „Zamknij sprawę" tıklamasında tık sesi. 44.6 sn'de `UI05_report_p1.png`: kadraja sığdır, sonra Scale 100→112 % (Ken Burns), cross dissolve 6 kare |
| S10 | Cross dissolve 10 kare. `G10_trust_chips.png` 46.6–50.6 sn |
| S11 | Düz kesme; müzik yükselişi burada |
| S12 | Cross dissolve 12 kare. İletişim satırı Essential Graphics metni olarak eklenir (Inter Bold 24 px, #CFE9E5, logonun 140 px altında, ortalı). Son 10 karede siyaha geçiş |

## 4. Renk
- **AI çekimleri:** Lumetri ile tek bir ortak görünüm. Hafif kontrast (+5), gölgelerde teal
  (Shadow tint), vurgularda amber; doygunluk 95 %. Çekimler arası ton farkı *Color Match* ile
  eşitlenir.
- **Arayüz klipleri:** renk düzeltmesi yok (beyaz beyaz kalmalı); yalnızca push-in.
- **Geçiş:** S04 ve S12 kartlarının lacivert tonu (#0B1F33) AI çekimlerinin gölgeleriyle uyumlu.

## 5. Altyazı (İngilizce, gömülü)
- `subtitles\en.srt` *File → Import* ile Captions izine alınır. Seslendirme kaydedildikten sonra
  zamanlama gerçek sese göre kaydırılır (ya da `script.json` güncellenip `tools/make_srt.py` ile
  yeniden üretilir).
- Stil:
  - Inter SemiBold 30 px, beyaz.
  - Arka plan kutusu #0B1F33 % 70, köşe 6 px, iç boşluk 8/14 px.
  - Alt kenardan 56 px yukarıda, ortalı.
  - En fazla 2 satır.
- S04 ve S12'de ekrandaki metinle çakışırsa altyazı yine altta kalır; kartlar buna göre tasarlandı.

## 6. Ses
| Kanal | Ayar |
|---|---|
| Seslendirme | −16 LUFS (konuşma), Essential Sound → Dialogue; hafif EQ ve de-esser |
| Müzik | Temel −18 dB; konuşma altında −8 dB ducking (Essential Sound → Music → Ducking, kaynak: Dialogue) |
| Efektler | −24 / −30 dB |
| Toplam | −14 LUFS integrated, true peak ≤ −1 dBTP (Loudness Radar ya da export normalizasyonu) |

## 7. Dışa aktarma
| Sürüm | Ayar |
|---|---|
| `RenovaCheck_promo_60s_EN-subs.mp4` | H.264, 1280×720, 25p, VBR 2-pass hedef 8 Mbps / maks 12, AAC 320 kbps 48 kHz, altyazı gömülü (Burn captions into video) |
| `RenovaCheck_promo_60s_clean.mp4` | Aynı ayarlar, altyazısız; yanında `RenovaCheck_promo_60s_EN.srt` (sidecar) |

Thumbnail: `gfx\G04_title_card.png` ya da 0:31'den bir kare (kanıt kutusu).

## 8. Son kontrol
- [ ] 60.0 sn, 1280×720, 25 fps
- [ ] Altyazı ve seslendirme senkron; hiçbir altyazı ekranda 1 sn'den kısa kalmıyor
- [ ] Ekranda okunur gerçek kişi, firma, NIP ya da adres yok; tüm arayüz verisi sentetik
- [ ] „Prototyp · prezentowane dane są syntetyczne" kapanış kartında okunuyor
- [ ] −14 LUFS, true peak ≤ −1 dBTP
- [ ] İki sürüm dışa aktarıldı; proje kaydedildi
