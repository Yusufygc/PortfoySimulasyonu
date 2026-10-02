# Veri Mimarisi: SQLite (OLTP) ve DuckDB (OLAP)

> MySQL desteği kaldırıldı (2026-10-02). Uygulama yalnızca yerel dosya tabanlı iki veritabanı kullanır.
> Yollar çalışma dizinine değil uygulama köküne göre çözülür: `src/infrastructure/db/paths.py`
> (`DB_SQLITE_PATH`, `DUCKDB_PATH` ortam değişkenleriyle değiştirilebilir).

## Sahiplik özeti

| Veri | Depo | Yazan | Okuyan |
|---|---|---|---|
| Portföy: `stocks`, `trades`, `cash_movements`, `trade_adjustments` | **SQLite** `data/portfolio.db` | `PortfolioService`, `TradeEntryService`, `CashMovementService` | Dashboard, Hisse Detay, Karşılaştırma, Optimizasyon, Excel |
| Portföydeki/izlenen hisselerin günlük kapanışları: `daily_prices` (~166 hisse) | **SQLite** | `MarketDataSyncService` (köprü + uzlaştırma), `PriceDataHealthService`, `BackfillService`, sermaye artırımı fiyat düzeltmesi | Portföy değerleme, grafik, Teknik tarama, Hisse 360, DCA |
| Canlı/gün içi fiyat önbelleği: `latest_prices` | **SQLite** | `LivePriceRefreshService` | `CurrentPriceResolver` (yalnızca son kapanıştan yeni güne aitse kullanılır) |
| Takip listeleri, model portföyler (+işlem/nakit), bütçe/hedef/sabit kalemler | **SQLite** | ilgili servisler | ilgili ekranlar |
| Kurumsal aksiyonlar ve KAP/MKK adayları | **SQLite** | `CorporateActionService`, aday servisleri | Hisse Detay, Ayarlar |
| Risk profilleri, Golden Cross olayları, KAP ortaklık anlık görüntüleri | **SQLite** | `RiskProfileService`, `TechnicalAnalysisService`, `ShareholderAnalysisService` | Optimizasyon, Tarayıcı, Hisse 360 |
| **Tüm BIST günlük barları** (`daily_prices`, ticker bazlı, ~2,2 milyon bar, 2000-bugün) ve hisse kataloğu (`bist_stocks`, ~624) | **DuckDB** `data/market_history.duckdb` | `BistBulkDownloader` (ilk yükleme, script), `MarketDataSyncService.sync_daily_delta` (artımlı) | `DuckDBMarketHistoryRepository` (salt okunur): grafik (portföy dışı hisseler), Hisse Detay son bar, DCA fallback; `DuckDBOptimizationMarketDataProvider` (Markowitz); Ayarlar istatistikleri |
| Ayarlar: tema, otomatik iş işaretleri, sohbet geçmişi | Windows `QSettings` | `SettingsController`, `StartupJobsController` | aynı |
| API anahtarları | `.env` | `persist_api_keys` | `settings_loader` |
| Harici önbellekler (TÜFE, KAP) | `data/_cache/*.json` | sağlayıcılar | sağlayıcılar |

## Kurallar

1. **İşlemsel veri ve portföy fiyatları SQLite'tadır.** DuckDB'ye yazma yalnızca piyasa verisi indiricileri içindir.
2. **DuckDB'ye yalnızca `IMarketHistoryRepository` (okuma) ve `MarketDataSyncService` / `BistBulkDownloader` (yazma) erişir.** Controller veya servislerde ham `duckdb.connect` kullanılmaz.
3. **DuckDB -> SQLite köprüsü repository üzerinden yapılır** (`price_repo.upsert_daily_prices_bulk`). Ham `sqlite3` yazımı yasaktır (BIGINT birincil anahtar otomatik artmadığı için eski köprü sessizce `NOT NULL constraint failed: daily_prices.id` ile başarısız oluyordu).
4. `MarketDataSyncService.reconcile_sqlite_from_duckdb` her senkronda DuckDB'de olup SQLite'ta olmayan **yeni** barları portföy hisseleri için SQLite'a taşır; mevcut (sermaye artırımıyla düzeltilmiş) geçmiş barların üzerine asla yazmaz.
5. SQLite BIGINT birincil anahtarlarında yeni satıra `id` elle verilir (`max(id)+1`).

## Bilinen sınırlar (karar bekleyen)

- **Evren farkı:** SQLite'ta 168 hisse, DuckDB'de ~624 hisse var. Tarayıcı (strateji + Golden Cross) ve teknik analiz `stock_repo`'daki hisseleri tarar, yani yalnızca SQLite'taki 168'i. Tüm BIST'i taramak için hisselerin `stocks` tablosuna eklenmesi veya tarayıcının DuckDB'den beslenmesi gerekir.
- **Düzeltilmiş/düzeltilmemiş fiyat:** Sermaye artırımı fiyat düzeltmesi yalnızca SQLite barlarına uygulanır; DuckDB ham barlar tutar. Optimizasyon DuckDB fiyatlarını kullandığı için bedelsiz sonrası getiri hesabı etkilenebilir.
- **Ticker biçimi:** SQLite `stocks.ticker` karışık (46 kayıt `.IS` uzantılı, 122 uzantısız); DuckDB uzantısızdır. Kod her ikisini de tolere eder, veri normalleştirilmemiştir.
