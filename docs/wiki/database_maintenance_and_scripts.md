# Veritabanı Bakımı ve Betikler

> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md) | Şema: [database_schema_and_orm.md](database_schema_and_orm.md) | Veri sahipliği: [data_architecture.md](data_architecture.md)

## 1. Uygulama İçi Bakım (`DatabaseMaintenanceService`)

`src/application/services/database/database_maintenance_service.py`, Ayarlar > Veri Sağlığı ve Dışa Aktarım sekmeleri için SQLite ve DuckDB dosyalarını **salt okunur** açar; arayüz katmanı ham bağlantı kullanmaz.

| İşlev | Ayrıntı |
|---|---|
| `collect_stats()` | Dosya boyutları; SQLite tablo satır sayıları (hisse, işlem, nakit hareketi, izleme listesi, model portföy, finansal hedef); DuckDB hisse sayısı, toplam bar ve son bar tarihi. Dosya yoksa "Dosya Yok" gösterilir. |
| `check_integrity()` | SQLite `PRAGMA integrity_check` ve DuckDB `daily_prices` okuma testi; sorun listesi döner, boş liste sağlam demektir. |
| `export_backup_data()` | JSON yedeği için `stocks`, `trades`, `cash_movements`, `watchlists` tablolarının içeriği. Dosyayı `SettingsController` masaüstüne (yoksa `reports/`) `PortfoySim_Yedek_<tarih>.json` olarak yazar. |
| `from_config()` | Yolları `src/infrastructure/db/paths.py` ile çözer (`DB_SQLITE_PATH`, `DUCKDB_PATH`). |

Not: JSON yedeği tam bir geri yükleme aracı değildir (model portföy, bütçe, kurumsal aksiyon içermez); tam yedek için `data/portfolio.db` dosyasını kopyalayın. Eski `DatabaseIntegrityService` (işlem zinciri denetimi) hiçbir yerde kullanılmadığı için 2026-10-03'te kaldırıldı; işlem zinciri tutarlılığı çalışma anında `build_portfolio_safely` ve `PortfolioTimelineValidator` ile sağlanır ([service_portfolio_and_market.md](service_portfolio_and_market.md)).

Portföy düzeyi bakım servisleri:

| Servis | Görev |
|---|---|
| `PortfolioMaintenanceService.purge_stock_by_ticker` | Hisseyi ve tüm bağlı kayıtlarını (işlem, izleme listesi, model portföy, fiyat) FK sırasına uygun siler. Geri alınamaz. |
| `PortfolioResetService.reset_all` | Ayarlar > Sistem > sıfırlama; model portföyleri, izleme listelerini, işlemleri, nakit hareketlerini, fiyatları ve hisseleri siler ([settings_and_system.md](settings_and_system.md)). |
| `MarketUniverseMigrationService` | SQLite piyasa geçmişini DuckDB'ye taşıyan bir kerelik göç (tamamlandı). |

## 2. Betikler (`scripts/`)

Tümü proje kökünden `.\venv\Scripts\python.exe scripts\<ad>.py` ile çalıştırılır. **Veriyi değiştiren betikleri önce kopya veritabanına yöneltin** (`DB_SQLITE_PATH`, `DUCKDB_PATH`; bkz. [development_guide.md](development_guide.md)).

| Betik | İşlev | Not |
|---|---|---|
| `sync_bist_to_duckdb.py` | Tüm BIST geçmişini yfinance'ten DuckDB'ye indirir (`--workers`, `--limit`, `--tickers THYAO,BIMAS`, `--db-path`). Hisse listesi TradingView Scanner API'sinden gelir. | İlk yükleme ve onarım içindir; günlük güncelleme uygulama içinde `MarketDataSyncService` ile yapılır. |
| `migrate_market_universe_to_duckdb.py` | SQLite piyasa geçmişini DuckDB tek evrenine taşır; **varsayılan kuru çalıştırma**, `--execute` önce yedek alır (`data/backups/`). | 2026-10-03'te çalıştırıldı ([data_architecture.md](data_architecture.md)). |
| `purge_stock.py` | `--ticker THYAO` ile hisseyi ve bağlı kayıtları siler (`PortfolioMaintenanceService`). | Geri alınamaz; önce yedek alın. |
| `measure_code_quality.py` | Kod boyutu/karmaşıklık ölçümü; `--output-dir`, `--fail-on-threshold` ([code_quality_guardrails.md](code_quality_guardrails.md)). | |
| `build_preflight.py` | Derleme öncesi kontroller ([project_build_and_deployment.md](project_build_and_deployment.md)). | |
| `import_bist_ohlcv_to_db.py` | BIST OHLCV CSV'lerini içe aktarır. | MySQL dönemine ait, sabit yerel kaynak dizini vardır; eskimiş kabul edin. |
| `backfill_missing_friday_prices.py`, `fix_technical_analysis.py` | Tek seferlik düzeltmeler (sabit tarih/hisse). | Yeniden kullanmadan önce okuyun. |
| `bencmarkVeri.py`, `tcmbApi.py`, `tcmbFaizApi.py`, `inspect_db.py`, `show_violations.py`, `finansal_lab/` | Keşif/prototip betikleri. | Hiçbir yerden çağrılmaz ([roadmap.md](roadmap.md)). |

## 3. Güvenli Çalışma Pratikleri

1. Veriyi değiştirmeden önce `data/portfolio.db` ve `data/market_history.duckdb` dosyalarını kopyalayın; migrasyon betikleri `data/backups/` altına SQLite yedeği alır.
2. Denemeler için `DB_SQLITE_PATH` ve `DUCKDB_PATH` ortam değişkenlerini kopya dosyalara yönlendirin; `.env` bu iki değişkeni ezmez.
3. Test ortamı: `PORTFOYSIM_ENV=test` `.env.test` dosyasını okur (`run_test.bat`). Pytest ayrıca oturum başına geçici kopya kullanır; testler gerçek dosyalara yazmaz ([testing_strategy.md](testing_strategy.md)).
4. Büyük sürüm geçişlerinden sonra Ayarlar'dan bütünlük kontrolünü çalıştırın.
5. DuckDB'ye yalnızca ilgili servis ve betikler yazar; elle `duckdb.connect` ile ham bar değiştirmeyin ([data_architecture.md](data_architecture.md) kural 6).

## 4. Kullanılmayan Hisse Temizliği

Model portföy veya izleme listesi silinince ortak sözlük olan `stocks` kaydı ve varsa `daily_prices` geçmişi otomatik silinmez (bilinçli, güvenli davranış). Hiçbir yerde kullanılmayan hisseleri temizlemek için önce `trades`, `watchlist_items`, `model_portfolio_trades` ve `corporate_actions` içinde kullanılmadığını doğrulayın, yedek alın, sonra `purge_stock.py` kullanın. Fiyat sağlığı raporu yalnızca net açık pozisyonları taradığı için kullanılmayan hisseler raporda görünmez.
