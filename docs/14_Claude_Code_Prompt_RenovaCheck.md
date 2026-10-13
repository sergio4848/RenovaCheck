# RenovaCheck – Claude Code başlangıç promptu

Kullanım: Windows'ta boş bir klasörde (`mkdir renovacheck && cd renovacheck`) Claude Code'u aç, `docs/` klasörüne başvuru paketindeki 03, 05, 06, 07, 08 numaralı .md dosyalarını kopyala, sonra aşağıdaki metni olduğu gibi yapıştır. `gh` CLI'nin oturum açmış olması gerekir (`gh auth status`).

---

Sen bu projede kıdemli full-stack mühendis ve teknik kurucu ortağımsın. Ürünün adı **RenovaCheck**: Polonya'da bina enerji yenileme (termomodernizacja) projelerinin belgelerini hazırlayan/kontrol eden firmalar için, aynı dosyaya ait farklı belgeler (wniosek özeti, oferta/umowa, faktura, protokół odbioru, karta produktu) arasında tutarlılık ve eksik belge kontrolü yapan B2B SaaS. Fikir aşamasındayız; hedef, **2 haftada sentetik belgelerle çalışan ince bir prototip (TRL 3)** üretmek. Tam MVP değil. Kapsamı büyütme.

## 0. Önce keşif, sonra plan (kod yazmadan önce)

1. `docs/` klasöründeki dosyaları oku: `03_*` (ürün tanımı, Lehçe), `05_*` (rakipler ve Czyste Powietrze belge seti), `06_*` (MVP kapsamı + mimari), `07_*` (ölçüm planı), `08_*` (iş modeli). Ürün sınırlarını ve "yapmayacaklarımızı" buradan al; çelişki görürsen sor.
2. Kullanabileceğin yetenekleri envanterle: mevcut skill/plugin listesini çıkar (`/skills` veya `ls ~/.claude/skills`, `~/.claude/plugins`). Bu projede özellikle şunları aktif kullan, yoksa söyle: `frontend-design`, `backend-design` (design/audit/schema-reviewer/security-reviewer), `zizi-skills:tabler-ui`, `zizi-skills:tdd-skill`, `coding-skills:parse-dont-validate`, `coding-skills:index-design`, `docker-skills:docker-compose-patterns`, `engineering:testing-strategy`. Her fazın başında hangi skill'i neden kullandığını tek satırla yaz.
3. GitHub'ımı tara ve yeniden kullanılabilir parçaları çıkar: `gh repo list sergio4848 --limit 50` ile listele; **Konstela, CareOS, EmlakPro** ve Laravel/Django içeren diğer repoları klonlayıp (`/tmp/scan/`) şunları ara: auth/organizasyon-rol iskeleti, layout ve bileşen kütüphanesi (Tailwind/Tabler/Blade bileşenleri), tablo/filtre/liste ekranları, dosya yükleme ve önizleme, PDF/rapor üretimi, kuyruk işleri, test düzeni, CI. `docs/REUSE_INVENTORY.md` yaz: repo → dosya → ne işe yarar → RenovaCheck'te nerede kullanılır → "kopyala / uyarlayarak al / alma" kararı. Lisans/attribution satırlarını koru. Kod kopyalarken telif/lisans dosyalarını taşı.
4. Sonra `docs/PLAN.md` yaz: fazlar, kabul kriterleri, riskler, bana sorman gereken **yalnızca engelleyici** sorular (en fazla 5). Onayımı bekle, sonra uygula.

## 1. Sabit mimari kararları (tartışma yok)

