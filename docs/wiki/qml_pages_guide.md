> Ana sayfa: [index.md](index.md) | Arayüz mimarisi: [ui_architecture_and_events.md](ui_architecture_and_events.md)

# Sayfa ve Denetleyici Rehberi

Uygulama 11 sayfadan oluşur. Sayfa dizini `ShellController.activePage` değeridir; Portföyüm dizini 10'dur ama kenar çubuğunda Genel Bakış'ın hemen altında (2. sıra) durur (dizinleri kaydırmamak için `Main.qml` StackLayout'una sona eklendi). Diğer sayfalar kenar çubuğunda dizin sırasıyladır. Her bölüm sayfanın amacını, denetleyicisini, kullandığı servisleri ve önemli kurallarını verir. Genel mimari için bkz. [ui_architecture_and_events.md](ui_architecture_and_events.md).

| # | Sayfa | Görünüm | Ana denetleyici(ler) |
|---|---|---|---|
| 0 | Genel Bakış | `DashboardView` | `ChartController`, `NewsController` (grafik + haber paneli) |
| 10 | Portföyüm | `MyPortfolioView` | `MyPortfolioController`, `AssetsController`, `DashboardController` (BIST modalları), `StockDetailController`, `DividendController` |
| 1 | İzleme Listeleri | `WatchlistView` | `WatchlistController` |
| 2 | Model Portföyler | `ModelPortfolioView` | `ModelPortfolioController` |
| 3 | Hisse 360 | `Stock360View` | `Stock360Controller` |
| 4 | Karşılaştırma Lab | `ComparisonView` | `ComparisonController` |
| 5 | Hisse Tarayıcı | `ScreenerView` | `ScreenerController`, `GoldenCrossController` |
| 6 | Finansal Planlama | `PlanningView` | `PlanningController`, `StrategyBacktestController` |
| 7 | Optimizasyon | `OptimizationView` | `OptimizationController`, `RiskProfileController` |
| 8 | AI Asistan | `AiAdvisorView` | `AiAdvisorController`, `ModelAnalysisController` |
| 9 | Ayarlar | `SettingsView` | `SettingsController`, `SystemController`, `PriceDataController`, `CorporateActionController`, `MarketAdjustmentController`, `NewsSettingsController` |

Üst başlık (`WindowHeader`): hisse arama (Genel Bakış grafiğini açar), piyasa şeridi (`MarketTickerController`: altın, gümüş, USD/TRY, EUR/TRY, BIST 100) ve piyasa senkron rozeti.

---

## 0. Genel Bakış

Etkileşimli grafik ve haber akışı; portföy bilgisi bu sayfada **yoktur** (Portföyüm'e taşındı).

- **TradingView grafiği** (`TradingViewChart`, `TradingViewToolbar`): zaman dilimi, mum/çizgi/alan/bar, göstergeler, tam ekran (`ChartFullscreenModal`); hisse detayından açıldığında ortalama maliyet çizgisi gösterilir. Hızlı seçici portföy BIST hisselerini ve Portföyüm varlıklarını (BTC, altın vb.) listeler; BIST dışı semboller varlık defterindeki kapanışlardan çizilir ([service_asset_prices_fx.md](service_asset_prices_fx.md)).
- **Haber paneli** (`NewsPanel`, `NewsController`): "Portföyüm ve İzleme" (şirket haberleri) ve "Piyasa ve Global" sekmeleri. Geniş pencerede (>= 1150 px) grafiğin sağında, dar pencerede altında. Ayrıntı: [service_news.md](service_news.md).
- Fiyat durumu (`PriceStatusChip`): ortak son güncelleme ve küçük yenile ikonu; fiyatlar kendiliğinden güncellenir.

## 0b. Portföyüm

Tüm portföyün (BIST + BIST dışı varlıklar) tek özeti. Rakamların tamamı `UnifiedPortfolioService`'ten okunur ([service_asset_ledger.md](service_asset_ledger.md)).

- **Başlık düğmeleri:** TRY/USD anahtarı, Fiyatları Yenile, Varlık Ekle, Varlık İşlemi, Sermaye Yönetimi, Excel Raporu, Hızlı Alım/Satım. Değerlenemeyen pozisyon ve USD kuru bulunamadı uyarıları sayfanın üstünde görünür; toplam kısmi veriyle hesaplanmışsa işaretlenir.
- **KPI kartları:** toplam değer, günlük kazanç, gerçekleşmemiş K/Z, nakit (BIST). Haftalık/aylık getiri kartları yalnızca BIST'tir (etiketlerde "(BIST)"); birleşik TWR yoktur.
- **Varlık dağılımı** (`AssetAllocationCard`, Canvas donut): BIST, ABD hisse, kripto, emtia ve nakit dilimleri; donut merkezi nakit dışı payı gösterir. Kart yüksekliği içeriğe göre uyar (sınıf sayısı artınca taşmaz); veriden bağımsız sabit "denge durumu" kutusu kaldırıldı.
- **Sayı biçimi:** Portföyüm Türkçe biçim kullanır (`₺1.234,56`, `-₺5.678,99`, `+%2,15`); giriş alanlarına önerilen değerler virgüllü ve kısadır (`74252,4051`). Nakit kartı havuzun tamamıdır (TL + USD karşılığı); USD varsa alt satır `TL ₺… + USD $…` yazar.
- **Haftalık/Aylık Getiri kartları:** Tüm Varlıklar TWR'si (nakit akışından arındırılmış; BIST'e özel değil).
- **Tablo:** Pozisyon tablosu 1440 piksel pencerede (kenar çubuğu açık) eylem sütunuyla birlikte sığar; daha darda yatay kayar. "Kaldır" onay penceresi ister.
- **Pozisyon tablosu** (`HoldingsTable`, `HoldingsListModel`): Tümü / BIST / ABD / Kripto / Emtia sekmeleri; tutarlar seçili para biriminde, fiyatlar varlığın kendi para biriminde; değerlenemeyen pozisyonda "Maliyet" işareti. BIST satırı: Grafik / Detay / İşlem (satıra tıklayınca **Hisse Detay modalı**); BIST dışı satır: İşlem / Kaldır. Emtia sekmesinde vadeli kontrat notu.
- **Varlık ekleme** (`AssetAddModal`): katalogdan tek tıkla veya sembolle; doğrulama, geçmiş doldurma, son fiyat ve kur yükleme arka planda; bir adım başarısız olursa varlık yine eklenir ve mesaj belirtir.
- **Varlık işlemi** (`AssetTradeModal`): kesirli miktar, fiyat ve kur önerisi veritabanından (ağ yok); TL ile işlem gören varlıkta (altın gram dahil) kur gizli; ödeme para biriminin kullanılabilir nakdi ve tahmini ücret gösterilir; elden fazla satış, geriye dönük satış ve yetersiz nakit (USD için 'Önce Döviz Al') reddedilir.
- **Döviz Al/Sat** (`FxConvertModal`, `cashPoolController`): ortak nakit havuzunda TL <-> USD; kur önerisi veritabanından, ücret isteğe bağlı, son 5 döviz işlemi silinebilir. Nakit kartı TL nakdi ve (varsa) USD nakdi gösterir; toplam değer USD nakdi güncel kurla içerir.
- **BIST işlemleri:** hızlı alım/satım (`QuickTradeModal`, tarih ve saat alanlı), sermaye yatırma/çekme (`CapitalModal`), tarihsel Excel raporu (`ExcelExportDialog`; mevcut dosyaya ekleme modu; yalnızca BIST).
- **Hisse Detay modalı** (`StockDetailController`): lot, ortalama maliyet, piyasa değeri, K/Z; işlem geçmişi ve sermaye artırımları sekmeleri; işlem etkisi ön izlemesi; hızlı emir; **Sermaye Artırımı** (`CorporateActionDialog`), **Temettü** (`DividendDialog`), TradingView ve Hisse 360'a geçiş, hisse bazlı Excel. Sermaye artırımı ve temettü yalnızca ana portföy ve açık pozisyon için görünür.
- **Bildirimler:** otomatik fiyat yenilemesi (5 dk, `AssetsController`) sessizdir; yalnızca "Fiyatları Yenile" ile istenen sonuç ve hatalar gösterilir.

Servisler: `UnifiedPortfolioService`, `AssetLedgerService`, `AssetPriceRefreshService`, `FxRateService` (varlıklar); `PortfolioService`, `TradeEntryService`, `CashMovementService`, `ReturnCalcService`, `CurrentPriceResolver`, `ExcelExportService` (BIST). Fiyat ve işlem kuralları: [service_portfolio_and_market.md](service_portfolio_and_market.md).

## 1. İzleme Listeleri

Birden çok liste (sürükle-bırak sıralama), hisse ekleme/çıkarma, hisse notu, mini sparkline (7 günlük trend), kazanan/kaybeden sayacı. Hisse eklerken kod doğrulanır: SQLite veya DuckDB kataloğunda bilinen kod doğrudan eklenir, bilinmeyen kod arka planda çevrimiçi doğrulanır; geçersizse "Geçersiz hisse kodu" gösterilir ve kayıt oluşmaz. Satırdan hızlı işlem ve hisse detayı açılabilir. Bkz. [service_watchlist.md](service_watchlist.md).

## 2. Model Portföyler

Sanal portföyler: oluşturma/düzenleme/silme, sürükle-bırak sıralama, başlangıç sermayesi, sermaye yatırma/çekme, hisse al/sat, fiyat durumu (`PriceStatusChip`; fiyat değişince seçili portföy `reloadPrices` ile DB'den yeniden okunur), tarihsel Excel raporu. KPI: net sermaye, nakit, toplam değer, K/Z (`toplam değer - net sermaye`). Pozisyon satırından hisse detayı açılır (model bağlamı: sermaye artırımı/temettü yok). Bkz. [service_planning_optimization.md](service_planning_optimization.md).

## 3. Hisse 360

Tek hisse için bütünleşik görünüm: genel bakış (fiyat, günlük değişim, 52 hafta aralığı, hacim), teknik seviyeler, değerleme rasyoları, çeyreklik finansal tablolar (bilanço, gelir, nakit akımı), DuPont, gelir grafiği ve KAP ortaklık yapısı (pasta + zaman çizelgesi). Yerel veri anında, dış veri (İş Yatırım, KAP) arka planda gelir. Ayrıntı: [stock_360.md](stock_360.md).

## 4. Karşılaştırma Lab

Portföy, model portföyler, BIST 100, altın, gümüş, USD/TRY, EUR/TRY, mevduat faizi, TÜFE ve hisseler arasında kıyaslama. Ayrıntı: [comparison_lab.md](comparison_lab.md).

## 5. Hisse Tarayıcı

İki sekme: **Strateji Taraması** (10 hazır strateji, tüm BIST, DuckDB'den ~birkaç saniye) ve **Golden Cross** (EMA50/EMA200 kesişimleri, son N gün, tür filtresi, tek hisse geçmişi, "veriyi tamamla"). Satıra çift tıklama grafiği açar, tek tıklama Hisse 360'a götürür. Ayrıntı: [technical_analysis_and_screener.md](technical_analysis_and_screener.md).

## 6. Finansal Planlama

Dört sekme (`PlanningView`):

| Sekme | İçerik |
|---|---|
| Bütçe Yönetimi | Ay seçici, gelir/gider kalemleri, tasarruf hedefi ve durum mesajı, kalemi "pinleme" (boş aylara taslak). |
| Finansal Hedefler | Hedef ekleme/düzenleme/silme, katkı ekleme, ilerleme çubuğu, fizibilite analizi (`PlanningService.analyze_feasibility`). |
| DCA Simülatörü | "Her ay X TL alsaydım" geçmiş simülasyonu; değer eğrisi (Lightweight Charts), toplam yatırılan, nihai değer, getiri, lot dökümü. |
| Strateji Testi | Periyodik yeniden dengeleme (eşit/Markowitz) ve stop-loss/take-profit backtest'i, "al ve tut" karşılaştırması. |

Ayrıntı: [service_planning_optimization.md](service_planning_optimization.md), [service_simulation.md](service_simulation.md).

## 7. Optimizasyon

Markowitz maksimum Sharpe optimizasyonu: kaynak (ana portföy, Tüm Varlıklar veya model portföy), risk profili seçici, tek hisse üst sınırı kaydırıcısı, risksiz faiz oranı. Üç sekme: Verimli Sınır (Monte Carlo bulutu, sınır eğrisi, mevcut/optimum/minimum risk noktaları), Ağırlık Dağılımı, Yeniden Dengeleme (EKLE/AZALT/TUT, tutar ve tahmini lot). Risk anketi `RiskQuestionnaireDialog` ile doldurulur ve kaydedilir; kayıtlı profil tek hisse sınırını belirler. Ayrıntı: [service_planning_optimization.md](service_planning_optimization.md).

## 8. AI Asistan

İki mod: **Portföy Danışmanı** (Gemini function-calling, portföy sağlık skoru ve XAI içgörüleri, hızlı sorular, sohbet geçmişi) ve **Hisse Modeli** (AI_Core model analizi; servis kapalıyken demo). Ayrıntı: [ai_integration.md](ai_integration.md).

## 9. Ayarlar

Sekmeler: Görünüm & Tema, API Anahtarları, Veri Sağlığı & Senkronizasyon, Dışa Aktarım & Yedekleme, Kurumsal Aksiyonlar, Fiyat Verisi, Piyasa Düzeltmeleri, Sistem, Haber Kaynakları (kaynak aç/kapa, özel RSS, bağlantı testi, yenileme aralığı; bkz. [service_news.md](service_news.md)). Ayrıntı: [settings_and_system.md](settings_and_system.md).

---

## Büyük Görünümlerin Bileşenleri

Beş büyük görünüm 2026-10-04'te bileşenlere bölündü (hiçbiri 900 satırı aşmaz; `test_qml_file_size_guard.py`). Bileşenler eskisi gibi doğrudan örneklenir (Loader kullanılmaz, sekmeler arası durum korunur); ana görünüm yalnızca yerleşimi, durumu ve diyalogları tutar, üst durumu özellik/sinyalle geçirir.

| Görünüm | Bileşenler |
|---|---|
| `SettingsView` | `SettingsAppearanceTab`, `SettingsApiKeysTab`, `SettingsDataHealthTab`, `SettingsExportTab` (+ önceden ayrı: `SettingsCorporateActionsTab`, `SettingsPriceDataTab`, `SettingsMarketAdjustmentsTab`, `SettingsSystemTab`, `SettingsNewsTab`) |
| `OptimizationView` (101) | `OptimizationParamsPanel` (`stacked`, `riskQuestionnaireRequested`), `OptimizationKpiStrip` (`stacked`, `hostWidth`), `OptimizationResultsPanel` |
| `Stock360View` (122) | `Stock360TopBar`, `Stock360ModeTabs`, `Stock360HeroCard`, `Stock360OverviewSection`, `Stock360FinancialsSection`, `Stock360ShareholdersSection` (`hostWidth` = Loader genişliği) |
| `StockDetailModal` (178) | `StockDetailHeader` (sinyaller), `StockDetailKpiCards` (`boxWidth`), `StockDetailTabsPanel` (`activeTab`), `StockDetailOrderForm` (emir durumu, `resetTradeMoment()`, `syncPrice()`) |
| `AiAdvisorView` (122) | `AiAdvisorHeader` (`historyRequested`), `AiChatTerminal` (`scrollToEnd()`), `AiHealthPanel` (`stacked`) |

**Görsel doğrulama (2026-10-04):** bölmeden önceki commit (`b3169fb`) ile sonrası, 17 ekran durumu için (Ayarlar 8 sekme, AI Asistan 2 mod, Optimizasyon, Hisse 360 3 mod, Hisse Detay kapalı/açık/2. sekme) ofscreen yazılımsal render ile `scripts/qml_visual_snapshot.py` aracılığıyla karşılaştırıldı: **farklı piksel sayısı 0**. Ofscreen ortamda yazı tipleri kutu olarak çizilir (yerleşim ve renk karşılaştırılır, metin biçimi değil); gerçek tıklama/kaydırma etkileşimi ve metin render'ı elle denenmedi.

Yeni bölme kuralları: bileşen yalnızca kendi kimliklerini ve `root` özelliklerini kullanır; ana görünümdeki kimliklere başvurmak yerine özellik/sinyal tanımlanır. Her bölmeden sonra `tests/ui_qml/test_qml_views_runtime_smoke.py` tüm sekme/modları uyarısız yüklemelidir.

## Denetleyici Referansı

| Denetleyici | Sorumluluk |
|---|---|
| `ShellController` | Etkin sayfa, piyasa seans durumu |
| `MyPortfolioController` | Portföyüm özeti (KPI, TRY/USD, sınıf dilimleri, sekmeler, tablo modeli); `UnifiedPortfolioService`'ten okur |
| `AssetsController` | Varlık ekleme (arka plan), işlem kaydı, fiyat yenileme (5 dk sessiz), öneri, kaldırma |
| `DashboardController` | BIST işlemleri (hızlı al/sat, sermaye, Excel), BIST haftalık/aylık getiri, kapanış güncelleme |
| `NewsController` | Genel Bakış haber paneli: şirket ve piyasa haberleri, periyodik yenileme, `openUrl` |
| `NewsSettingsController` | Ayarlar > Haber Kaynakları: aç/kapa, özel RSS, test, yenileme aralığı |
| `ChartController` | OHLCV, zaman dilimi, grafik tipi, göstergeler (TradingView); BIST dışı semboller için varlık defteri yolu |
| `StockDetailController` | Hisse detay modalı, hızlı emir, işlem etkisi, hisse Excel'i |
| `DividendController` | Hisse temettü kayıtları (ekle, listele, sil) |
| `CorporateActionController` | Bedelli/bedelsiz giriş ve ön izleme, KAP/MKK aday inceleme |
| `WatchlistController` | Listeler, hisse ekleme/çıkarma/not, sıralama, fiyat yenileme |
| `ModelPortfolioController` | Model portföy CRUD, işlem, sermaye, fiyat, Excel |
| `Stock360Controller` (+ `stock_360_calc/fallback/formatters/html`) | Hisse 360 verisi ve biçimlendirme |
| `ComparisonController` | Varlık seçimi, dönem, mod, para birimi, grafik panelleri, AI yorumu |
| `ScreenerController` | Strateji taraması |
| `GoldenCrossController` | Golden/Death Cross listesi, tarama, veri tamamlama |
| `PlanningController` | Bütçe, hedefler, DCA |
| `StrategyBacktestController` | Strateji testi |
| `OptimizationController` | Optimizasyon, sınır, rebalance |
| `RiskProfileController` | Risk anketi ve kayıtlı profil |
| `AiAdvisorController` | Danışman sohbeti, sağlık skoru, oturumlar |
| `ModelAnalysisController` | Hisse bazlı model analizi |
| `SettingsController` | Tema, API anahtarları, veritabanı istatistiği, bütünlük, dışa aktarım |
| `SystemController` | Otomatik canlı fiyat yenileme, sistem sıfırlama |
| `StartupJobsController` | Açılış bakım işleri |
| `MarketSyncController` | DuckDB artımlı senkron ve kapanış verisi nöbetçisi (18:30) |
| `PriceRefreshController` | Fiyat güncellemesinin tek koordinatörü: kaynak sinyallerini tek `pricesChanged`'e birleştirir (400 ms), ortak son güncelleme ve tek yenile ikonu (`priceRefreshController`) |
| `PriceDataController` | Fiyat verisi sağlığı |
| `MarketAdjustmentController` | Piyasa sermaye artırımı düzeltmeleri |
| `MarketTickerController` | Üst piyasa şeridi |
