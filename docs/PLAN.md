# RenovaCheck – Prototip planı (TRL 3, 14 gün)

**Hedef:** Sentetik belgelerle uçtan uca çalışan ince prototip: yükle → sınıflandır → alan çıkar (provenanslı) → deterministik kurallar → insan kararı → rapor + ölçüm. Tam MVP değil.

**Girdi durumu:** `docs/03,05,06,07,08` bu ortamda yok; kapsam başlangıç promptundaki özetlerden alındı (bkz. `ASSUMPTIONS.md` A1–A4). Ayrıntılı yeniden kullanım kararları: `REUSE_INVENTORY.md`.

## 1. Mimari (sabit kararlar + uygulama ayrıntıları)

```
            ┌──────────────── docker compose ─────────────────────────────────┐
 tarayıcı ─►│ web (Laravel 11, PHP 8.3, Blade+Tabler, Fortify auth)           │
            │   │  ├─ queue (aynı image, `php artisan queue:work redis`)        │
            │   │  └─ Postgres 16  (RLS: organization_id = app.organization_id)│
            │   ▼                                                            │
            │ extract (FastAPI, Py 3.12) ── durumsuz HTTP: render/ocr/classify │
            │   │                              extract/evaluate-rules        │
            │   └─ worker (aynı image): uzun işler, eval, OCR benchmark       │
            │ Redis 7 (kuyruk) · MinIO (S3, private bucket, signed URL)        │
            └────────────────────────────────────────────────────────────────┘
 packages/rules  : fields.yaml, doc_types.yaml, rules/*.yaml, schema/*.json, zum_sample.csv
 tools/synth     : sentetik sprawa + ground truth üreteci (reportlab, Pillow)
```

