> Ana sayfa: [index.md](index.md) | Arayüz mimarisi: [ui_architecture_and_events.md](ui_architecture_and_events.md)

# Sayfa ve Denetleyici Rehberi

Uygulama 10 sayfadan oluşur. Sayfa dizini kenar çubuğu sırasıyladır (`ShellController.activePage`). Her bölüm sayfanın amacını, denetleyicisini, kullandığı servisleri ve önemli kurallarını verir. Genel mimari için bkz. [ui_architecture_and_events.md](ui_architecture_and_events.md).

| # | Sayfa | Görünüm | Ana denetleyici(ler) |
|---|---|---|---|
| 0 | Genel Bakış | `DashboardView` | `DashboardController`, `ChartController`, `StockDetailController`, `DividendController` |
| 1 | İzleme Listeleri | `WatchlistView` | `WatchlistController` |
| 2 | Model Portföyler | `ModelPortfolioView` | `ModelPortfolioController` |
| 3 | Hisse 360 | `Stock360View` | `Stock360Controller` |
| 4 | Karşılaştırma Lab | `ComparisonView` | `ComparisonController` |
| 5 | Hisse Tarayıcı | `ScreenerView` | `ScreenerController`, `GoldenCrossController` |
| 6 | Finansal Planlama | `PlanningView` | `PlanningController`, `StrategyBacktestController` |
| 7 | Optimizasyon | `OptimizationView` | `OptimizationController`, `RiskProfileController` |
| 8 | AI Asistan | `AiAdvisorView` | `AiAdvisorController`, `ModelAnalysisController` |
| 9 | Ayarlar | `SettingsView` | `SettingsController`, `SystemController`, `PriceDataController`, `CorporateActionController`, `MarketAdjustmentController` |

Üst başlık (`WindowHeader`): hisse arama (Genel Bakış grafiğini açar), piyasa şeridi (`MarketTickerController`: altın, gümüş, USD/TRY, EUR/TRY, BIST 100) ve piyasa senkron rozeti.

---

## 0. Genel Bakış (Dashboard)

Ana portföyün canlı özeti.

- **KPI şeridi** (`PortfolioSummaryStrip`/`MetricCard`): toplam değer, kâr/zarar, günlük değişim, nakit, haftalık ve aylık getiri, "son güncelleme" zamanı (`last_update_store.py`).
- **Açık pozisyonlar tablosu** (`PositionsTableModel`): lot, maliyet, güncel fiyat, günlük %, ağırlık; fiyat değişiminde yeşil/kırmızı yanıp sönme. Satıra tıklayınca **Hisse Detay modalı** açılır.
- **Varlık dağılımı** (`AssetAllocationCard`, Canvas donut).
- **TradingView grafiği** (`TradingViewChart`, `TradingViewToolbar`): zaman dilimi, mum/çizgi/alan/bar, göstergeler, tam ekran (`ChartFullscreenModal`); hisse detayından açıldığında ortalama maliyet çizgisi gösterilir.
- **İşlemler:** hızlı alım/satım (`QuickTradeModal`, tarih ve saat alanlı), sermaye yatırma/çekme (`CapitalModal`), fiyat durumu (`PriceStatusChip`: ortak son güncelleme ve küçük yenile ikonu; fiyatlar kendiliğinden güncellenir), tarihsel Excel raporu (`ExcelExportDialog`; mevcut dosyaya ekleme modu).
- **Hisse Detay modalı** (`StockDetailController`): lot, ortalama maliyet, piyasa değeri, K/Z; işlem geçmişi ve sermaye artırımları sekmeleri; işlem etkisi ön izlemesi; hızlı emir; **Sermaye Artırımı** (`CorporateActionDialog`), **Temettü** (`DividendDialog`), TradingView ve Hisse 360'a geçiş, hisse bazlı Excel. Sermaye artırımı ve temettü yalnızca ana portföy ve açık pozisyon için görünür.

Servisler: `PortfolioService`, `TradeEntryService`, `CashMovementService`, `ReturnCalcService`, `CurrentPriceResolver`, `ExcelExportService`. Fiyat ve işlem kuralları: [service_portfolio_and_market.md](service_portfolio_and_market.md).

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

Markowitz maksimum Sharpe optimizasyonu: kaynak (ana portföy veya model portföy), risk profili seçici, tek hisse üst sınırı kaydırıcısı, risksiz faiz oranı. Üç sekme: Verimli Sınır (Monte Carlo bulutu, sınır eğrisi, mevcut/optimum/minimum risk noktaları), Ağırlık Dağılımı, Yeniden Dengeleme (EKLE/AZALT/TUT, tutar ve tahmini lot). Risk anketi `RiskQuestionnaireDialog` ile doldurulur ve kaydedilir; kayıtlı profil tek hisse sınırını belirler. Ayrıntı: [service_planning_optimization.md](service_planning_optimization.md).

## 8. AI Asistan

İki mod: **Portföy Danışmanı** (Gemini function-calling, portföy sağlık skoru ve XAI içgörüleri, hızlı sorular, sohbet geçmişi) ve **Hisse Modeli** (AI_Core model analizi; servis kapalıyken demo). Ayrıntı: [ai_integration.md](ai_integration.md).

## 9. Ayarlar

Sekmeler: Görünüm & Tema, API Anahtarları, Veri Sağlığı & Senkronizasyon, Dışa Aktarım & Yedekleme, Kurumsal Aksiyonlar, Fiyat Verisi, Piyasa Düzeltmeleri, Sistem. Ayrıntı: [settings_and_system.md](settings_and_system.md).

---

## Büyük Görünümlerin Bileşenleri

Beş büyük görünüm 2026-10-04'te bileşenlere bölündü (hiçbiri 900 satırı aşmaz; `test_qml_file_size_guard.py`). Bileşenler eskisi gibi doğrudan örneklenir (Loader kullanılmaz, sekmeler arası durum korunur); ana görünüm yalnızca yerleşimi, durumu ve diyalogları tutar, üst durumu özellik/sinyalle geçirir.

| Görünüm | Bileşenler |
|---|---|
| `SettingsView` (231 satır) | `SettingsAppearanceTab`, `SettingsApiKeysTab`, `SettingsDataHealthTab`, `SettingsExportTab` (+ önceden ayrı: `SettingsCorporateActionsTab`, `SettingsPriceDataTab`, `SettingsMarketAdjustmentsTab`, `SettingsSystemTab`) |
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
| `DashboardController` | Portföy KPI, pozisyonlar, işlem, sermaye, kapanış güncelleme, haftalık/aylık getiri, Excel |
| `ChartController` | OHLCV, zaman dilimi, grafik tipi, göstergeler (TradingView) |
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
