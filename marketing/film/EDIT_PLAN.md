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
| V2 | Üst katmanlar: önce animasyonlu giriş (`*_in.mov`, ProRes 4444 alfa), hemen ardından aynı grafiğin durağanı (`*.png`). S04 logo+slogan, S06–S09 kenar notları, S10 numaralı ilkeler |
| V3 | Altyazı (Captions): `subtitles\en.srt` |
| V4 | Opsiyonel: el çizimi halka `gfx\FX_ring_draw.mov` (+ `FX_ring.png` ile tutma), örn. S07'de PH-08B kutusunun etrafına. Kayıtlarda imleç zaten var |
| A1 | Seslendirme `vo\VO01…VO11.wav` |
| A2 | Müzik `music\music.mp3` |
| A3 | Efektler `sfx\*.wav` |

## 3. Çekim çekim yapılacaklar
| Çekim | Hareket / efekt |
|---|---|
| S01 | Siyahtan açılış 12 kare. Kâğıt efekti 0:00'da |
| S02–S03 | Düz kesme. S03'te kalem durduğu an VO03'teki „literówka" kelimesine denk gelsin; gerekirse klibin girişini ±10 kare kaydır |
| S04 | V1 `G04_title_bg.png` (kâğıt, üst/alt mono satırlar). V2 `G04_title_logo_in.mov` (25 kare: çizgi çizilir, logo ve slogan gelir) → `G04_title_logo.png`. Ek hareket yok. 14.2 sn'de whoosh; girişte 8 karelik beyaza dip (Dip to White) |
| S05 | Cross dissolve 8 kare. Scale 100→108 %, tüm çekim boyunca yavaş push-in (anchor üst-orta). 19.6 sn civarı tık sesi, „Wgraj" tıklamasıyla eşleşir |
| S06 | Kenar notu 24.6 sn'de animasyonla girer (`G06_note_discrepancy_in.mov`, 15 kare, kırmızı alt çizgi çizilir), sonra PNG tutar; kesmeden 0.4 sn önce 6 karelik Opacity ile çıkar. Push-in hedefi „krytyczne" satırı |
| S07 | Scale 100→115 %, anchor sol yarı (sayfa görüntüsü), kanıt kutusu vurgusu kadrajda kalsın |
| S08 | Klip zaten 2× hızlı (`UI04_decision_2x.mp4`). Tık sesi radyo seçiminde |
| S09 | „Zamknij sprawę" tıklamasında tık sesi. 44.6 sn'de `UI05_report_p1.png`: kadraja sığdır, sonra Scale 100→112 % (Ken Burns), cross dissolve 6 kare |
| S10 | Cross dissolve 10 kare. 46.4 sn'de kâğıt sütun soldan gelir, üç ilke sırayla belirir (`G10_trust_in.mov`, 40 kare), sonra `G10_trust.png` tutar |
| S11 | Düz kesme; müzik yükselişi burada |
| S12 | Cross dissolve 12 kare. İletişim satırı Essential Graphics metni: Geist Regular 18 px, #5B6470, sola yaslı x=100, y=530 (CTA'nın altı). Son 10 karede siyaha geçiş |

## 4. Renk
- **AI çekimleri:** amaç belgesel gerçekliği; „AI görüntüsü" hissini kırmak.
  - Lumetri ile tek bir ortak görünüm: kontrast +5, doygunluk 90 %, gölgeler hafif soğuk,
    vurgular nötr-sıcak.
  - Sharpen 0 (AI klipleri zaten fazla keskin).
  - Hepsine aynı ince film grain: Noise ~4 % ya da bir 35 mm grain overlay, Overlay modunda
    % 15–20.
  - Gerekirse Seedance çıktısı 24/25 fps'e conform ve hafif motion blur.
  - Aşırı pürüzsüz yüzlere hafif Unsharp yerine grain. Çekimler arası ton farkı *Color Match* ile
  eşitlenir.
- **Arayüz klipleri:** renk düzeltmesi yok (beyaz beyaz kalmalı); yalnızca push-in.
- **Grafikler:** kâğıt (#FAFAF7) ve mürekkep (#111418); renk düzeltmesi uygulanmaz. Grain yalnızca AI çekimlerinde, grafik ve arayüz katmanlarında değil.

## 5. Altyazı (İngilizce, gömülü)
- `subtitles\en.srt` *File → Import* ile Captions izine alınır. Seslendirme kaydedildikten sonra
  zamanlama gerçek sese göre kaydırılır (ya da `script.json` güncellenip `tools/make_srt.py` ile
  yeniden üretilir).
- Stil:
  - Geist Medium 32 px, kâğıt rengi (#FAFAF7), mürekkep (#111418) zeminli düz kutu, % 90
    opaklık, köşe 0 px, iç boşluk 6/12 px. Kâğıt, arayüz ve görüntü üzerinde aynı okunurluk.
  - Alt kenardan 56 px yukarıda, ortalı.
  - En fazla 2 satır.
- Fontlar: `brand/fonts/*.ttf` Windows'a kurulur (sağ tık → Tüm kullanıcılar için yükle), sonra Premiere yeniden başlatılır.

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
