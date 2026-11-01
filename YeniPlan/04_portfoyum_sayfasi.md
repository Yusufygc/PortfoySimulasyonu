# 04 — Portföyüm Sayfası

> Ana sayfa: [index.md](index.md) | Günlük: [log.md](log.md) | Önceki: [03_fiyat_ve_kur_hatti.md](03_fiyat_ve_kur_hatti.md) | Sonraki: [05_genel_bakis_ve_haber.md](05_genel_bakis_ve_haber.md)

Durum: Aşama 1, 4 ve 5 **Uygulandı** (2026-11-01)

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

## 2. Aşama 4 — Birleşik Portföy Servisi (Uygulandı)

Dosyalar:

| Katman | Dosya |
|---|---|
| Domain | `src/domain/models/unified_portfolio.py` (`AllocationClass`, `HoldingValuation`, `AllocationSlice`, `UnifiedSummary`, `daily_gain`); `Asset.unit_price` (`asset.py`) |
| BIST okuyucu | `src/application/services/assets/bist_holdings_reader.py` (`BistHoldingsReader`) |
| Varlık okuyucu | `src/application/services/assets/asset_holdings_reader.py` (`AssetHoldingsReader`) |
| Servis | `src/application/services/assets/unified_portfolio_service.py` (`UnifiedPortfolioService.get_summary(display_currency)`) |
| Container | `ServiceSet.unified_portfolio_service`; `build_services` aynı `CurrentPriceResolver` ve `StockLookupService` örneklerini paylaşır |
| Test | `tests/domain/test_unified_portfolio_models.py`, `tests/application/services/assets/test_unified_portfolio_service.py`, `tests/application/test_asset_container_wiring.py` |

Kurallar:

- **Birleşim:** BIST açık pozisyonları (`PortfolioService` + `CurrentPriceResolver`) + BIST TRY nakdi + varlık defteri pozisyonları. Toplam değer = pozisyon değerleri + nakit. Nakit yalnızca BIST nakdidir (varlık alımı nakdi etkilemez).
- **Varlık fiyatı:** son fiyat ile son günlük kapanıştan tarihi daha yeni olan seçilir (eşitse son fiyat). Gram birimli madende ons fiyatı gram fiyatına çevrilir (`Asset.unit_price`); değer `miktar × birim fiyat × güncel kur`.
- **Maliyet ve K/Z:** TRY maliyet her alımın kendi kuruyla tutulur; `unrealized_pl_try` kur farkını da içerir.
- **Eksik veri:** fiyat veya kur yoksa pozisyon TRY maliyetiyle değerlenir, `is_priced=False` olur; özet `is_partial` ve `unpriced_symbols` taşır. Hiçbir pozisyon sessizce düşmez.
- **Günlük değişim:** varlığın kendi para biriminde, seçilen fiyatın gününden önceki son kapanışa göre; kur hareketi dahil değildir. Günlük kazanç = bugünkü değer − önceki kapanış değeri.
- **Dağılım:** sınıf bazlı dilimler (BIST, ABD hisse, kripto, emtia, nakit), değere göre azalan; her pozisyonun `weight_pct` değeri toplam değere (nakit dahil) göredir.
- **Gösterim:** `get_summary("USD")` toplamları güncel USD/TRY ile çevirmek için `display_rate` döner (`display_amount`); kur yoksa TRY'ye düşer ve `display_unavailable=True` olur. Yalnızca TRY ve USD desteklenir.

Doğrulama ve bulgu (2026-11-01, gerçek veritabanı kopyası): 7 BIST pozisyonu için toplam değer (260.311,90), maliyet (699.848,88) ve nakit `DashboardController` ile **birebir aynı**. Günlük kazanç farklı: birleşik servis −14.730 ₺ (%-5,36), dashboard −13.780 ₺ (%-5,29). Birleşik servis tam formülü kullanır (bugünkü değer − önceki kapanış değeri); dashboard `bugünkü değer × yüzde` yaklaşığını kullanır ve negatif günlerde farkı küçük, pozitif günlerde büyük gösterir. Dashboard hesabı bu aşamada değiştirilmedi (BIST davranışı korunur); Portföyüm arayüzü (Aşama 5) birleşik değeri göstereceğinden iki ekran arasındaki fark için karar gerekir.

