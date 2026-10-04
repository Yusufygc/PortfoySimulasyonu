# Veri Mimarisi: SQLite (OLTP) ve DuckDB (OLAP)

> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md) | Şema: [database_schema_and_orm.md](database_schema_and_orm.md) | Kaynaklar: [service_market_data_providers.md](service_market_data_providers.md)

> MySQL desteği kaldırıldı (2026-10-02). Uygulama yalnızca yerel dosya tabanlı iki veritabanı kullanır.
> Yollar çalışma dizinine değil uygulama köküne göre çözülür: `src/infrastructure/db/paths.py`
> (`DB_SQLITE_PATH`, `DUCKDB_PATH` ortam değişkenleriyle değiştirilebilir).
> **Not:** `settings_loader` `.env` dosyasını `override=True` ile yükler, ancak kabuktan/test ortamından açıkça verilen
> `DB_SQLITE_PATH` ve `DUCKDB_PATH` değerleri korunur (kopya veritabanında betik çalıştırmak için). Testlerde
> `tests/conftest.py` oturum başına gerçek veritabanlarının kopyasını geçici klasöre alır ve bu iki değişkeni oraya yönlendirir;
> testler gerçek `data/` dosyalarına yazmaz.

## Ticker biçimi (tek tip)

Kanonik ticker **uzantısız büyük harftir** (`THYAO`): `stocks.ticker`, DuckDB, KAP, Golden Cross olayları ve arayüz.
`.IS` yalnızca yfinance gibi borsa son eki isteyen dış sınırlarda eklenir (`src/domain/ticker.py`: `clean_ticker`,
`to_yf_symbol`). `SQLAlchemyStockRepository.get_stock_by_ticker` her iki biçimi de bulur; yazma (`insert/update`)
uzantısızı kaydeder; açılışta eski `.IS` kayıtlar çakışma yoksa uzantısıza çevrilir. Yazıcılar (işlem girişi, model
portföy, izleme listesi, KAP sağlayıcı) uzantı eklemez. Uygulama BIST odaklıdır: uzantısız her kod yfinance'e `.IS`
ile gider; endeks (`^XU100`), kur (`USDTRY=X`) ve zaten uzantılı semboller olduğu gibi kalır.

## DuckDB şeması (`data/market_history.duckdb`)

| Tablo | Sütunlar |
|---|---|
| `bist_stocks` | `ticker` (PK), `name`, `currency_code`, `first_date`, `last_date`, `total_bars`, `updated_at` |
| `daily_prices` | `ticker`, `price_date` (PK birlikte), `open_price`, `high_price`, `low_price`, `close_price`, `volume` (ham, düzeltilmemiş) |
| `market_corporate_actions` | `ticker`, `effective_date` (PK), `factor`, `action_type`, `status`, `source`, `ex_date`, `ratio`, `rights_price`, `observed_ratio`, `confidence`, `note`, `updated_at` |

Dosyayı yalnızca `BistBulkDownloader` ve `MarketDataSyncService` (yazma), `DuckDBMarketHistoryRepository` ve `DuckDBCorporateActionStore` (okuma/aksiyon yazma) açar; `DatabaseMaintenanceService` istatistik için salt okunur açar.

## Sahiplik özeti

| Veri | Depo | Yazan | Okuyan |
|---|---|---|---|
| Portföy: `stocks`, `trades`, `cash_movements`, `trade_adjustments` | **SQLite** `data/portfolio.db` | `PortfolioService`, `TradeEntryService`, `CashMovementService` | Dashboard, Hisse Detay, Karşılaştırma, Optimizasyon, Excel |
| Kullanıcı verisine (işlem, izleme listesi, model portföy, kurumsal aksiyon) bağlı hisselerin günlük kapanışları: `daily_prices` (~35 hisse) | **SQLite** | `MarketDataSyncService` (köprü + uzlaştırma), `PriceDataHealthService`, `BackfillService`, sermaye artırımı fiyat düzeltmesi | Portföy değerleme, Karşılaştırma, `CurrentPriceResolver` |
| Canlı/gün içi fiyat önbelleği: `latest_prices` | **SQLite** | `LivePriceRefreshService` | `CurrentPriceResolver` ve İzleme Listesi (yalnızca seans penceresinde alınmış ve son kapanıştan yeni güne aitse kullanılır; `src/domain/live_price_rule.py`) |
| Takip listeleri, model portföyler (+işlem/nakit), bütçe/hedef/sabit kalemler | **SQLite** | ilgili servisler | ilgili ekranlar |
| Portföy kurumsal aksiyonları ve KAP/MKK adayları (`corporate_actions`, `corporate_action_candidates`) | **SQLite** | `CorporateActionService`, aday servisleri | Hisse Detay, Ayarlar |
| Risk profilleri, KAP ortaklık anlık görüntüleri | **SQLite** | `RiskProfileService`, `ShareholderAnalysisService` | Optimizasyon, Hisse 360 |
| Golden/Death Cross olayları `cross_events` (ticker anahtarlı, türetilmiş) | **SQLite** | `TechnicalAnalysisService` | Hisse Tarayıcı |
| **Tüm BIST günlük ham barları** (`daily_prices`, ticker bazlı, ~2,2 milyon bar, 2000-bugün) ve hisse kataloğu (`bist_stocks`, ~624) | **DuckDB** `data/market_history.duckdb` | `BistBulkDownloader` (ilk yükleme, script), `MarketDataSyncService.sync_daily_delta` (artımlı) | `DuckDBMarketHistoryRepository` (salt okunur) |
| **Sermaye artırımı/bölünme olayları ve fiyat düzeltme faktörleri** (`market_corporate_actions`, ticker anahtarlı) | **DuckDB** | `DuckDBCorporateActionStore` (`MarketCorporateActionService` üzerinden) | `DuckDBMarketHistoryRepository` (düzeltilmiş okuma) |
| Ayarlar: tema, otomatik iş işaretleri, sohbet geçmişi | Windows `QSettings` | `SettingsController`, `StartupJobsController` | aynı |
| API anahtarları | İşletim sistemi sır deposu (Windows Kimlik Bilgisi Yöneticisi, `keyring`); depo yoksa `.env` | `persist_api_keys` (`config/secret_store.py`) | `settings_loader` |
| Harici önbellekler (TÜFE, KAP) | `data/_cache/*.json` | sağlayıcılar | sağlayıcılar |

