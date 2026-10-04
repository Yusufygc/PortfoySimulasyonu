> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md)

# Proje Yapısı ve Modül Haritası

Bu sayfa kaynak ağacını ve her dizinin sorumluluğunu özetler. Katman ilkeleri için bkz. [architecture.md](architecture.md).

## 1. Kök Dizin

| Yol | İçerik |
|---|---|
| `app.py` | Uygulama giriş noktası: Qt ölçek normalizasyonu, loglama, `AppContainer`, `run_qml_app`. |
| `config/` | `settings_loader.py` (ortam ayarları), `safety_patterns.txt` (AI girdi güvenlik kalıpları). |
| `src/` | Uygulama kodu (aşağıya bakın). |
| `tests/` | pytest paketi; `src/` yapısını yansıtır ([testing_strategy.md](testing_strategy.md)). |
| `scripts/` | Bakım, göç ve ölçüm betikleri ([database_maintenance_and_scripts.md](database_maintenance_and_scripts.md)). |
| `data/` | `portfolio.db`, `market_history.duckdb`, `_cache/` (KAP ve mali tablo önbelleği), `backups/`. |
| `docs/wiki/` | Bu bilgi tabanı. |
| `icons/` | Uygulama ve derleme simgeleri. |
| `build_nuitka.bat`, `requirements*.txt` | Windows `.exe` derlemesi ve pinli bağımlılıklar ([project_build_and_deployment.md](project_build_and_deployment.md)). |
| `AGENTS.md`, `CLAUDE.md`, `RULES.md`, `GOVERNANCE.md`, `ARCHITECTURE_GATES.md` | Ajan/geliştirici kuralları. |
| `README.md`, `QML_TRANSFORMATION_HANDOFF.md`, `TRANSFORMATION_PLAN.md` | Genel tanıtım, dönüşüm devralma kılavuzu ve tarihsel plan. |

## 2. `src/domain/`

| Alt dizin | İçerik |
|---|---|
| `models/` | Saf modeller: `stock`, `trade`, `position`, `portfolio`, `cash_movement`, `corporate_action`, `corporate_action_candidate`, `daily_price`, `latest_price`, `market_bar`, `market_corporate_action`, `market_indicator`, `model_portfolio`, `watchlist`, `budget`, `financial_goal`, `risk_profile`, `optimization_result`, `golden_cross_event`, `shareholder`, `trade_adjustment`, `ai_analysis`, `ai_tool`. |
| `ports/repositories/` | Veri erişim arayüzleri (`i_portfolio_repo`, `i_price_repo`, `i_market_history_repo`, `i_cash_movement_repo`...). |
| `ports/services/` | Dış sağlayıcı arayüzleri (`i_market_data_client`, `i_financial_statement_provider`, `i_inflation_data_provider`, `i_shareholder_provider`, `i_ai_chat_provider`...). |
| `constants/`, `exceptions.py`, `ticker.py` | BIST ticker listesi, alan istisnaları, kanonik ticker yardımcıları (`clean_ticker`, `to_yf_symbol`). |

## 3. `src/application/`

| Alt dizin | Servisler |
|---|---|
| `container.py`, `container_parts/` | DI container ve fabrikalar (`repositories`, `market_clients`, `services`, `ai`). |
| `events/` | `GlobalEventBus` (`prices_updated`). |
| `services/portfolio/` | `PortfolioService`, `TradeEntryService`, `CashMovementService`, `PriceUpdateService`, `PortfolioUpdateCoordinator`, `PortfolioMaintenanceService`, `PortfolioResetService`, `timeline_validator`, `safe_portfolio_builder`. |
| `services/market/` | `StockLookupService`, `CurrentPriceResolver`, `LivePriceRefreshService`, `PriceDataHealthService`, `PriceLookupService`, `MarketIndicatorsService`, `BistMarketSessionService`, işlem günü takvimi ve seans koruması. |
| `services/market_data/` | `MarketDataSyncService` (artımlı DuckDB senkronu), `BistBulkDownloader`, `MarketUniverseMigrationService`. |
| `services/corporate_actions/` | `CorporateActionService`, `CorporateActionPriceAdjustmentService`, KAP/MKK aday keşfi ve inceleme, `MarketCorporateActionService` (DuckDB). |
| `services/analysis/` | `AnalysisService`, `PortfolioAnalyticsService`, `ComparisonService`, `AnalysisBenchmarkService`, `ReturnCalcService`, `risk_metrics`, `Stock360Service`, `FinancialAnalysisService`, `ShareholderAnalysisService`; `financials/` (metrik, değerleme, enflasyon) ve `technical/` (göstergeler, tarayıcı, Golden Cross, destek/direnç). |
| `services/planning/` | `PlanningService`, `OptimizationService`, `frontier_simulation`, `RiskProfileService`, `RiskOptimizationBridgeService`, model portföy servisleri. |
| `services/simulation/` | `HistorySimulationService`, `BackfillService`, DCA ve strateji backtest, `price_series_loader`. |
| `services/watchlist/` | `WatchlistService`. |
| `services/reporting/` | Excel dışa aktarım (`ExcelExportService`, `ModelPortfolioExcelExportService`...) ve `html/` (Plotly/finansal/ortaklık HTML üreticileri). |
| `services/ai/` | `AiAdvisorService`, `advisor_tools`, `AiChatService`, `AiAnalysisService`, `ChatSessionService`, `safety_guard`. |
| `services/database/` | `DatabaseMaintenanceService`. |