- Monorepo: `apps/web` (Laravel 11, PHP 8.3, Blade + Tabler UI veya repolarımdan çıkan bileşen seti; Livewire/Alpine serbest, SPA yok), `services/extract` (Python 3.12, FastAPI + worker), `packages/rules` (YAML kural seti + şema), `tools/synth` (sentetik belge üreteci), `docs/`.
- PostgreSQL 16 (organizasyon bazlı veri ayrımı: `organization_id` + row-level security), Redis (kuyruk), S3-uyumlu depolama (MinIO yerelde), docker-compose ile tek komutla ayağa kalkar (`make up`, `make seed`, `make test`).
- OCR adaptör arayüzü: `AzureDocumentIntelligence` (Poland Central), `GoogleDocumentAI`, `TesseractPol` (yerel yedek). Seçim env ile. Hiçbir adaptör olmadan da test suite'i sentetik "temiz metin" modunda geçmeli.
- LLM yalnızca ekstraksiyon yardımcısı; çıktısı şema ile doğrulanır ve **her alan sayfa metninde string-match ile bulunmak zorundadır**, bulunamazsa alan düşer. LLM kural kararı vermez. Sıcaklık 0. Sağlayıcı env ile, varsayılan kapalı.
- Her çıkarılan değer: `{value, doc_id, page, bbox, method, confidence}`. Kaynaksız değer kabul edilmez. Belgede olmayan değer asla "varsayılan" ile doldurulmaz; okunamayan alan `unreadable` olur.
- Kural motoru deterministik. Kural = YAML: `id, title_pl, program, edition, valid_from, valid_to, severity (critical|warning|info), inputs, comparator, threshold, source_url, notes`. Kurallar dosya tarihine göre seçilir. Kural değişikliği = yeni versiyon + regresyon testi.
- Bulgu (finding) her zaman "do sprawdzenia" statüsünde doğar; `critical` bulgular insan kararı (`zgodne | rozbieżność | uzgodniona zmiana | nie dotyczy` + yorum) olmadan rapora "onaylı" girmez.
- UI dili Lehçe (i18n altyapısı PL/EN; metinler `lang/pl.json`). Tasarım: sade, yoğun veri ekranı; kaynak sayfa görüntüsü bulgunun yanında, bbox vurgulu.

## 2. Fazlar ve kabul kriterleri

**Faz 1 – İskelet (gün 1–2):** docker-compose, Laravel auth + organizasyon + rol (owner/reviewer), Python servisi health endpoint, CI (lint + test), `README.md` (kurulum, mimari şeması, karar günlüğü `docs/ADR/`). Kabul: `make up && make test` yeşil.

**Faz 2 – Sentetik belge üreteci (gün 2–4):** `tools/synth` ile 20 "sprawa" × 5 belge üret: `wniosek_ekstrakt`, `oferta` veya `umowa`, `faktura` (+ %30 olasılıkla `faktura korygująca`/zaliczkowa), `protokół odbioru`, `karta produktu`. Gerçekçi Lehçe şablonlar (ad/adres/NIP/ulica/kod pocztowy formatları, "Szanowni Państwo", VAT 8/23, netto/brutto satırları). Her sprawa için **ground truth JSON** (alanlar + bilerek ekilmiş hatalar). Hata enjeksiyonu: adres numarası 12↔21, cadde yazım varyantı, model A↔B, güç 8 kW↔10 kW, protokół eksik, netto/brutto karışması, zaliczka nedeniyle toplam farkı, uzgodniona zmiana senaryosu, düşük kalite skan (PDF→PNG→gürültü/eğim→PDF). Kabul: `make synth` 100 belge üretir; ground truth şema doğrulamasından geçer.

**Faz 3 – Alma ve sınıflandırma (gün 4–5):** yükleme, virüs/boyut kontrolü, sayfa görüntüleri, belge türü sınıflandırma (önce kural/anahtar kelime, sonra opsiyonel model), kullanıcı düzeltmesi. Kabul: sentetik sette tür doğruluğu ≥ %95.

