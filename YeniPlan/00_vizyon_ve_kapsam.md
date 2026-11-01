# 00 — Vizyon ve Kapsam

> Ana sayfa: [index.md](index.md) | Günlük: [log.md](log.md) | Sonraki: [01_mimari_kararlar.md](01_mimari_kararlar.md)

Durum: **Onaylı**

## 1. Neden

Bugün Genel Bakış (`src/ui_qml/qml/views/DashboardView.qml`, 677 satır) hem portföy bilgisini (KPI kartları, pozisyon tablosu, varlık dağılımı, işlem ve sermaye modalları) hem grafiği taşıyor. Uygulama yalnızca BIST hissesi ve TRY varsayımıyla çalışıyor; altın, gümüş, platin, kripto ve ABD hisseleri takip edilemiyor. Repoda haber altyapısı yok.

## 2. Hedefler

1. **Portföyüm sayfası:** Portföy bilgisi Genel Bakış'tan çıkıp yeni bir sayfaya taşınır.
2. **Genel Bakış:** Grafik ve haber akışı (şirket haberleri + global/piyasa haberleri) sayfası olur.
3. **Çoklu varlık:** Portföyüm'de BIST dışı varlıklar (emtia, kripto, NASDAQ hisseleri) eklenir ve takip edilir.
4. **Sınıf bazlı dağılım:** Varlık dağılımı BIST, ABD hisse, kripto, emtia ve nakit sınıflarına göre yeniden tasarlanır.
5. **Haber kaynağı yönetimi:** KAP, yfinance ve Türkçe RSS kaynakları Ayarlar sayfasından tek tek açılıp kapatılır.

## 3. v1 Kapsamı

- Varlık ekleme (katalogdan veya sembolle), kesirli miktarla alım/satım kaydı.
- Değer, maliyet, kâr/zarar, günlük değişim, sınıf bazlı dağılım.
- TRY ana para birimi, USD gösterim anahtarı.
- Genel Bakış'ta global sembolleri de çizen grafik.
- Haber paneli: şirket haberleri ve piyasa/global haberleri, kaynak başına aç/kapa.

## 4. v1 Dışı (v2'ye ertelenen)

| Konu | Not |
|---|---|
| Birleşik TWR getirisi ve risk metrikleri | Yalnızca BIST portföyü için çalışmaya devam eder |
| Optimizasyon evreninde varlık sınıfları | `OptimizationService` BIST odaklı kalır |
| Excel raporunda varlık sayfaları | Mevcut rapor BIST portföyü içindir |
| AI danışman aracı (`get_assets_overview`) | Danışman araçları bilerek salt okunur kalır |
| Benchmark olarak BTC / NASDAQ | `AnalysisBenchmarkService` listesi sabittir |
| Varlık temettü / stake geliri | Yok |
| Varlık nakdi (USD vb.) defteri | Varlık alımı BIST nakdine bağlanmaz (bkz. [01](01_mimari_kararlar.md)) |

## 5. Başarı Ölçütleri

- Genel Bakış'ta portföy bilgisi yoktur; eski tüm portföy işlevleri Portföyüm'de eksiksiz çalışır.
- Altın, BTC ve AAPL eklenip kesirli alım yapılabilir; uygulama yeniden açıldığında veri kalıcıdır.
- TRY/USD anahtarı toplam değeri değiştirir; eksik fiyat veya kur varsa toplam "kısmi" olarak işaretlenir.
- Ayarlar'da bir haber kaynağı kapatılınca o kaynağın haberleri panelden kaybolur.
- Tam test paketi yeşil, kalite ölçümünde ihlal sayısı artmaz.