## 4. `src/infrastructure/`

| Alt dizin | İçerik |
|---|---|
| `db/` | `paths.py` (veri dosyası yolları), `db_config.py`, `sqlalchemy/` (`database_engine`, `schema_migrations`, `orm_models`, 15 repository). |
| `market_data/` | DuckDB deposu (`duckdb_market_history_repo`, `duckdb_corporate_action_store`, `duckdb_optimization_market_data_provider`), yfinance istemcileri, `evds_client`, `evds_tufe_provider`, `isyatirim_provider`, `scraped_benchmark_provider`. |
| `corporate_actions/` | `kap_mkk_provider` (kurumsal aksiyon duyuruları), `kap_shareholder_provider` (ortaklık yapısı). |
| `calendar/` | BIST resmi tatil takvimi (2020-2030) ve işlem günü sağlayıcıları. |
| `ai/` | `gemini_chat_provider`, `gemini_advisor_chat_provider`, `ai_core_fastapi_client`, `mock_ai_analysis_provider`, `qsettings_chat_history_repo`. |
| `logging/` | `logger_setup` (dönen dosya, gizli değer maskeleme, global istisna kancası). |
| `retry.py` | Ağ çağrıları için üstel geri çekilmeli yeniden deneme. |

## 5. `src/ui_qml/`

| Yol | İçerik |
|---|---|
| `app.py` | `run_qml_app`: denetleyicileri kurar, context property olarak kaydeder, `Main.qml`'i yükler. |
| `controllers/` | 25 denetleyici (`*_controller.py`) ve yardımcı modüller (`number_input`, `lw_chart_html`, `stock_360_calc/fallback/formatters/html`). Rehber: [qml_pages_guide.md](qml_pages_guide.md). |
| `models/` | `PositionsTableModel`, `WatchlistTableModel` (`QAbstractTableModel`). |
| `last_update_store.py` | Son fiyat güncelleme zamanı ve dönemsel getirilerin `QSettings`'te saklanması. |
| `qml/Main.qml` | Ana pencere, kenar çubuğu, sayfa yükleyiciler (lazy `Loader`). |
| `qml/views/` | 10 sayfa görünümü. |
| `qml/components/` | Yeniden kullanılabilir bileşenler ve diyaloglar (`Modern*`, `*Dialog`, `*Tab`, `*Card`...). |
| `qml/theme/` | `Theme`, `Strings`, `Icons` singleton'ları ve `qmldir`. |
| `assets/` | `icons/` (Lucide SVG), `js/` (TradingView Lightweight Charts, Chart.js), `templates/`. |

## 6. `src/qt_compat/`

Qt binding sınırı: `qtcore`, `qtwidgets` ve `scaling` (Windows ekran ölçeğini ters `QT_SCALE_FACTOR` ile normalize eder). Üretim kodu `GlobalEventBus` gibi yerlerde Qt sınıflarını buradan alır.

## 7. Test Dizini

| Dizin | Kapsam |
|---|---|
| `tests/domain/` | Saf model testleri. |
| `tests/application/` | Servis testleri (mock repository, sahte sağlayıcı). |
| `tests/infrastructure/` | Gerçek geçici SQLite/DuckDB ile repository ve sağlayıcı testleri. |
| `tests/ui_qml/` | Denetleyici, QML derleme/uyarı ve koruma testleri. |
| `tests/qt_compat/` | Ekran ölçeği testi. |
| `tests/test_repo_guards.py`, `tests/test_code_quality_measurement.py` | Depo geneli korumalar ve ölçüm betiği testi. |