## 3. Aşama 5 — Arayüz (Uygulandı, 2026-11-01)

Portföyüm sayfasının tüm rakamları `UnifiedPortfolioService` üzerinden okunur (BIST sekmesi dahil); `DashboardController` yalnızca BIST modallarına (hızlı al/sat, sermaye, Excel) ve haftalık/aylık BIST getiri kartlarına bağlı kalır. Günlük kazanç tam formülle hesaplanır.

Dosyalar:

| Katman | Dosya |
|---|---|
| Sunum yardımcıları | `src/ui_qml/controllers/portfolio_presenter.py` (para/miktar/yüzde biçimi, satır ve dilim sözlükleri, sekme süzgeci) |
| Model | `src/ui_qml/models/holdings_list_model.py` (`HoldingsListModel`) |
| Denetleyici | `src/ui_qml/controllers/my_portfolio_controller.py` (`myPortfolioController`: özet, TRY/USD, sekme, dilimler), `assets_controller.py` (`assetsController`: varlık ekleme, işlem, fiyat yenileme, öneri) |
| Kayıt | `src/ui_qml/app.py`: iki denetleyici + `pricesChanged` / `portfolioChanged` / `systemReset` / `assetsController.dataChanged` bağlantıları; `AssetsController(autostart=True)` 5 dakikada bir `refresh_latest(only_open=True)` çalıştırır |
| QML | `views/MyPortfolioView.qml`, `components/HoldingsTable.qml` (eski `OpenPositionsTable.qml` yerine), `AssetAddModal.qml`, `AssetTradeModal.qml`; `AssetAllocationCard.qml` artık `slices` özelliğiyle beslenir ve sınıf etiketlerini `Strings.allocationClassName` ile çözer |
| Test | `test_portfolio_presenter.py`, `test_my_portfolio_controller.py`, `test_assets_controller.py`, `test_my_portfolio_view.py` (taze DB, gerçek container, gerçek QML), `test_qml_views_runtime_smoke.py` genişletmesi |

Davranış notları:

- **Sayfa:** TRY/USD anahtarı; "Fiyatları Yenile"; Varlık Ekle / Varlık İşlemi; BIST nakdi, Excel ve hızlı al/sat BIST için aynen. Üstte değerlenemeyen pozisyon uyarısı ve USD kuru bulunamadı uyarısı; 4 KPI kartı birleşik özetten.
- **Dağılım:** sınıf bazlı dilimler (BIST, ABD, kripto, emtia, nakit); donut merkezi nakit dışı payı gösterir.
- **Tablo:** Tümü / BIST / ABD / Kripto / Emtia sekmeleri (adetli); tutarlar seçili para biriminde, fiyatlar varlığın kendi para biriminde; değerlenemeyen pozisyonda "Maliyet" işareti; BIST satırı Grafik / Detay / İşlem, BIST dışı satır İşlem / Kaldır; emtia sekmesinde vadeli kontrat notu.
- **Varlık ekleme:** katalogdan tek tıkla ya da sembolle; doğrulama, geçmiş doldurma, son fiyat ve kur yükleme arka planda; adımlardan biri başarısız olursa varlık yine eklenir ve mesaj bunu belirtir.
- **Varlık işlemi:** kesirli miktar, fiyat ve kur önerisi veritabanından (ağ yok), TRY fiyatlı varlıkta kur gizli; elden fazla satış ve geriye dönük satış servis tarafından reddedilir.
- **Bildirimler:** otomatik fiyat yenilemesi sessizdir; yalnızca "Fiyatları Yenile" ile istenen sonuç ve hatalar gösterilir.
- **Bilinen sınırlar:** haftalık/aylık getiri kartları yalnızca BIST'tir (etiketlerde "(BIST)"); birleşik TWR v2. BIST nakdi dışında varlık nakdi yoktur. Ofscreen anlık görüntüde yazılar kutu çizildiği için yatay genişlik doğrulaması güvenilir değildir; gerçek pencerede kontrol edilmelidir.

### Özgün plan metni


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