**Faz 4 – Ekstraksiyon + provenans (gün 5–8):** alan sözlüğü (`packages/rules/fields.yaml`: adres bileşenleri, inwestor, producent/model/moc, kwota netto/brutto/VAT, daty, numer faktury, podpis var/yok), deterministik çıkarıcılar (regex/anchor/tablo), opsiyonel LLM yardımcı, normalizasyon (adres: diakritik/kısaltma; model: büyük-küçük, tire, boşluk; tutar: `1 234,56 zł`). Kabul: ground truth'a göre alan bazında precision/recall tablosu (`make eval`), temiz PDF'de ≥ %95, gürültülü skanda raporlanır (eşik yok, ölçüm var).

**Faz 5 – Kural motoru (gün 8–10):** 4 aile: (a) adres/inwestor tutarlılığı, (b) producent/model/moc tutarlılığı (ZUM eşleştirmesi opsiyonel: `packages/rules/zum_sample.csv` ile), (c) tutar: faktura satır toplamı vs oferta/umowa — netto/brutto/VAT/zaliczka/korekta farkındalığı, sonuç her zaman "do sprawdzenia" + gerekçe, (d) eksik belge + tarih kuralları (örn. fatura tarihi > sözleşme tarihi; kural tarihli). Kabul: kural başına FP/FN sayıları `make eval` çıktısında; her kuralın `source_url` ve `valid_from` alanı dolu.

**Faz 6 – İnceleme ekranı (gün 10–12):** sprawa listesi → sprawa detay → bulgular (ciddiyet, kural, gerekçe, güven) → kaynak sayfa görüntüsü + bbox vurgusu yan yana → karar + yorum → olay günlüğü (değiştirilemez). Kabul: tek bir sentetik sprawa'yı baştan sona 5 dakikada gösterebileceğim demo akışı; ekran görüntüleri `docs/screens/`.

**Faz 7 – Rapor + ölçüm (gün 12–14):** PDF/CSV kontrol raporu (bulgular, kararlar, kim/ne zaman), `make eval` ile precision/recall/FP/FN tablosu, OCR kıyaslama scripti (Azure vs Google vs Tesseract, 200 sayfa; maliyet/sayfa notu). Kabul: `docs/EVAL_REPORT.md` otomatik üretilir.

## 3. Yapılmayacaklar
Enerji hesabı, audyt/świadectwo üretimi, hibe kararı, GWD/kurum entegrasyonu, otomatik gönderim, gerçek müşteri verisi, mobil uygulama, çok aileli bina, birden fazla program. Bu listeye giren bir şey istersem bana hatırlat.

## 4. Çalışma kuralları
- Her faz: önce kısa plan, sonra uygulama, sonra test; faz sonunda `feat:`/`fix:`/`refactor:`/`docs:`/`test:` formatında anlamlı commit'ler. Git geçmişini yeniden yazma (rebase --root, force push, filter-repo yok).
- Repo, kod, yorumlar, README, commit mesajları ve PR'larda **hiçbir AI/asistan atfı, disclaimer'ı veya meta açıklaması olmayacak** ("Generated by…", "AI-generated", "Co-Authored-By: …" vb. yok). Kod yorumları yalnızca teknik gerekçe/davranış açıklar. Ürünün kendi LLM/OCR entegrasyon kodu, env değişkenleri ve açıklamaları elbette kalır. Lisans/copyright/üçüncü taraf atıfları asla silinmez.
- Uydurma veri yok: demo ve testler yalnızca `tools/synth` çıktısıyla. Gerçek firma adı/NIP/adres kullanma.
- Güvenlik tabanı: dosya tipi doğrulama, imzalı URL ile indirme, organizasyon izolasyonu testleri, gizli anahtarlar yalnızca env; `backend-design:security-reviewer` ile faz 3 ve 6 sonunda gözden geçir.
- Bana soru sormadan karar ver; yalnızca engelleyici konularda sor. Varsayımlarını `docs/ASSUMPTIONS.md`'ye yaz.
- Her faz sonunda kısa rapor: ne yapıldı, ne test edildi, ölçümler, açık riskler, sonraki adım.

Başla: Adım 0 (keşif + REUSE_INVENTORY + PLAN) ile.
