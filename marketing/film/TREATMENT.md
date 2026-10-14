# RenovaCheck – tanıtım filmi tretmanı (60 sn, 1280×720, 16:9, 25 fps)

## Hedef ve izleyici
- **Kimin için:** Czyste Powietrze başvurularını hazırlayan ve kontrol eden firmalar: enerji
  denetçileri, başvuru operatörleri, kurulum firmalarının evrak ekipleri.
- **Ne zaman:** satış görüşmesinin ilk dakikası, web sitesi, LinkedIn.
- **Tek cümlelik vaat:** *„Rozbieżność w dokumentach wyłapiesz, zanim zrobi to urząd."* Belgeler
  arasındaki tutarsızlığı kurumdan önce sen yakalarsın.
- **İzleyicinin akılda tutacağı üç şey:**
  1. Belgeler otomatik karşılaştırılır.
  2. Her bulgu sayfadaki kanıtıyla gelir.
  3. Kararı insan verir ve raporu alır.

## Ton ve görsel dil
- **Ton:** sakin, güven veren, net. Korku satmıyoruz; gece mesaisinin yorgunluğunu tanıtıp
  rahatlamayla kapatıyoruz.
- **İki dünya:**
  - **Hikâye sahneleri (Seedance):** belgesel gerçekliği, reklam parlaklığı değil. 35 mm film
    hissi, doğal grain, hafif el kamerası, pratik ışık (masa lambası, pencere), dağınık ve
    yaşanmış bir ofis, doğal cilt dokusu. Pürüzsüz/plastik cilt, HDR, aşırı doygunluk ve kusursuz
    simetri yok: „AI görüntüsü" hissini veren her şeyden kaçınılır.
  - **Ürün sahneleri:** gerçek arayüz kayıtları. Temiz, beyaz, okunur; yavaş push-in.
- **Grafik dili** (`brand/DESIGN.md`): editoryal, belge gibi.
  - Kâğıt beyazı (#FAFAF7) ve mürekkep siyahı (#111418); Geist ve Geist Mono.
  - Sola yaslı düzen, ince çizgiler, `03 — PRD-01` gibi mono sayfa/kod etiketleri.
  - Vurgu yalnızca bir denetçinin kalemi gibi: el çizimi alt çizgi ya da halka. Teal olağan,
    düzeltme kırmızısı (#D9480F) yalnızca uyuşmazlık için.
  - Gradyan, parıltı (glow), gölgeli kart, yuvarlak „pill" etiket, ortalanmış büyük başlık yok.
- **Kurallar:**
  - AI sahnelerinde okunur metin, logo ya da marka yok. Belgeler bulanık, ekranlar görünmez açıda.
  - Arayüz yalnızca gerçek kayıtlardan gelir.
  - Tüm veriler sentetik: kişi, firma, NIP ve adresler `tools/synth`'ten. Altbilgide
    „Prototyp · prezentowane dane są syntetyczne" yazar.
- **Karakter:** Marta (kurgu), 35 yaşlarında, küçük bir enerji danışmanlık ofisinde başvuruları
  kontrol ediyor. Tüm AI çekimlerinde aynı referans görselle tutarlı tutulur.

## Yapı (beat sheet)
| Zaman | Bölüm | Duygu | Görüntü |
|---|---|---|---|
| 0–14 sn | Sorun | yorgunluk, gerilim | Belge yığını → akşam karşılaştırma → tek karakterlik fark |
| 14–18 sn | Dönüm | merak | Logo açılışı, slogan |
| 18–46 sn | Çözüm | kontrol, netlik | Yükleme → bulgular → sayfadaki kanıt → karar → kapatma ve PDF rapor |
| 46–56 sn | Sonuç | rahatlama, güven | Ertesi sabah teslim, güven etiketleri → ısı pompalı ev, el sıkışma |
| 56–60 sn | Çağrı | eylem | Kapanış kartı: logo, slogan, „Umów prezentację", iletişim |

## Müzik ve ses
- **Müzik:** sıcak, modern kurumsal underscore. 0–14 sn minimal ve hafif gergin (tek piyano notası,
  nabız); 14 sn'de logo ile açılır; 46 sn'den itibaren yükselen, umutlu çözüm; 56–60 sn kadans.
  Vokal yok; ~96 BPM.
- **Ses efektleri:** kâğıt hışırtısı (S01), logo „whoosh" (S04), yumuşak arayüz tıklamaları.
- **Seviye:** seslendirme önde. Müzik konuşma altında −8 dB ducking; toplam −14 LUFS (web).

## Dürüstlük
- **Kapsam:** ürün TRL3 prototipi. Filmde vaat yalnızca ürünün bugün yaptıklarıdır: alan okuma,
  kurallarla karşılaştırma, kanıt, insan kararı, rapor.
- **Rakam:** yüzde ya da başarı oranı söylenmez. Gerekirse yalnızca „na danych testowych"
  notuyla verilir.
- **Kurum:** „urząd" genel bir ifadedir; hiçbir kurum adı ya da logosu kullanılmaz.
