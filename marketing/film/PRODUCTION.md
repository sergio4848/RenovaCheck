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
| REF | | | | |
| S01 | | | | |
| S02 | | | | |
| S03 | | | | |
| S10 | | | | |
| S11 | | | | |
| **Toplam** | | | | |

## 2. ElevenLabs – `VOICEOVER.md`
1. Ses seçimi (Polish, 2–3 aday, VO04 ile dene).
2. VO01…VO11 tek tek üret → `media\vo\VO01.wav` …
3. Opsiyonel: müzik (`media\music\music.mp3`) ve 3 efekt (`media\sfx\`).
4. Her segmentin gerçek süresini not et; hedeften > %10 sapma varsa `VOICEOVER.md`'deki uydurma
   adımları uygulanır.

## 3. Premiere Pro – `EDIT_PLAN.md`
1. `renovaCheck` projesini aç; `marketing/film/edit/renovacheck_assembly.xml` dosyasını içe aktar.
2. Offline klipleri `media\` klasörüne bağla (Link Media).
3. VO segmentlerinin gerçek uzunluğuna göre ince ayar: her VO, `script.json`'daki başlangıcına
   oturur; kayan kesmeler en yakın nefes boşluğuna çekilir.
4. Altyazı: `subtitles\en.srt` içe aktarılır ve zamanlaması VO'ya göre düzeltilir.
5. Hareket, renk, ses ve dışa aktarma: `EDIT_PLAN.md` 3–7.
6. Son kontrol listesi (`EDIT_PLAN.md` §8).

## 4. Açık kararlar (kullanıcı)
- Kapanış kartındaki iletişim satırı: web adresi / e-posta / telefon.
- ~~AI notu~~: **konmayacak** (kullanıcı kararı, 2026-10-14). Filmdeki kişiler kurgusaldır;
  gerçek bir kişiye benzeyen görüntü üretilmez.
- Müzik kaynağı: ElevenLabs Music ya da lisanslı stok parça (lisans notu buraya).

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
