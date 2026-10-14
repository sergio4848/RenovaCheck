# RenovaCheck – final raporu (TRL 3 prototip)

Tarih: 14.10.2026 · Repo: `github.com/sergio4848/RenovaCheck`, dal `main` · Durum: prototip tamamlandı,
tanıtım filmi üretildi.

Bu belge başvuru dosyası için kaynak metindir. Buradaki her sayı repodaki ölçümlerden gelir
(`docs/EVAL_REPORT.md`, CI kayıtları, `marketing/film/PRODUCTION.md`). Başvuruya aktarırken
sayılar „sentetik test verisi üzerinde" notuyla kullanılmalıdır.

---

## 1. Özet

**RenovaCheck**, Polonya'da „Czyste Powietrze" programı kapsamında termomodernizasyon başvurularını
hazırlayan ve kontrol eden firmalar (enerji denetçileri, başvuru operatörleri, kurulum firmaları) için
bir B2B SaaS'tır. Aynı dosyaya ait belgeleri birbiriyle karşılaştırır, tutarsızlık ve eksik belgeleri
kanıtıyla birlikte gösterir:
- wniosek özeti;
- oferta / umowa;
- faktura;
- protokół odbioru;
- karta produktu.

Kararı her zaman insan verir.

- **Olgunluk:** TRL 3. Teknik kavram, sentetik belgeler üzerinde uçtan uca çalışan bir prototiple
  kanıtlandı.
- **Süre:** planlanan 14 gün; prototip 13–14.10.2026 arasında 7 fazda tamamlandı.
- **Kapsam dışı (bilinçli):** enerji hesabı, audyt/świadectwo üretimi, hibe kararı, kurum (GWD)
  entegrasyonu, otomatik gönderim, gerçek müşteri verisi.

## 2. Problem ve çözüm

- **Problem:**
  - Bir sprawa 5–6 belgeden oluşur. Adres, yatırımcı, cihaz modeli ve gücü, tutarlar (net/brüt,
    avans, korekta), tarihler ve imzalar bu belgeler arasında elle karşılaştırılır.
  - Tek bir karakterlik fark (ör. model „PH-08A" yerine „PH-08B") rozliczenie'nin geri
    dönmesine yol açabilir.
  - Kontrol yavaştır, yorucudur ve iz bırakmaz.
- **Çözüm:**
  1. Belgeler yüklenir.
  2. Sistem belge türünü tanır ve tanımlı alanları okur. Her değer sayfa ve kutu konumuyla
     (provenans) saklanır.
  3. Deterministik ve versiyonlu kurallar belgeleri karşılaştırır.
  4. Bulgular önem derecesi, gerekçe ve kaynak kuralla gösterilir. Her bulgu, belge sayfasındaki
     tam yeri işaretler.
  5. Denetçi karar verir (zgodne / rozbieżność / uzgodniona zmiana / nie dotyczy). Kritik
     bulgularda yorum zorunludur; her karar kim/ne zaman bilgisiyle kalıcı olarak kaydedilir.
  6. Sprawa kapatılır ve PDF/CSV kontrol raporu alınır.

## 3. Yapılanlar

| Faz | İçerik | Kanıt |
|---|---|---|
| 1 İskelet | Docker Compose yığını: Laravel web, PostgreSQL (organizasyon başına RLS), Redis kuyruk, MinIO (S3) belge deposu, FastAPI extract servisi + worker; Fortify girişi, organizasyon ve roller | ADR-0001…0005 |
| 2 Sentetik veri | `tools/synth`: 20 sprawa, 106 PDF, 32 enjekte edilmiş hata, ground truth ve kutu konumları; yalnızca sentetik kişi/firma/NIP/adres | `tools/synth/README.md` |
| 3 Alma ve sınıflandırma | MIME/magic-byte kontrolü, opsiyonel ClamAV, tekrar algılama, özel depolama ve imzalı URL; metin katmanı ya da Tesseract OCR; belge türü sınıflandırıcı | ADR-0006 |
| 4 Ekstraksiyon | 27 alanlı sözlük, normalizasyon, deterministik çıkarıcılar, her değer için sayfa + kutu | ADR-0007 |
| 5 Kural motoru | 16 YAML kural (adres, taraflar, cihaz, tutarlar, eksik belge, tarih, imza, okuma kalitesi); şema, versiyon kilidi, kaynak bağlantısı | ADR-0008 |
| 6 İnceleme ekranı | Sayfa görüntüsü üzerinde kanıt kutuları, karar + yorum, değiştirilemez karar geçmişi, sprawa kapatma; sıkı CSP | ADR-0009, `docs/DEMO.md` |
| 7 Rapor ve ölçüm | PDF/CSV kontrol raporu; `make eval` ile tek komutta ölçüm raporu; OCR karşılaştırması | ADR-0010, `docs/EVAL_REPORT.md` |

