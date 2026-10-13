# Varsayımlar ve eksikler

Bu dosya, kaynak dokümanlarda bulunmayan ya da belirsiz kalan konularda verilen kararları kaydeder.
Her madde: **varsayım** → gerekçe → doğrulanınca ne değişir.

## A. Kaynak dokümanlar

| # | Varsayım | Gerekçe | Etki |
|---|---|---|---|
| A1 | `docs/03_*`, `05_*`, `06_*`, `07_*`, `08_*` dosyaları bu ortamda **yok** (çalışma klasörü boş, Google Drive'da "RenovaCheck / termomodernizacja / Czyste Powietrze" aramaları sonuç vermedi). Ürün sınırları, MVP kapsamı ve "yapmayacaklar" yalnızca `14_Claude_Code_Prompt_RenovaCheck.md` içindeki özetlerden alındı. | Başlangıç promptu bu dosyaları özetliyor; prototip için yeterli. | Dosyalar eklendiğinde kapsam/alan sözlüğü/ölçüm planı bunlarla karşılaştırılır; çelişkiler `PLAN.md`'de "açık soru" olarak işaretlenir. |
| A2 | Tek program: **Czyste Powietrze** (tek aileli bina, bireysel yatırımcı). Kurallar bu programın tek bir "edition"ı için yazılır; `valid_from/valid_to` alanları sürüm geçişini modellemeye hazırdır. | "Birden fazla program" ve "çok aileli bina" yapılmayacaklar listesinde. | Başka program istenirse hatırlatılır. |
| A3 | Belge seti (05'in yerine): `wniosek_ekstrakt` (başvurudan alınan özet: inwestor, adres, kapsam), `oferta`/`umowa`, `faktura` (+ `faktura korygująca` / `faktura zaliczkowa`), `protokół odbioru`, `karta produktu`. | Promptta sayılan set. | — |
| A4 | Ölçüm planı (07'nin yerine): alan bazında precision/recall, belge türü doğruluğu, kural başına FP/FN; temiz PDF eşik ≥ %95, gürültülü skan yalnızca raporlanır. | Promptun faz kabul kriterleri. | 07 gelirse metrikler genişletilir. |

## B. Veri ve gizlilik

| # | Varsayım | Gerekçe |
|---|---|---|
| B1 | Sentetik NIP'ler checksum'ı geçerli ama **`00` ile başlayan** (hiçbir urząd skarbowy koduna atanmamış) numaralardır → gerçek bir firmayla çakışamaz. | "Gerçek NIP kullanma" kuralı + format gerçekçiliği. |
| B2 | Firma, kişi ve yer adları uydurma sözlüklerden üretilir (ör. `Zielonowo`, `Brzozówka Mała`); posta kodları `NN-NNN` formatında ama uydurma yerleşimlere bağlıdır. Her sayfada küçük "DOKUMENT SYNTETYCZNY" ibaresi vardır. | Gerçek adres kullanmama. |
| B3 | ZUM (Zielona Lista Urządzeń i Materiałów) için yalnızca uydurma üretici/model içeren `packages/rules/zum_sample.csv` kullanılır. | Gerçek veri yok kuralı. |

## C. Teknik

| # | Varsayım | Gerekçe |
|---|---|---|
| C1 | Laravel **11** sabit karar olarak kullanılır (promptta "tartışma yok"). Laravel 11'in güvenlik desteği 2026 Mart'ında bitti; bu bir prototip riski olarak `PLAN.md`'de kayıtlı, 12'ye yükseltme ayrı bir karar. | Sabit mimari kararı. |
| C2 | PDF işleme yalnızca izin verici lisanslı kütüphanelerle yapılır (pdfplumber/pdfminer MIT, pypdfium2 Apache-2.0/BSD, reportlab BSD, Pillow HPND). **PyMuPDF (AGPL) kullanılmaz.** | SaaS'ta AGPL yükümlülüğünden kaçınma. |
| C3 | "Temiz metin modu" = PDF metin katmanından kelime + bbox okuma (`PdfTextLayer` adaptörü). OCR adaptörü tanımlı olmasa da test suite bu modda geçer. | Promptun OCR şartı. |
| C4 | Bulut OCR (Azure DI Poland Central, Google Document AI) anahtarları bu ortamda yok; adaptörler kayıtlı yanıt fixture'larıyla birim testinden geçer, gerçek kıyaslama anahtar verildiğinde çalışır. | Gizli anahtarlar yalnızca env. |
| C5 | UI kütüphanesi: Tabler (MIT) `@tabler/core` derlenmiş dosyaları lisansıyla birlikte `apps/web/public/vendor/tabler/` altına konur; Node build zinciri zorunlu değildir. | SPA yok, sade kurulum. |
| C6 | Virüs taraması ClamAV ile yapılır ama compose profili `av` altında **varsayılan kapalıdır** (imza veritabanı ~1 GB). Kapalıyken yükleme yine magic-byte tip, boyut ve sayfa sayısı kontrolünden geçer; durum `scan: skipped` olarak kaydedilir. | Yerel kurulumun hafif kalması. |
| C7 | Web ↔ extract: Laravel kuyruk işi orkestrasyonu yapar ve DB'ye tek yazar odur; extract servisi durumsuzdur, dosyaya kısa ömürlü signed URL ile erişir. Python `worker` toplu işler içindir (eval, OCR kıyaslama). | RLS ve audit tek yerde kalır; iki dilde şema sahipliği çakışmaz. |
| C8 | Kural motoru ve eval Python'da (`services/extract` + `packages/rules`) çalışır; Laravel bulguları saklar ve karar akışını yönetir. | Eval Laravel'siz, hızlı ve deterministik koşar. |
| C9 | Yerel S3 deposu: `minio/minio` imajları Docker Hub'dan kaldırıldığı için topluluk derlemesi `pgsty/minio` (sabit sürüm) kullanılır; uygulama yalnızca S3 API'sine bağlıdır (ADR-0004). | "MinIO yerelde" kararı korunur, imaj kaynağı değişir. |
| C10 | RLS "baseline" kontrolleri pgTAP yerine PHPUnit içinden katalog sorgularıyla yapılır (`RlsBaselineTest`). | Ek Postgres eklentisi/imajı gerektirmez; aynı güvenceyi verir. |
| C11 | Hash zinciri değiştirmeyi **tespit eder**, şema sahibi yetkisiyle trigger'ı kapatan birini **engellemez** (ADR-0005). | Prototip için yeterli; üretimde harici imzalı çapa (ör. günlük hash'in dışarı yazılması) değerlendirilir. |

## D. Sentetik veri (Faz 2)

| # | Varsayım | Gerekçe |
|---|---|---|
| D1 | "20 sprawa × 5 belge = 100 belge" beş **çekirdek belge slotu** olarak yorumlandı: wniosek_ekstrakt, oferta/umowa, faktura, protokół odbioru, karta produktu. `missing_protocol` senaryosu slotu boş bırakır (2 vaka → 98 çekirdek belge); faktura zaliczkowa/korygująca ve aneks ek belgedir (+8). Toplam 106 PDF. | Eksik belge senaryosu tanım gereği belgeyi kaldırır; ek faturalar promptta "+" olarak tanımlı. |
| D2 | Tek tedbir türü: hava-su pompa ciepła (+ montaż, opsiyonel zasobnik c.w.u. ve %23 KDV'li servis kalemi). Docieplenie/stolarka yok. | Kapsamı büyütmeme; tutar kuralları için %8/%23 karışımı yeterli. |
| D3 | Konut termomodernizasyonunda montajlı cihaz teslimi için %8 KDV (art. 41 ust. 12); servis kalemi %23. | Gerçekçi netto/brutto satırları. Vergi danışmanlığı değildir. |
| D4 | Üretici/model adları (Termavix TVX-08A vb.), ZUM numaraları (`ZUM/PC/1234`) ve şirket adları uydurmadır; yerleşim adları uydurma olmakla birlikte Polonya'da benzer adlı köyler bulunabilir. | Gerçek veri kullanmama kuralı. |
| D5 | Wniosek ekstrakt, başvurunun tamamı değil; operatör sisteminden alınmış bir "wyciąg" olarak modellenir (başvurucu, adres, kapsam, planlanan maliyet). | 05 dokümanı yok; prompttaki "wniosek özeti" ifadesi. |

## E. Belge alma ve sınıflandırma (Faz 3)

| # | Varsayım | Gerekçe |
|---|---|---|
| E1 | Sınıflandırma yalnızca kural/anahtar kelime ile yapılır; "opsiyonel model" ertelendi. | Sentetik sette %100 doğruluk (106/106, skanlar dahil); model eklemek ölçülebilir bir kazanç getirmez. Gerçek belgelerde yeniden değerlendirilir. |
| E2 | Compose'da varsayılan OCR `tesseract` (pol). Testler ve `RENOVA_OCR_PROVIDER=text_layer` modu OCR'sız çalışır; bu modda skanlar "nierozpoznany" kalır, yanlış türe atanmaz. | Promptun "adaptörsüz test" şartı + skanların sınıflandırılması. |
| E3 | Sayfa görüntüleri 150 dpi gri tonlamalı PNG; sayfa sınırı 50, dosya sınırı 20 MB (web) / 25 MB (extract), istek başına 20 dosya. | İnceleme ekranı için yeterli çözünürlük, makul depolama. |
| E4 | ClamAV varsayılan kapalı (`--profile av` + `CLAMAV_ENABLED=true` ile açılır); açıkken ClamAV'a ulaşılamazsa yükleme reddedilir (fail closed). | ASSUMPTIONS C6. |
| E5 | Holdout ölçümü (seed 4242) aynı şablon ailesinden üretildiği için gerçek dağılım dışı test değildir. | Ezberleme riskinin kısmi kontrolü; gerçek belgelerle doğrulama TRL 4 işi. |
| E6 | Kaynak sınırları prototip değerleri: sayfa render ≤ 25 MP, görüntü ≤ 40 MP, sayfa başına ≤ 100k karakter, belge başına OCR bütçesi 120 s, eşzamanlı analiz 2, extract konteyneri 2 GB / 2 CPU. | Güvenlik incelemesi (kaynak tüketimi); gerçek yükte ölçülüp ayarlanır. |
| E7 | Yerel MinIO'da servis başına hesap (`minio-init`): web yalnızca `org/*` altında oku/yaz/sil, extract yalnızca `…/pages/*` altına yazar. Root hesabı yalnızca kurulumda kullanılır. Üretimde aynı ayrım bulut IAM ile yapılır. | En az yetki; extract orijinallere yalnızca web'in imzaladığı URL ile erişir. |
| E8 | Veritabanı sahibi (`renova_owner`) kimlik bilgileri yalnızca `migrate` servisine verilir; web ve kuyruk yalnızca `renova_app` ile çalışır. | RLS'in atlanamaması (ADR-0002). |

## F. Alan çıkarımı ve provenans (Faz 4)

| # | Varsayım | Gerekçe |
|---|---|---|
| F1 | Çıkarım tamamen deterministiktir (etiket/blok/adres/başlık/imza mürekkebi); "tablo" yöntemi kalem satırları için henüz kullanılmaz, toplamlar etiketli satırlardan okunur. Kalem satırları Faz 5'te tutar kuralı gerektirirse eklenir. | Kabul kriteri toplam tutarlar üzerinden; kalem toplamı kuralı (Faz 5 c) gerekirse aynı yerleşim modeli kullanılır. |
| F2 | Belge türü hangi alanların okunacağını belirler; tür bilinmiyorsa tüm alanlar denenir. Kişinin düzelttiği tür extract'a `doc_type` olarak gönderilir ve tür düzeltmesi analizi yeniden çalıştırır. | Yanlış türde gereksiz alan (FP) üretmemek. |
| F3 | Sokak adlarında `ul./al./pl./os.` öneki ve yaygın patron adları/baş harfleri (ör. „Tadeusza”, „T.”) karşılaştırmada yok sayılır; liste `fields/normalize.py` içindedir ve son kelime asla düşürülmez. | „ul. T. Kościuszki” = „Kościuszki” (sentetik hata türü `street_spelling_variant` bunu bekler). |
| F4 | Model karşılaştırması büyük/küçük harf, tire ve boşluğu yok sayar; A/B varyantları farklı kalır. OCR'ın `0`/`O` karışıklığı düzeltilmez (skan ölçümünde 1 hata olarak görünür). | Yanlış düzeltme, gerçek bir model farkını gizleyebilir. |
| F5 | İmza varlığı, imza başlığının üstündeki alanda koyu piksel oranıyla ölçülür (≥ %0,4 imzalı, ≤ %0,15 imzasız, arası düşük güvenle). İmzanın kime ait olduğu veya geçerliliği değerlendirilmez. | Kapsam: „podpis var/yok”. |
| F6 | LLM yardımcısı varsayılan kapalı. Açılırsa sayfa metni (yalnızca sentetik veri) yapılandırılan sağlayıcıya gider; öneri yalnızca sayfada birebir geçiyorsa kabul edilir, güven ≤ 0,5. Varsayılan model `claude-sonnet-5-5` (`RENOVA_LLM_MODEL`). OpenAI sağlayıcısı kaldırıldı (tek sağlayıcı yeterli). | Promptun „opsiyonel, kapalı, temperature 0, string-match” şartı. |
| F7 | Azure/Google adaptör testleri, belgelenmiş yanıt şemasına göre yazılmış fixture'larla çalışır (canlı servisten kaydedilmedi; anahtar yok). Google için erişim belirteci ortamdan gelir (`gcloud auth print-access-token`, saatlik); servis hesabı anahtarı saklanmaz. | ASSUMPTIONS C4; gerçek kıyaslama Faz 7'de anahtarla. |
| F8 | Ölçüm, doğru belge türüyle (ground truth) yapılır; sınıflandırma hatası ayrı ölçülür (Faz 3, %100). Aynı alan bir belgede birden çok kez basılmışsa (protokolde adres) herhangi biriyle eşleşme doğru sayılır. `unreadable` FN'dir ama FP değildir. | Hataların kaynağını ayırmak. |

## G. Kural motoru (Faz 5)

| # | Varsayım | Gerekçe |
|---|---|---|
| G1 | Tüm kurallar `program: czyste_powietrze`, `edition: 2025-03-31`, `valid_from: 2025-03-31` ile yazıldı; `source_url` programın resmi sitesi (`https://czystepowietrze.gov.pl/`). Edycja başlangıç tarihi ve kuralların program belgelerindeki karşılığı **do weryfikacji** (05/06 yok); her kuralın `notes` alanında belirtildi. | Uydurma ayrıntılı kaynak/paragraf yerine doğrulanabilir kök kaynak. |
| G2 | Referans tarihi: wniosek `application_date` → umowa/oferta `contract_date` → sprawa oluşturma tarihi. „Bugün” kullanılmaz (sonuç günden güne değişmesin). | „Kurallar dosya tarihine göre seçilir”. |
| G3 | Tutarlılık çoğunluk oyuyla yapılır; tam çoğunluk yoksa hatalı belge atanmadan tek bulgu üretilir. Aneks varsa ürün alanları aneks öncesi {wniosek, umowa/oferta} ve sonrası {aneks, faktura, protokół, karta} olarak ayrı karşılaştırılır; değişikliği PRD-03 „uzgodniona zmiana” olarak bildirir. | Gerçek vakada 3–6 belge; uzgodniona zmiana yanlış alarm olmamalı. |
| G4 | Wniosek tutarları faturayla karşılaştırılmaz (wniosek planlanan maliyettir; aneks sonrası farklı olması olağan). Fatura satır toplamı kalem satırları okunmadığı için `netto + VAT = brutto` kontrolüyle sınırlıdır (F1). | Kapsam ve çift alarm önleme. |
| G5 | Oferta için yalnızca wykonawca imzası zorunlu; umowa, aneks ve protokół için iki imza. Okunamayan imza „eksik” sayılmaz (kalite kuralına gider). | Sentetik şablon ve pratik: teklifler müşteri imzası olmadan da geçerli olabilir. |
| G6 | ZUM eşleştirmesi (opsiyonel) yapılmadı: sentetik karta numaraları modele bağlı üretilmiyor; `zum_sample.csv` ile anlamlı bir eşleştirme için synth'in genişletilmesi gerekir. | Opsiyonel kapsam. |
| G7 | Sokak yazım bulgusu (ADR-02), önek ve patron adı/baş harfi dışındaki farkları (diakritik, büyük harf) bildirir. Bu tanımla tutarlı olsun diye sentetik veri tablosu düzeltildi (bazı „olağan” varyantlar farklı yazılıyordu). | Temiz vakalarda sahte bulguyu önlemek; düzeltme `fix:` commit'inde. |
| G8 | Değerlendirme, sprawa'daki son belge işlendiğinde otomatik ve „Sprawdź ponownie” ile elle çalışır; girdi değişmediyse otomatik çalıştırma atlanır. Bulgular silinmez: artık üretilmeyen bulgu `is_current=false` olur. | Faz 6 kararlarının kaybolmaması. |