| Konu | Karar | ADR |
|---|---|---|
| Monorepo düzeni | `apps/web`, `services/extract`, `packages/rules`, `tools/synth`, `infra/`, `docs/` | 0001 |
| Kiracı izolasyonu | Her iş tablosunda `organization_id` + `ENABLE/FORCE ROW LEVEL SECURITY`; uygulama tablo sahibi olmayan `renova_app` rolüyle bağlanır; middleware her istek/işte `set_config('app.organization_id')` yazar, istek/iş sonunda temizler. Uygulama katmanında ayrıca global scope (çift kilit). | 0002 |
| Web ↔ extract | Laravel kuyruk işi (Redis) orkestrasyonu yapar ve sonuçları **tek yazar** olarak DB'ye kaydeder; extract servisi DB'ye yazmaz, dosyaya MinIO'dan kısa ömürlü signed URL ile erişir. Python `worker` süreci toplu işler (eval, OCR kıyaslama, gürültülü skan OCR) içindir. | 0003 |
| Provenans | Her değer `{value, doc_id, page, bbox, method, confidence}`; bbox sayfaya göre normalize [0..1]. Kaynaksız değer reddedilir; okunamayan alan `unreadable`; varsayılan değerle doldurma yok. Pydantic modelinde "parse, don't validate": `ExtractedValue` yalnızca kaynakla kurulabilir. | 0007 |
| OCR | `OcrAdapter` arayüzü: `PdfTextLayer` (temiz metin, varsayılan, test modu), `TesseractPol`, `AzureDocumentIntelligence` (Poland Central), `GoogleDocumentAI`. Seçim `RENOVA_OCR_PROVIDER`. | 0008 |
| LLM | Yalnızca ekstraksiyon yardımcısı, varsayılan `off`; `fake` modu CI için. Sıcaklık 0, çıktı Pydantic şemasıyla doğrulanır, her değer sayfa metninde normalize string-match ile bulunmazsa düşer. Kural kararı vermez. | 0009 |
| Kural motoru | Saf Python, deterministik; YAML kuralları JSON Schema ile doğrulanır; dosya tarihine göre `valid_from/valid_to` seçimi; kural değişikliği = yeni `version` + regresyon fixture'ı. | 0010 |
| Bulgu yaşam döngüsü | Her bulgu `do_sprawdzenia` doğar; karar: `zgodne / rozbieżność / uzgodniona_zmiana / nie_dotyczy` + yorum (critical'da yorum zorunlu). Onaysız `critical` rapora "onaylı" girmez. Kararlar ve tüm durum değişiklikleri append-only `audit_events`'e yazılır (UPDATE/DELETE trigger ile engelli + hash zinciri). | 0005, 0011 |
| PDF kütüphaneleri | pdfplumber (MIT), pypdfium2 (Apache/BSD), reportlab (BSD), Pillow. PyMuPDF (AGPL) yok. Laravel rapor PDF'i: `barryvdh/laravel-dompdf`. | 0008 |
| UI | Tabler (MIT) vendored, Blade bileşenleri, Alpine.js; dil PL (`lang/pl.json`), i18n altyapısı PL/EN. | — |
| Belge alma ve sınıflandırma | Magic-byte doğrulama, SHA-256 tekilleştirme, opsiyonel ClamAV, private bucket + kısa ömürlü imzalı URL; anahtar kelime sınıflandırıcı (`doc_types.yaml`), metin katmanı yoksa OCR. | 0006 |
| Nesne deposu | MinIO upstream imajları Docker Hub'dan kalktı → topluluk derlemesi `pgsty/minio` (sabit sürüm). | 0004 |

## 2. Fazlar, işler, kabul kriterleri

Her fazın başında kullanılan skill'ler tek satırla yazılır; faz sonunda test + `feat:/fix:/test:/docs:` commit'leri + push + kısa rapor (yapılan, test edilen, ölçümler, açık riskler, sonraki adım).

### Faz 1 – İskelet (gün 1–2)
Skill: `docker-skills:docker-compose-patterns` (compose/healthcheck), `backend-design:design` + `schema-reviewer` (org/rol şeması, RLS), `coding-skills:index-design` (FK/organization_id indeksleri), `zizi-skills:tabler-ui` (layout), `engineering:testing-strategy` (test piramidi).
- compose: `web`, `queue`, `extract`, `worker`, `postgres:16`, `postgres-test` (tmpfs), `redis:7`, `minio` + bucket init; `Makefile`: `up, down, reset, seed, test, lint, synth, eval`.
- Laravel 11: Fortify auth (giriş/çıkış), `organizations`, `users`, `memberships(role: owner|reviewer)`, Gate'ler, RLS migration'ları, `SetTenantContext` middleware, Tabler layout + PL çeviriler, seed (2 organizasyon, 3 kullanıcı).
- extract: careos iskeletinden config/logging/errors/middleware, `/health`, `/ready`.
- Testler: auth, rol yetkileri, **organizasyon izolasyonu** (uygulama katmanı + doğrudan SQL ile RLS), pgTAP RLS baseline, pytest health.
- CI (GitHub Actions): Pint + PHPUnit (Postgres servis), ruff + mypy + pytest, pgTAP; aksiyonlar SHA'ya pinli.
- `README.md` (kurulum, mimari şeması, komutlar), `docs/ADR/0001–0003`.
- **Kabul:** `make up && make test` yeşil; CI yeşil.

### Faz 2 – Sentetik belge üreteci (gün 2–4)
Skill: `coding-skills:parse-dont-validate` (ground truth modelleri), `zizi-skills:tdd-skill`.
- `tools/synth`: 20 sprawa × 5 belge (wniosek_ekstrakt, oferta|umowa, faktura [+%30 korygująca/zaliczkowa], protokół odbioru, karta produktu); Lehçe şablonlar (adres/NIP/kod pocztowy, "Szanowni Państwo", VAT 8/23, netto/brutto satırları); deterministik seed.
- Hata enjeksiyonu: adres no 12↔21, cadde yazım varyantı, model A↔B, moc 8↔10 kW, protokół eksik, netto/brutto karışması, zaliczka toplam farkı, uzgodniona zmiana (aneks), düşük kalite skan (PDF→PNG→gürültü/eğim→PDF).
- Ground truth JSON (alanlar + sayfa + bbox + ekilen hatalar + beklenen bulgular) + JSON Schema doğrulama.
- **Kabul:** `make synth` 100 belge üretir; tüm ground truth şema doğrulamasından geçer; aynı seed → aynı çıktı (hash testi).

### Faz 3 – Alma ve sınıflandırma (gün 4–5)
Skill: `backend-design:security-discipline`, `backend-design:idempotency-and-side-effects`, sonunda `backend-design:security-reviewer` ajanı.
- Sprawa oluşturma, çoklu upload (Livewire/Alpine), magic-byte tip doğrulama (PDF/PNG/JPEG), boyut/sayfa limiti, SHA-256 ile tekrar yükleme tespiti, ClamAV (compose profili `av`, varsayılan kapalı), private MinIO + signed URL.
- extract: sayfa render (PNG 150 dpi) + metin katmanı; anahtar kelime sınıflandırıcı (`packages/rules/doc_types.yaml`) + güven; kullanıcı tür düzeltmesi (audit'li).
- **Kabul:** sentetik sette tür doğruluğu ≥ %95 (`make eval` çıktısında); güvenlik incelemesi bulguları kapatılmış.

### Faz 4 – Ekstraksiyon + provenans (gün 5–8)
Skill: `coding-skills:parse-dont-validate`, `zizi-skills:tdd-skill`, `coding-skills:unicode-pitfalls` (diakritik normalizasyonu).
- `packages/rules/fields.yaml` alan sözlüğü; deterministik çıkarıcılar (anchor/regex/tablo satırı), normalizasyon (adres: diakritik/kısaltma `ul.`/`al.`; model: büyük-küçük/tire/boşluk; tutar `1 234,56 zł` → Decimal), `unreadable` durumu.
- OCR adaptörleri (Tesseract gerçek; Azure/Google kayıtlı yanıt fixture'larıyla), opsiyonel LLM yardımcısı (string-match zorunlu).
- **Kabul:** `make eval` alan bazında precision/recall tablosu; temiz PDF'de ≥ %95; gürültülü skan ayrı satırda raporlanır.

### Faz 5 – Kural motoru (gün 8–10)
Skill: `zizi-skills:tdd-skill`, `coding-skills:metamorphic-testing` (normalizasyon/kural değişmezlikleri).
- 4 aile: (a) adres/inwestor, (b) producent/model/moc (+ opsiyonel `zum_sample.csv`), (c) tutar: satır toplamı vs oferta/umowa — netto/brutto/VAT/zaliczka/korekta farkındalığı, sonuç her zaman `do_sprawdzenia` + gerekçe, (d) eksik belge + tarih kuralları (faktura ≥ umowa tarihi vb.).
- Her kuralda `source_url`, `valid_from` dolu; kural şeması CI'da doğrulanır; kural başına regresyon fixture'ı.
- **Kabul:** `make eval` çıktısında kural başına TP/FP/FN.

### Faz 6 – İnceleme ekranı (gün 10–12)
Skill: `frontend-design:frontend-design` + `zizi-skills:tabler-ui` (yoğun veri ekranı), `design-skills:ux-writing` (PL mikro metin), sonunda `backend-design:security-reviewer`.
- Sprawa listesi (filtre: durum/ciddiyet) → sprawa detay (belgeler, alanlar, bulgular) → bulgu paneli: ciddiyet, kural, gerekçe, güven + kaynak sayfa görüntüsü bbox vurgulu yan yana → karar + yorum → değiştirilemez olay günlüğü.
- Playwright ile ekran görüntüleri `docs/screens/`; demo senaryosu `docs/DEMO.md` (≤ 5 dk).
- **Kabul:** tek sentetik sprawa baştan sona 5 dakikada gösterilebilir; güvenlik incelemesi bulguları kapatılmış.

### Faz 7 – Rapor + ölçüm (gün 12–14)
Skill: `engineering:testing-strategy`, `dataviz` (rapor tabloları/grafikleri gerekirse).
- PDF/CSV kontrol raporu (bulgular, kararlar, kim/ne zaman; onaysız critical "niezatwierdzone" olarak ayrı bölümde).
- `make eval` → `docs/EVAL_REPORT.md` otomatik (sınıflandırma, alan P/R temiz/gürültülü, kural FP/FN, süreler).
- `tools/ocr_bench`: Azure vs Google vs Tesseract, 200 sayfa (sentetik setten), maliyet/sayfa notu; anahtar yoksa ilgili sütun "uruchomienie pominięte" olarak raporlanır.
- **Kabul:** `docs/EVAL_REPORT.md` tek komutla üretilir.

## 3. Yapılmayacaklar (kapsam koruması)
Enerji hesabı, audyt/świadectwo üretimi, hibe kararı, GWD/kurum entegrasyonu, otomatik gönderim, gerçek müşteri verisi, mobil uygulama, çok aileli bina, birden fazla program. Bu listeye giren bir istek gelirse hatırlatılır.

## 4. Riskler

| Risk | Etki | Önlem |
|---|---|---|
| Kaynak dokümanlar (03–08) yok | Alan sözlüğü/kurallar gerçek belge setinden sapabilir | Prompt özetleriyle ilerle; dokümanlar gelince fark listesi çıkar (`ASSUMPTIONS.md`) |
| Laravel 11 güvenlik desteği bitti (Mart 2026) | Prototip için kabul edilebilir, üretim için değil | Sabit karar korunur; 12'ye geçiş ayrı ADR adayı |
| Kural `source_url`/`valid_from` gerçek program belgesine dayanmalı | Yanlış kural tarihi | Resmi Czyste Powietrze sayfaları kaynak gösterilir, her kural `notes: do weryfikacji` ile işaretlenir |
| Sentetik veri ezberi (synth ile çıkarıcı aynı şablonu bilir) | %95 metriği şişebilir | Üreteçte şablon varyantları (≥3/tür), ayrı "holdout" seed; eval raporunda açıkça belirtilir |
| Bulut OCR anahtarları yok | Faz 7 kıyaslaması eksik kalır | Tesseract gerçek ölçülür; Azure/Google anahtar verilince aynı script |
| Bu cloud oturumunda Docker daemon elle başlatıldı | Ortam yeniden başlarsa kaybolur | Testler compose'suz da (yerel PHP 8.3 + Postgres 16) çalışabilecek şekilde |
| RLS + uzun ömürlü bağlantılar (kuyruk) | Yanlış tenant bağlamı sızıntısı | Bağlam her istek/iş sonunda temizlenir (`TenantContext::run`), mod_php kalıcı bağlantı kullanmaz; izolasyon testleri CI'da zorunlu |
| GitHub reposu public | Plan/doküman görünür | Gerçek veri yok; gerekirse repoyu private'a almak senin kararın |

## 5. Engelleyici sorular (yanıt gelmezse varsayılanla ilerlenir)

1. **Kendi repolarından kod kopyalama izni.** careos/emlakpro/konstela "Copyright (c) 2026 Sergen Şahin. All rights reserved." taşıyor. Bunlar senin; RenovaCheck'e kopyalamama/uyarlamama izin veriyor musun? *Varsayılan: evet — dosya başına kaynak satırı + kökte `NOTICE.md`.*
2. **Kaynak dokümanlar.** 03/05/06/07/08 dosyalarını bu repoya (`docs/`) ekleyebilir misin? *Varsayılan: prompt özetleriyle devam; gelince fark analizi.*
3. **Laravel sürümü.** Prompt Laravel 11 diyor; 11'in güvenlik desteği bitti. 11'de mi kalayım, 12'ye mi geçeyim? *Varsayılan: 11 (sabit karar).*

## 6. Skill/plugin envanteri

Promptta istenen tüm skill'ler bu oturumda **mevcut**: `frontend-design:frontend-design`, `backend-design` (skill'ler: `design`, `audit`, `review-migration`, `security-discipline` …; ajanlar: `schema-reviewer`, `security-reviewer`, `component-architect`), `zizi-skills:tabler-ui`, `zizi-skills:tdd-skill`, `coding-skills:parse-dont-validate`, `coding-skills:index-design`, `docker-skills:docker-compose-patterns`, `engineering:testing-strategy`. Eksik yok.
Ek olarak kullanılacaklar: `coding-skills:unicode-pitfalls`, `coding-skills:metamorphic-testing`, `design-skills:ux-writing`, `backend-design:migration-safety`.

## 7. Çalışma düzeni
- Her faz sonunda commit + push. Geçmiş yeniden yazılmaz.
- Commit/kod/dokümanda AI atfı yok; lisans/telif satırları korunur.
- Tüm demo/test verisi yalnızca `tools/synth` çıktısı.
