# Demo senaryosu (≤ 5 dakika)

Tek bir sentetik sprawa'yı baştan sona gösterir: yükleme → sınıflandırma → alan okuma → kurallar →
inceleme ve karar → kapatma → olay günlüğü. Tüm veriler sentetiktir (`tools/synth`).

## Hazırlık (demo öncesi, bir kez)

```bash
make up      # yığın ayağa kalkar, demo hesapları oluşturulur
make synth   # data/synth/ altına 20 sentetik sprawa
```

Demo dosyaları: `data/synth/SYN-2026-012/documents/` (6 PDF: wniosek, oferta, faktura, faktura
korygująca, protokół odbioru, karta produktu). Bu sprawa'da üç beklenen bulgu vardır:

- karta produktu'da model varyantı değiştirilmiş (**krytyczne**);
- faturada sokak farklı yazılmış (**informacja**);
- korekta faturası (**informacja**).

Giriş: <http://localhost:8080>, `weryfikator@alfa.test` / `renova-demo`.

## Akış

| Süre | Adım | Ne gösterilir |
|---|---|---|
| 0:00 | **Sprawy → „Nowa sprawa”**: sygnatura `DEMO/1`, başlık „Pompa ciepła — dom jednorodzinny” | Organizasyon izolasyonu: yalnızca kendi organizasyonun sprawy'ları görünür; sağ üstte rol. |
| 0:30 | **„Wgraj dokumenty”**: 6 PDF'i birlikte seç → „Wgraj” | Dosya türü içerikten doğrulanır, aynı dosya ikinci kez eklenmez. Sayfa kendiliğinden yenilenir; ~10 saniyede tüm belgeler „Przetworzono”. |
| 1:00 | **Dokumenty** tablosu | Tür otomatik (güvenle), „pola: N” okunan alan sayısı. Bir belge adına tıkla → sayfa görüntüsü üzerinde alan kutuları, satıra gelince kutu vurgulanır. |
| 1:45 | **Ustalenia** kartı | Kurallar son belge işlenince kendiliğinden çalıştı; her bulgu „do sprawdzenia”. Başlıkta hangi tarihte geçerli kuralların (16) kullanıldığı. |
| 2:00 | **„Zamknij sprawę”** | Reddedilir: „1 ustalenie krytyczne czeka na decyzję” — critical bulgu kararsız kapanamaz. |
| 2:15 | Krytyczne bulguya tıkla → **inceleme ekranı** | Solda karta produktu sayfası, model kutusu vurgulu; sekmelerde diğer belgeler (bağlam, kesik çizgili kutu). Sağda kural `PRD-01 v1`, gerekçe, kural kaynağı, okuma güveni, kanıt tablosu (her belgedeki değer). |
| 3:00 | **„Rozbieżność”** + yorum („Karta produktu dla modelu B; poproszono o właściwą kartę”) → „Zapisz decyzję” | Yorum critical'da zorunludur (boş bırakılırsa hata). Kayıttan sonra sıradaki açık bulguya geçer. |
| 3:30 | Bilgi bulguları: **„Zgodne”** (yorumsuz) | Sokak yazımı: „ul. Kosciuszki” = „ul. Tadeusza Kościuszki”; korekta: düzeltilmiş toplam gösterilir. |
| 4:00 | Sprawa'ya dön → **„Zamknij sprawę”** | Bu kez kapanır; yükleme ve tür değiştirme gizlenir. |
| 4:20 | **Dziennik zdarzeń** (sprawa sayfasının altı) | Yükleme, analiz, kural çalıştırma, her karar (karar türüyle), durum değişiklikleri; kim ve ne zaman. Kayıtlar değiştirilemez (veritabanı tetikleyicileri + hash zinciri). |
| 4:40 | Üst menü **Sprawy** | Listede ciddiyet rozetleri; „otwarte: krytyczne” filtresi kararsız kritik bulgusu olan sprawy'ları gösterir. |

## Sık sorulanlar

- **Karar değiştirilebilir mi?** Evet, yeni karar eklenir; önceki „Historia decyzji”de kalır.
  Belgeler değişip bulgunun değerleri farklılaşırsa bulgu „do ponownej weryfikacji” olur.
- **Kural nereden geliyor?** `packages/rules/rules/*.yaml`; her kuralın kaynağı, geçerlilik
  tarihi ve sürümü var. Eski sprawy kendi tarihindeki kurallarla değerlendirilir.
- **Skanlar?** OCR ile okunur. Değerler bulgu gerekçesinde „odczytana przez OCR” notuyla
  işaretlenir; ayrıca kalite bulgusu (`QLT-01`) üretilir.

Otomatik prova: aynı akış Playwright ile ~15 saniyede tamamlanır (ekran görüntüleri
`docs/screens/phase6/`).
