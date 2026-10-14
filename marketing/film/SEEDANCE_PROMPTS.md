# Dreamina · Seedance 2.5 – AI çekimleri

Filmde 5 AI çekimi var: S01, S02, S03, S10, S11. Ürün arayüzü hiçbir zaman AI ile üretilmez;
arayüz `ui/` klasöründeki gerçek kayıtlardan gelir.

## Ayarlar (her çekim için aynı)
| Ayar | Değer |
|---|---|
| Model | Seedance 2.5 |
| Oran | 16:9 |
| Çözünürlük | 720p |
| Süre | 5 sn |
| Ses | kapalı (seslendirme, müzik ve efekt kurguda eklenir) |
| Kamera hareketi | prompt'ta yazılı; varsa „kamera kontrolü" otomatik |
| Referans | `REF_marta.png` (aşağıda): S02, S03 (el), S10. S01 ve S11 referanssız |

Dosya adları: indirilen klipler `S01.mp4`, `S02.mp4`, … olarak `media\ai\` klasörüne konur.

## Kredi bütçesi (7185 kredi mevcut)
Dreamina'nın Seedance 2.5 720p oranı bu hazırlık sırasında resmi olarak doğrulanamadı. Kaynaklarda
saniyede ~26–37 kredi geçiyor; **gerçek oran her üretimden önce arayüzdeki maliyet etiketinden
okunur.**

| Kalem | Adet | Tahmini kredi |
|---|---|---|
| Karakter referans görseli (Seedream) | 2–4 görsel | düşük (görsel başına arayüzde gösterilen) |
| AI çekim, 1. deneme | 5 × 5 sn | 650–925 |
| AI çekim, 2. deneme (gerekenler) | 5 × 5 sn | 650–925 |
| **Plan toplamı** | | **~1.300–1.850** |
| Üst sınır (yeniden denemeler dahil) | | **3.500** |
| Yedek (dokunulmaz) | | ~3.600 |

**Durma kuralları**
- Bir çekim için en fazla 3 deneme yapılır. Hâlâ olmuyorsa aynı fikrin daha sade bir varyantı
  denenir ya da `ui/UI06_case_list.mp4` B-roll olarak kullanılır.
- Toplam harcama 3.500 krediye ulaşınca üretim durur ve kullanıcıya sorulur.
- Her denemeden sonra kontrol listesi uygulanır: yüz/el bozulması, titreme, okunur metin ya da
  logo, karakter tutarlılığı. Kusur varsa çekim seçilmez.

---

## REF – karakter referansı (Seedream görseli)
**Prompt**
> Photorealistic portrait of Marta, a 35-year-old Polish woman, energy efficiency consultant, shoulder-length dark blonde hair tied loosely, light natural make-up, small silver earrings, wearing a muted teal knit sweater over a white collar shirt, friendly focused expression, sitting at a wooden desk in a small modern office, soft window light from the left, 50mm lens, shallow depth of field, neutral background, high detail skin texture, no text, no logo

**Negatif:** text, watermark, logo, cartoon, illustration, heavy make-up, distorted hands, extra fingers

Biri seçilir ve `REF_marta.png` adıyla kaydedilir. Aynı kıyafet ve saç tüm çekimlerde korunur.

---

## S01 – Belgeler (0:00–0:05) · referanssız
**Prompt**
> Cinematic close-up, top-down angle slowly tilting to a low angle: a pair of hands spreads a thick stack of printed documents across a wooden desk in the evening — application forms, contracts, invoices and handover protocols, some with stamps and signatures, papers sliding and overlapping. Warm desk lamp light from the right, cool blue dusk light from a window, slow dolly push-in, shallow depth of field, all printed text soft and unreadable, realistic paper texture, gentle dust in the light beam. Commercial look, muted teal shadows and warm amber highlights.

**Negatif:** readable text, letters in focus, logos, brand names, watermark, extra fingers, warped hands, flicker

## S02 – Akşam kontrolü (0:05–0:10) · referans: REF_marta
**Prompt**
> Medium shot of Marta (reference image) at her desk in a small office at dusk, comparing two printed documents held side by side, eyes moving between them, she sighs and rubs her temple, a closed laptop and a coffee mug on the desk, window behind her with soft city lights bokeh, warm desk lamp on her face, slow lateral camera move from left to right, realistic, cinematic, shallow depth of field, documents' text unreadable.

**Negatif:** readable text, screen content, logos, smiling, extra people, distorted face, extra fingers, flicker

## S03 – Tek karakter (0:10–0:15) · referans: REF_marta (yalnızca el ve kazak kolu)
**Prompt**
> Extreme close-up macro shot: the tip of a dark blue pen moves slowly along a row of a printed table on a document, stops, and draws a small circle around one single character; teal knit sweater cuff visible at the edge of frame; very shallow depth of field, rack focus from the pen tip to the paper, the printed characters remain soft and unreadable, warm lamp light, subtle tension, cinematic.

**Negatif:** readable text, legible letters or numbers, logos, extra fingers, warped pen, flicker

## S10 – Rahatlama (0:46–0:51) · referans: REF_marta
**Prompt**
> Bright morning in the same small office, sunlight through the window, Marta (reference image) relaxed and smiling, closes a neat folder of documents and hands it across the desk to a colleague in a light shirt, both nod and smile, plants on the windowsill, slow push-in, clean modern interior, natural warm color grade, realistic, cinematic, no visible screen content.

**Negatif:** readable text, screen content, logos, distorted faces, extra fingers, extra people, flicker

## S11 – Sonuç (0:51–0:56) · referanssız
**Prompt**
> Golden hour exterior of a modern single-family house in a quiet Polish suburb, freshly insulated light plaster facade, a new white air-to-water heat pump outdoor unit standing on a small concrete base next to the wall; a homeowner couple in their forties shakes hands with an installer in grey work clothes in front of the house, a child waves from the doorway; slow crane-down camera move, warm sunlight, long soft shadows, realistic, cinematic commercial.

**Negatif:** text, brand logos on the heat pump, company names, signs, license plates, distorted faces, extra fingers, flicker, snow

---

## Kontrol listesi (her çekim)
- [ ] 1280×720, 16:9, 5 sn, akıcı (titreme yok)
- [ ] Okunur metin, logo ve marka yok
- [ ] Eller ve yüzler doğal; parmak sayısı doğru
- [ ] Marta: S02, S03 ve S10'da aynı kişi ve kıyafet
- [ ] Işık ve renk: akşam (S01–S03) soğuk/amber; sabah (S10) ve gün batımı (S11) sıcak
- [ ] Dosya `media\ai\Sxx.mp4` olarak kaydedildi; kullanılan kredi `PRODUCTION.md` tablosuna yazıldı