**Ek işler:**
- **Laravel 11 → 13 geçişi** (ADR-0011): güvenlik desteği 2028-03'e kadar sürüyor. `composer audit`
  temiz ve CI'da zorunlu.
- **Marka kiti** (`brand/`): logo, `DESIGN.md`, Geist yazı tipleri (OFL).
- **60 sn tanıtım filmi** (`marketing/film/`); ayrıntılar §6'da.

## 4. Doğrulama ve ölçümler (sentetik test verisi)

**Veri seti:** 20 sprawa, 106 belge / 118 sayfa (98 temiz PDF, 8 gürültülü tarama), 32 beklenen bulgu.

| Ölçüt | Hedef | Ölçülen |
|---|---|---|
| Belge türü doğruluğu | ≥ %95 | **%100** (106/106) |
| Alan kesinliği / duyarlılığı, temiz PDF | ≥ %95 | **%100 / %100** |
| Alan kesinliği / duyarlılığı, taramalar | rapor | **%99,2 / %99,2** (1 OCR hatası: „PH-O8A") |
| Kural hataları, gerçek alanlar üzerinde (FP/FN) | 0 / 0 | **0 / 0** (32/32) |
| Uçtan uca kurallar (OCR + ekstraksiyon + kural) | rapor | **kesinlik %97,0, duyarlılık %100** (1 yanlış pozitif, OCR kaynaklı ve „skandan okundu" uyarısıyla) |
| İşlem süresi, temiz PDF (p50) | – | ~20–30 ms / belge |
| İşlem süresi, tarama (p50) | – | ~2 s / belge |
| Kural motoru, sprawa başına | – | ~1 ms |

**OCR karşılaştırması** (200 sentetik sayfa, Tesseract):

| Ölçüt | Değer |
|---|---|
| Alan bulma oranı, temiz / tarama | %97,1 / %94,0 |
| CER / WER, temiz | %3,1 / %7,1 |
| Sayfa başı maliyet | ~0,00002 USD |

Azure ve Google sütunları API anahtarı olmadığı için çalıştırılmadı. Liste fiyatları 1,50 USD /
1000 sayfa olarak not edildi.

**Testler ve CI:**
- 130 web testi (gerçek PostgreSQL + RLS üzerinde);
- 242 extract testi;
- 31 sentetik üreteç testi;
- ruff, mypy, Pint, `composer audit`;
- tüm yığının Docker'da ayağa kalkıp test edildiği ayrı bir CI işi.

`main` dalında CI yeşil.

## 5. Güvenlik ve veri koruma

- **Organizasyonlar arası izolasyon:** veritabanı düzeyinde PostgreSQL Row-Level Security.
  Uygulama hatası bile başka organizasyonun verisini döndüremez; CI'da izolasyon testleri var.
- **Denetim günlüğü:** append-only ve hash zinciriyle kurcalamaya karşı korumalı.
- **Belge depolama:** belgeler özel S3 deposunda tutulur ve yalnızca kısa ömürlü imzalı URL ile
  açılır. Yüklemede içerik tipi doğrulanır; isteğe bağlı virüs taraması yapılır.
- **Tarayıcı tarafı:** sıkı Content-Security-Policy, inline script yok. Raporlarda CSV
  formül enjeksiyonuna karşı koruma var.
- **Harici servisler:** dış OCR/LLM servisleri varsayılan olarak kapalı. Yalnızca onay vermiş
  organizasyonlar için açılabilir.
- **Bu oturumda düzeltilen iki hata:**
  - yeni kurulumda MinIO yetki politikasının bağlanmaması;
  - depolama yazımı başarısız olduğunda belgenin yine de kaydedilmesi.

## 6. Tanıtım filmi (tamamlandı)

**Özellikler:** 60 sn, 1280×720, 25 fps. Lehçe seslendirme ve İngilizce altyazı. Ürün sahneleri
uygulamanın gerçek ekran kayıtları; hikâye sahneleri Dreamina Seedance 2.5 ile üretildi; tüm veriler
sentetik.

**Üretim:**
- **AI sahneleri:** 5 sahne ve 1 karakter referansı. Toplam **2.847 kredi** harcandı (sınır 3.500);
  her sahne ilk denemede kabul edildi.
- **Seslendirme:** ElevenLabs, ses „Magdalena – Warm, Low-Pitched and Lively", model Multilingual v2.
- **Müzik:** ElevenLabs Music. Ticari kullanım öncesinde plan şartları kontrol edilmeli.
- **Kurgu:** Premiere Pro. Ses seviyesi −14,2 LUFS, true peak −1,2 dBTP.

**Çıktılar:** `renovaCheck\export\` klasöründe:
- `RenovaCheck_promo_60s_EN-subs.mp4` (altyazı gömülü);
- `RenovaCheck_promo_60s_clean.mp4`;
- `RenovaCheck_promo_60s_EN.srt`.

**İletişim:** sergen@saimediaworks.com.tr

## 7. Sınırlar ve açık riskler

- **Veri:** yalnızca sentetik veri kullanıldı. Ölçümler gerçek belgelerdeki performansı garanti etmez;
  gerçek belge setiyle doğrulama bir sonraki aşamadır.
- **Kurallar:** kurallar resmi Czyste Powietrze sayfalarına dayanır ve „do weryfikacji" olarak
  işaretlidir. Başvuru paketindeki 03–08 kaynak belgeleri prototip sırasında sağlanmadı.
- **OCR karşılaştırması:** bulut OCR (Azure/Google) karşılaştırması eksik; anahtar verildiğinde aynı
  script çalışır.
- **Canlı ortam:** henüz yok. Uygulama Docker ile yerelde çalışıyor; gereksinimler §8'de.

## 8. Sonraki adımlar (TRL 4–6 yolu)

1. **Gerçek belgelerle doğrulama:** pilot firmalarla anonimleştirilmiş gerçek belge seti; alan ve
   kural doğruluğunun yeniden ölçülmesi; kuralların uzman (enerji denetçisi) onayından geçmesi.
2. **Pilot ortam:**
   - Docker çalıştırabilen bir VPS (≥ 2 vCPU, 4 GB RAM), PostgreSQL 16, HTTPS;
   - yedekleme ve izleme;
   - RODO uyumu (veri işleme sözleşmesi, saklama süreleri).
3. **OCR:** bulut OCR karşılaştırmasının tamamlanması ve taramalar için en iyi sağlayıcının seçilmesi.
4. **Ürün:** kullanıcı yönetimi, program sürümlerine göre kural setleri, toplu sprawa görünümü.

## 9. Başvuru için kısa metinler

**Türkçe (1 paragraf):**
RenovaCheck, termomodernizasyon başvurularını hazırlayan firmalar için belge tutarlılığı kontrolü
yapan bir B2B SaaS'tır. Wniosek, oferta/umowa, faktura, protokół odbioru ve karta produktu
belgelerindeki adres, cihaz, tutar, tarih ve imza bilgilerini okur, deterministik ve versiyonlu
kurallarla karşılaştırır ve her tutarsızlığı belge sayfasındaki kanıtıyla gösterir. Kararı insan
verir; tüm kararlar denetim izine kaydedilir ve PDF/CSV kontrol raporu üretilir. TRL 3 prototip
sentetik test verisinde belge türlerini %100, temiz PDF'lerdeki alanları %100 doğrulukla okudu ve
32 beklenen tutarsızlığın tamamını buldu.

**Polski:**
RenovaCheck to usługa B2B SaaS dla firm przygotowujących wnioski termomodernizacyjne, która
sprawdza spójność dokumentów sprawy: wyciągu z wniosku, oferty/umowy, faktur, protokołu odbioru i
karty produktu. System odczytuje adresy, dane urządzeń, kwoty, daty i podpisy, porównuje je za pomocą
deterministycznych, wersjonowanych reguł i wskazuje każdą rozbieżność bezpośrednio na stronie
dokumentu. Decyzję podejmuje człowiek; każda decyzja trafia do niezmiennej historii, a na koniec
powstaje raport kontroli w PDF lub CSV. Prototyp TRL 3 na danych syntetycznych rozpoznał 100 %
typów dokumentów, odczytał 100 % pól z czystych PDF-ów i wykrył wszystkie 32 oczekiwane rozbieżności.

**English:**
RenovaCheck is a B2B SaaS for firms that prepare thermal-modernisation grant applications. It
cross-checks the documents of a case (application extract, offer/contract, invoices, acceptance
report, product sheet): it reads addresses, device data, amounts, dates and signatures, compares them
with deterministic, versioned rules and shows every discrepancy on the document page itself. A person
makes every decision; decisions are kept in an append-only history and the case ends with a PDF or
CSV control report. On synthetic test data the TRL 3 prototype recognised 100 % of document types,
read 100 % of fields from clean PDFs and found all 32 expected discrepancies.

## 10. Kaynaklar (repo içinde)

| Konu | Dosya |
|---|---|
| Ölçüm raporu | `docs/EVAL_REPORT.md` |
| Plan, varsayımlar | `docs/PLAN.md`, `docs/ASSUMPTIONS.md` |
| Mimari kararlar | `docs/ADR/0001…0011` |
| 5 dakikalık demo senaryosu | `docs/DEMO.md` |
| Ekran görüntüleri | `docs/screens/` |
| Marka | `brand/README.md`, `brand/DESIGN.md` |
| Film üretim kaydı | `marketing/film/PRODUCTION.md` |
| Kurulum (yerel) | `README.md` → Quick start |
