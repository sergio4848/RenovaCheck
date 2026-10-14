# Üretim sırası (runbook)

Bu paket repo'da hazır: senaryo, altyazılar, çekim listesi, Seedance prompt'ları, seslendirme
talimatı, grafikler, gerçek arayüz kayıtları ve Premiere ilk montaj XML'i. Geriye kalan üretim
adımları bu sırayla yapılır.

## 0. Hazırlık
1. Repo'yu güncelle: `git pull` (dal: `claude/loving-meitner-q1lxqh`).
2. Premiere proje klasöründe medya yapısını kur:
   `C:\Users\serge\OneDrive\Documents\Adobe\Premiere Pro\26.0\renovaCheck\media\{ai,ui,gfx,vo,music,sfx}`
3. Kopyala: `marketing/film/ui/*` → `media\ui\`, `marketing/film/graphics/*` → `media\gfx\`
   (`.png` ve `.mov` hepsi).
4. Fontları kur: `brand/fonts/*.ttf` (Geist, Geist Mono; OFL). Premiere'i yeniden başlat.

## 1. Dreamina (Seedance 2.5) – `SEEDANCE_PROMPTS.md`
1. Bakiyeyi not et (başlangıç: 7185 kredi).
2. Karakter referansı: Seedream ile `REF_marta.png`.
3. S01, S02, S03, S10, S11: 720p, 16:9, 5 sn. Her üretimden önce gösterilen maliyeti oku;
   aşağıdaki tabloya yaz.
4. Kontrol listesinden geçen klibi `media\ai\Sxx.mp4` olarak kaydet.
5. **Durma:** toplam 3.500 krediye ulaşınca ya da bir çekim 3 denemede olmazsa dur ve kullanıcıya
   sor (yedek: `ui\UI06_case_list.mp4`).

| Çekim | Deneme | Kredi | Seçildi mi | Not |
|---|---|---|---|---|
| REF | 1 (2 görsel) | 72 (36/görsel, Seedream 5.0 Pro, 3:4, 2K; arayüz: 48 → %25 indirim) | evet – 2. görsel | 14.10 14:10; başlangıç bakiyesi arayüzde 7.2K; `media\ai\REF_marta.png` (1728×2304) |
| S01 | 1 | 555 (Seedance 2.5, 16:9, 720p, 5 s) | evet | 14.10 14:20; 1280×720, 5.06 s; metin okunmuyor, el doğal; klip ses izi içeriyor → kurguda sessize alınır |
| S02 | 1 | 555 (Seedance 2.5, 16:9, 720p, 5 s, @Marta öğesi referans) | evet | 14.10 14:33; 1280×720, 5.02 s; karakter REF ile tutarlı; şakak ovma 3.5–5 s arasında; laptop açık (prompt: kapalı) – kabul |
| S03 | 1 | 555 (Seedance 2.5, 16:9, 720p, 5 s, @Marta) | evet | 14.10 14:58; 5.06 s; kalem ~3.5–4.0 s'de durup karakteri çevreliyor (VO03 „literówka" buraya denk getirilir); tablo metni sahte sözcükler (okunmuyor); kazak kolu kadrajda |
| S10 | 1 | 555 (Seedance 2.5, 16:9, 720p, 5 s, @Marta) | evet | 14.10 15:08; 5.06 s; dosyayı kapatıp uzatıyor, 2.5 s'den sonra el sıkışma (promptta „nod" – kabul, rahatlama duygusu yerinde); meslektaş omuz üstünden, yüzü yok |
| S11 | 1 | 555 (Seedance 2.5, 16:9, 720p, 5 s) | evet | 14.10 15:17; 5.06 s; çatıdan vinç inişi, 2 s'den sonra çift + montajcı el sıkışıyor, kapıda el sallayan çocuk; ısı pompasında logo yok; altın saat |
| **Toplam** | 6 üretim | **2.847** (sınır 3.500; bakiye arayüzde 4.3K) | 5/5 | Her çekim tek denemede kabul edildi; yeniden deneme yapılmadı. Seedance çıktıları ses izi içeriyor (promptta „no audio" olsa da) – kurguda sessize alınır. Gerçek fiyat: Seedance 2.5 720p/5 s = 555 kredi (belgedeki 130–185 tahmini geçersiz) |

## 2. ElevenLabs – `VOICEOVER.md`
1. Ses seçimi (Polish, 2–3 aday, VO04 ile dene).
2. VO01…VO11 tek tek üret → `media\vo\VO01.wav` …
3. Opsiyonel: müzik (`media\music\music.mp3`) ve 3 efekt (`media\sfx\`).
4. Her segmentin gerçek süresini not et; hedeften > %10 sapma varsa `VOICEOVER.md`'deki uydurma
   adımları uygulanır.

**Yapıldı (14.10.2026):** ses testi VO04 ile 3 aday (Magdalena – Warm, Low-Pitched and Lively; Magdalena – Mighty and Calm Wordsmith; Asia – Warm and Friendly Native Polish; testler `media\vo\_tests\`). **Seçilen ses: Magdalena – Warm, Low-Pitched and Lively** (Voice Library, Polish, Narration). Model Eleven Multilingual v2, stability 50 %, similarity 75 %, style 15 %, speaker boost açık, dil Polish, hız 0.98 (sesin varsayılanı; VO05 1.08, VO08 1.08). Hesapta WAV üretimi kapalı → MP3 44.1 kHz 128 kbps üretildi, geçmişten WAV 48 kHz olarak indirildi (VO05: MP3 → ffmpeg ile 48 kHz WAV).

| Segment | Hedef (s) | Gerçek (s) | Not |
|---|---|---|---|
| VO01 | 4.0 | 3.89 | ✓ |
| VO02 | 4.8 | 5.04 | +5 % ✓ |
| VO03 | 3.8 | 3.94 | ✓ |
| VO04 | 3.8 | 3.79 | ✓ |
| VO05 | 5.2 | 5.93 | +14 % – 3 deneme (0.98: 6.45; 1.05: 6.03; 1.08: 5.93); en kısası alındı, kurguda VO06 ≈0.7 s kaydırılır; alternatifler `_alt\` |
| VO06 | 5.6 | 5.28 | ✓ |
| VO07 | 5.6 | 3.89 | kısa – boşluk müzikle dolar |
| VO08 | 4.8 | 4.73 | 3. deneme (1.08 + tire→virgül); 1./2. deneme 5.33/5.46 `_alt\` |
| VO09 | 4.4 | 4.62 | +5 % ✓ |
| VO10 | 4.6 | 4.21 | ✓ |
| VO11 | 3.6 | 3.66 | ✓ |

## 3. Premiere Pro – `EDIT_PLAN.md`
1. `renovaCheck` projesini aç; `marketing/film/edit/renovacheck_assembly.xml` dosyasını içe aktar.
2. Offline klipleri `media\` klasörüne bağla (Link Media).
3. VO segmentlerinin gerçek uzunluğuna göre ince ayar: her VO, `script.json`'daki başlangıcına
   oturur; kayan kesmeler en yakın nefes boşluğuna çekilir.
4. Altyazı: `subtitles\en.srt` içe aktarılır ve zamanlaması VO'ya göre düzeltilir.
5. Hareket, renk, ses ve dışa aktarma: `EDIT_PLAN.md` 3–7.
6. Son kontrol listesi (`EDIT_PLAN.md` §8).

**Yapıldı (14.10.2026, Premiere MCP + ExtendScript):**
- Proje yedeği: `renovaCheck\renovaCheck_backup_<tarih>.prproj`. XML içe aktarıldı; orijinal `RenovaCheck_promo_60s` sekansına dokunulmadı, kurgu **`RenovaCheck_promo_60s_edit`** kopyasında yapıldı. Tüm medya `media\` altından otomatik bağlandı (offline klip yok).
- Zamanlama: VO klipleri gerçek sürelerine kırpıldı; VO03 10.2→**10.6 s**, VO06 24.0→**24.4 s** (VO05 uzun). S03 giriş noktası 0.4→**0.85 s** (kalem 12.9 s'de duruyor; „literówka" ~11.5 s – tam eşleşme klip uzunluğu nedeniyle mümkün değil, kalem kelime söylenirken satırda ilerliyor). `script.json` ve `subtitles/*.srt` yeni zamanlarla yeniden üretildi.
- Geçişler: S01 başta 12 kare siyahtan; S04 başında 8 kare Dip to White (+whoosh 14.2); S05 8 kare, S09b 6 kare, S10 10 kare, S12 12 kare Cross Dissolve; S12 sonunda 10 kare siyaha; S06 kenar notu çıkışı 6 kare dissolve.
- Hareket: S05 üst-orta çapa 100→108 %; S06 100→105 %; S07 sol yarı çapa 100→115 %; S09b 100→112 %.
- Renk: yalnız AI çekimlerinde (S01–S03, S10, S11) Lumetri (kontrast +5, doygunluk 90, sıcaklık −3, Faded Film 8) + Premiere „Noise" grain (yoğunluk 18, renk 20). Arayüz ve grafiklerde düzeltme yok.
- Altyazı: EDIT_PLAN §5 stili (Geist Medium 32 px, kâğıt metin, mürekkep kutu %90, 6/12 px, alt 56 px) **PNG katman olarak V3'te** (`media\gfx\subs\SUB_01…11.png`; Captions izinin stilini API ile ayarlamak mümkün olmadığı için). `subtitles\en.srt` sidecar.
- Kapanış kartı iletişim satırı: `media\gfx\subs\CONTACT_email2.png` – **sergen@saimediaworks.com.tr** (kullanıcı kararı 14.10; web adresi yok) (Geist Regular 18 px, #5B6470, x=100 y=530), 6 kare giriş / 10 kare çıkış.
- Ses: VO +1.5…+3 dB (≈ −16 LUFS). Müzik: Premiere anahtar kare ducking yerine **sidechain ile işlenmiş dosya** `media\music\music_ducked.mp3` (VO yatağı ile sidechaincompress, konuşma altında ≈ −12 dB; 58.8–60 s sönüm), klip seviyesi −16 dB → boşluklarda ≈ −31 LUFS, konuşma altında ≈ −44 LUFS (kullanıcı isteği: müzik sesi bastırmasın). Efektler: paper +20 dB (kaynak çok düşüktü), whoosh −14 dB, click −6 dB. Dışa aktarma sonrası ffmpeg ile +1.95 dB → **−14.2 LUFS, true peak −1.2 dBTP** (export normalizasyonu).
- Dışa aktarma: özel preset `RenovaCheck_720p25_8Mbps.epr` (H.264 1280×720 25p VBR 2-pass 8/12 Mbps, AAC 320 k). Sonuç: `renovaCheck\export\RenovaCheck_promo_60s_EN-subs.mp4`, `RenovaCheck_promo_60s_clean.mp4`, `RenovaCheck_promo_60s_EN.srt` (ham ve test dosyaları `export\_tmp\`).

## 4. Açık kararlar (kullanıcı)
- ~~Kapanış kartındaki iletişim satırı~~: **sergen@saimediaworks.com.tr** (kullanıcı, 14.10.2026).
- ~~AI notu~~: **konmayacak** (kullanıcı kararı, 2026-10-14). Filmdeki kişiler kurgusaldır;
  gerçek bir kişiye benzeyen görüntü üretilmez.
- Müzik kaynağı: **ElevenLabs Music** (Eleven Music v2.5, enstrümantal, 60 s, 14.10.2026; `media\music\music.wav/.mp3`; kullanım hakları ElevenLabs hesap planına tabidir – ticari kullanım öncesi plan şartları kontrol edilmeli).

## Dosya haritası
| Dosya | İçerik |
|---|---|
| `TREATMENT.md` | Konsept, ton, yapı, müzik ve dürüstlük ilkeleri |
| `SCRIPT.md` / `script.json` | Lehçe seslendirme, İngilizce altyazı, ekran metinleri |
| `subtitles/en.srt`, `subtitles/pl.srt` | Altyazılar (`tools/make_srt.py`) |
| `SHOTLIST.md` / `shots.json` | Çekim listesi ve zamanlama |
| `SEEDANCE_PROMPTS.md` | AI çekim prompt'ları, kredi bütçesi |
| `VOICEOVER.md` | ElevenLabs ses, müzik ve efekt talimatı |
| `EDIT_PLAN.md` | Premiere kurgu planı |
| `edit/renovacheck_assembly.xml` | İlk montaj (FCP7 XML, `tools/make_xml.py`) |
| `ui/` | Gerçek arayüz kayıtları ve durağan görüntüler (`tools/capture_ui.js`) |
| `preview/animatic.mp4` | Ön izleme: son zamanlamalar, AI yerine yer tutucu kartlar (`tools/make_animatic.py`) |
| `graphics/` | Editoryal grafikler: başlık ve kapanış kartı, kenar notları, numaralı ilkeler, el çizimi işaretler; PNG ve animasyonlu ProRes 4444 `.mov` (`brand/tools/render_graphics.js`, stil: `brand/DESIGN.md`) |

Bir metin ya da zaman değişirse: `script.json`/`shots.json` düzenlenir, ardından
`tools/make_srt.py`, `tools/make_docs.py`, `tools/make_xml.py` ve `tools/make_animatic.py` çalıştırılır.
