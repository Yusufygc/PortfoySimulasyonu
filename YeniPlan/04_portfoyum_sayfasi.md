# 04 — Portföyüm Sayfası

> Ana sayfa: [index.md](index.md) | Günlük: [log.md](log.md) | Önceki: [03_fiyat_ve_kur_hatti.md](03_fiyat_ve_kur_hatti.md) | Sonraki: [05_genel_bakis_ve_haber.md](05_genel_bakis_ve_haber.md)

Durum: **Taslak** (Aşama 1, 4 ve 5)

## 1. Aşama 1 — Sayfa Bölünmesi (davranış korunur)

`DashboardView.qml` şu an `Item > ScrollView > ColumnLayout` yapısında. Taşınacak ve kalacak parçalar:

| Parça | Konum (satır) | Hedef |
|---|---|---|
| Başlık (`dashboardTitle` / `dashboardSubtitle`) | 35-48 | Her iki sayfada kendi başlığı |
| `PriceStatusChip` | 50 | Genel Bakış'ta kalır (Portföyüm'de de gösterilebilir) |
| Sermaye Yönetimi / Excel Raporu / Hızlı Alım-Satım düğmeleri | 59-84 | Portföyüm |
| 4 KPI kartı + 2 dönemsel getiri kartı | 89-166 | Portföyüm |
| `TradingViewToolbar` + hızlı hisse seçici + `TradingViewChart` | 190-245 | Genel Bakış |
| `AssetAllocationCard` | 250-256 | Portföyüm |
| Açık pozisyonlar tablosu | 260-629 | Portföyüm |
| `QuickTradeModal`, `CapitalModal`, `ExcelExportDialog`, `ToastNotification` | 633-659 | Portföyüm |
| `Connections` (`tradeExecuted`, `capitalUpdated`, `excelExported`) | 662-676 | Portföyüm |

`ChartFullscreenModal` grafikle birlikte Genel Bakış'ta kalır. `StockDetailModal` zaten `Main.qml` içinde global.

Kararlar:

- `dashboardController` adı **değişmez**; BIST portföy mantığı olduğu gibi Portföyüm'e bağlı kalır. Böylece `app.py` `pricesChanged` bağı, `conftest.py` içindeki `_reload_returns` monkeypatch'i ve `scripts/qml_visual_snapshot.py` bozulmaz.
- Pozisyon satırı tıklaması önceden `chartView.loadStock()` çağırıyordu; grafik artık aynı sayfada olmadığından satır tıklaması `stockDetailController.openStock` açar. "Grafik" düğmesi `chartController.loadTicker` + `shellController.navigateTo(0)` yapar (diğer sayfalardaki kalıp).
- Dokunulacak dosyalar: `shell_controller.py` (`PAGE_TITLES[10]`), `Main.qml` (yeni Loader), `Sidebar.qml` (`menuItems`, 2. sıra), `Strings.qml` (`navMyPortfolio` ve taşınan metinler; kullanılmayan anahtarlar silinir), `Icons.qml`, `tests/ui_qml/test_qml_poc.py:33`.
- Doğrulama: `test_dashboard_*`, `test_qml_poc`, `test_strings_catalog`, `test_qml_file_size_guard` yeşil; `scripts/qml_visual_snapshot.py`'ye Genel Bakış ve Portföyüm eklenir.

## 2. Aşama 4 — Birleşik Portföy Servisi

`UnifiedPortfolioService` (`src/application/services/assets/` veya `portfolio/`):

- Girdi: BIST `Portfolio` (mevcut `PortfolioService`, `CurrentPriceResolver`) + `AssetLedger` + güncel fiyatlar + kur.
- Çıktı:
  - `UnifiedSummary`: toplam değer (TRY), maliyet, kâr/zarar, günlük değişim, "kısmi" bayrağı.
  - `AllocationBreakdown`: sınıf bazlı dilimler (BIST, ABD hisse, kripto, emtia, nakit) ve varlık bazlı dilimler; BIST nakdi ayrı dilim.
- Gösterim kuru: TRY veya USD; `FxRateService` ile çevrilir.

## 3. Aşama 5 — Arayüz

`views/MyPortfolioView.qml`:

1. Üst şerit: TRY/USD anahtarı, toplam KPI'lar, "kısmi veri" uyarısı.
2. `AssetAllocationCard`: sınıf bazlı dilimlerle (dilim kaynağı `UnifiedPortfolioService`).
3. Sekmeler: **Tümü / BIST / ABD Hisse / Kripto / Emtia**.
   - BIST sekmesi: mevcut pozisyon tablosu.
   - Diğer sekmeler: `AssetPositionsTableModel` (kesirli miktar, kendi para biriminde fiyat, TRY karşılığı, K/Z).
   - Tümü sekmesi: sınıf etiketli birleşik liste.
4. Modallar:
   - `AssetAddModal`: katalogdan seç veya sembolle ekle; çevrimiçi doğrulama sonucu gösterilir.
   - `AssetTradeModal`: kesirli alım/satım, tarih-saat, işlem kuru.
   - Mevcut Sermaye ve Excel modalları BIST için kalır.
5. Emtia satırlarında "vadeli kontrat fiyatı" notu.

Controller'lar (her biri ≤400 satır / 30 metot):

- `MyPortfolioSummaryController`: özet, dilimler, kur anahtarı, sekme filtresi.
- `AssetsController`: varlık listesi, ekleme, işlem kaydı, doğrulama.
- `ThreadPoolExecutor` + Signal kalıbı; ağ gerektiren doğrulama arka planda.

Yeni bileşenler ayrı dosyalarda (QML dosyası ≤900 satır). Metinler `Strings.qml`, emoji yok. Yeni ikonlar (`coins`, `bitcoin` vb.) `src/ui_qml/assets/icons/` altına Lucide SVG olarak eklenir ve `Icons.qml` ile kaydedilir.

## 4. Testler

- Birleşik servis: sahte BIST portföyü + sahte defter + sabit kur; kısmi veri; USD çevrimi; dilim toplamı = 100%.
- Controller: sahte servis; sinyal sırası; hata durumları.
- QML: uyarısız yükleme; boş portföy; `test_qml_views_runtime_smoke.py`'ye ekleme.