DuckDB'yi okuyanlar: Hisse Tarayıcı ve Golden Cross (tüm evren), Hisse 360 (genel bakış/teknik seviyeler/şirket adı/hızlı liste),
grafik, Hisse Detay son bar, DCA (birincil kaynak), Markowitz optimizasyonu, Ayarlar istatistikleri.

## Kurallar

1. **İşlemsel veri SQLite'tadır; piyasa verisinin sahibi DuckDB'dir.** SQLite `daily_prices` yalnızca kullanıcı verisine
   bağlı hisseler içindir (kullanıcı verisine bağlı olmayan 133 hissenin fiyatı ve kaydı 2026-10-03'te silindi).
2. **DuckDB'ye yalnızca `IMarketHistoryRepository` (okuma), `IMarketCorporateActionRepository` ve
   `MarketDataSyncService` / `BistBulkDownloader` (yazma) erişir.** Controller veya servislerde ham `duckdb.connect` kullanılmaz.
3. **DuckDB -> SQLite köprüsü repository üzerinden yapılır** (`price_repo.upsert_daily_prices_bulk`). Ham `sqlite3` yazımı yasaktır
   (BIGINT birincil anahtar otomatik artmadığı için eski köprü sessizce `NOT NULL constraint failed` ile başarısız oluyordu).
4. `MarketDataSyncService.reconcile_sqlite_from_duckdb` her senkronda DuckDB'de olup SQLite'ta olmayan **yeni** barları
   kullanıcı verisine bağlı hisseler için SQLite'a taşır; mevcut (düzeltilmiş) geçmiş barların üzerine asla yazmaz.
5. SQLite BIGINT birincil anahtarı otomatik artmaz. `orm_models.py` içindeki `before_insert` dinleyicisi `id` verilmeden eklenen kayıtlara `max(id)+1` atar (işlem, nakit hareketi, model portföy, bütçe vb.). Kimliği repository'de elle atayanlar etkilenmez. Dinleyici eşzamanlı yazıcılarda çakışmayı önlemek için `max(id)` okumadan önce yazma kilidini alır ([database_schema_and_orm.md](database_schema_and_orm.md)).
6. **DuckDB'deki ham barlar asla değiştirilmez.** Düzeltme `market_corporate_actions` faktörleriyle okuma anında uygulanır
   (bkz. [market_corporate_actions.md](market_corporate_actions.md)).
7. **Dış ağ çağrıları `src/infrastructure/retry.py::retry_call` ile yapılır.** Geçici hatalar (bağlantı/zaman aşımı, HTTP 408/429/5xx,
   yfinance hız sınırı) üstel geri çekilmeyle (1 sn, 2 sn...) en çok 3 kez denenir; kalıcı hatalar (4xx, ayrıştırma) denenmez.
   Kullanan istemciler: yfinance indirme ve optimizasyon verisi, EVDS, KAP (kamuya açık kaynak ve ortaklık), İş Yatırım, ölçüt
   (benchmark) kazıyıcısı ve `BistBulkDownloader`. Tek hisse anlık fiyat sorguları (`YFinancePriceLookupProvider`, değerleme)
   arayüzü bekletmemek için bilerek yeniden denenmez. Testlerde bekleme `tests/conftest.py` ile kapatılır.

## Bilinen sınırlar

- **Düzeltilmemiş adaylar:** Veriden tespit edilen sermaye artırımı adayları kullanıcı onayına kadar düzeltmeye girmez;
  onaylanana dek tarayıcı o hisse için ham seriyi görür.
- **Hacim:** Düzeltilmiş okumada OHLC faktörlenir, hacim ham kalır.
- **SQLite fiyatları (35 hisse):** Portföy değerlemesi SQLite'tan okur; DuckDB düzeltmesi ile otomatik eşitlenmez. Portföy aksiyonu
  uygulandığında her iki depo da güncellenir.
- **`candidate.ticker` eski kayıtları** `.IS` uzantılı olabilir (yalnızca `corporate_action_candidates`); aramalar iki biçimi de tolere eder.
