# Veritabanı Şeması ve SQLAlchemy ORM

> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md) | Veri sahipliği: [data_architecture.md](data_architecture.md)

Bu sayfa SQLite (işlemsel) şemasını ve ORM katmanını anlatır. DuckDB şeması [data_architecture.md](data_architecture.md) ve [market_corporate_actions.md](market_corporate_actions.md) içindedir.

## 1. Repository Deseni

Domain katmanı SQL'den bağımsızdır: `src/domain/ports/repositories/` altındaki soyut arayüzler `src/infrastructure/db/sqlalchemy/repositories/` içindeki 15 SQLAlchemy repository'siyle (`sa_*.py`) uygulanır. Yazma yollarındaki `commit/rollback/refresh` tekrarları `_transaction.py` yardımcılarına (`commit_or_rollback`, `commit_refresh_or_rollback`) taşınmıştır; hata yakalama `SQLAlchemyError` ailesiyle sınırlıdır. `SQLAlchemyRiskProfileRepository` eski `risk_profiles` şeması için bilinçli bir uyumluluk yolu taşır.

## 2. Tablolar (`orm_models.py`, 23 tablo)

| Alan | Tablo | İçerik |
|---|---|---|
| Hisse ve işlem | `stocks` | `ticker` (benzersiz, kanonik uzantısız), `name`, `currency_code`. |
| | `trades` | BUY/SELL: `stock_id`, tarih, saat, `quantity`, `price`, `original_quantity`, `original_price` (sermaye artırımı öncesi özgün değerler), `total_amount` (üretilmiş sütun: `quantity * price`), `notes`. |
| | `trade_adjustments` | Sermaye artırımı düzeltme denetim izi: `trade_id`, `corporate_action_id`, `factor`, önceki/sonraki lot ve fiyat. |
| | `cash_movements` | `DEPOSIT`/`WITHDRAW`/`DIVIDEND`, `amount`, tarih/saat, `notes`, `stock_id` (yalnızca temettü; `ON DELETE SET NULL`). |
| Fiyat | `daily_prices` | `(stock_id, price_date)` benzersiz; `close_price`, `open/high/low`, `volume`, `source`. Yalnızca portföy hisseleri (kullanıcı verisine bağlı). |
| | `latest_prices` | Hisse başına tek satır canlı/gün içi fiyat: `price`, `as_of`, `source`, `provider`, `fetched_at`, `updated_at`. Tarihsel rapor kaynağı değildir. |
| Kurumsal aksiyon | `corporate_actions` | `BEDELLI`/`BEDELSIZ`, `ex_date`, `ratio`, `subscription_price`, `applied`, `prices_adjusted` ve düzeltme faktörü/sayısı (idempotency). |
| | `corporate_action_candidates` | KAP/MKK adayları: kaynak, duyuru kimliği, tür, durum, oran, güven, ham yük, ayrıştırma notu; `(source, source_disclosure_id, action_type, ticker)` benzersiz. |
| İzleme listesi | `watchlists`, `watchlist_items` | [service_watchlist.md](service_watchlist.md). |
| Model portföy | `model_portfolios` | `name`, `description`, `initial_cash`, `sort_order`. |
| | `model_portfolio_trades` | Portföye bağlı işlemler. |
| | `model_portfolio_cash_movements` | Sonradan eklenen/çekilen sermaye (tarih-saatli). |
| Planlama | `budgets` (`month` benzersiz), `budget_items`, `budget_pinned_items` (`item_type + name` benzersiz), `financial_goals` | Bütçe, kalemler, pinli şablonlar, hedefler. |
| Risk | `risk_profiles` | Skor, etiket, anket sürümü, yanıt/boyut puanı/dağılım JSON'ları, uygunluk notları. |
| Teknik | `cross_events` | Golden/Death Cross olayları: `(ticker, cross_date, cross_type)` benzersiz; türetilmiş veri. |
| KAP | `kap_companies` (`ticker` benzersiz, `mkk_member_oid`), `kap_shareholder_snapshots`, `kap_shareholder_rows` | Ortaklık yapısı önbelleği. |

Sohbet geçmişi, tema ve açılış işaretleri veritabanında değil `QSettings`'tedir ([settings_and_system.md](settings_and_system.md)).

## 3. İlklendirme ve Şema Evrimi

- `SQLAlchemyEngineProvider` bağlantıyı `check_same_thread=False` ile kurar, SQLite PRAGMA'larını uygular (WAL günlük modu, `synchronous=NORMAL`, `foreign_keys=ON`) ve `Base.metadata.create_all(checkfirst=True)` ile eksik tabloları oluşturur. Alembic kullanılmaz.
- **Sürümlü şema göçleri** (`schema_migrations.py`, `_init_db_schema` çağırır): uygulanan göçler `schema_migrations` tablosunda (`version`, `name`, `applied_at`) tutulur ve her biri yalnızca bir kez çalışır. Mevcut göçler: 1 eski `golden_cross_events` tablosunu siler (türetilmiş veri), 2 `.IS` uzantılı `stocks.ticker` kayıtlarını çakışma yoksa uzantısıza çevirir, 3 `cash_movements.stock_id` sütununu ekler.
  - Bekleyen göç varsa ve veritabanı doluysa göçten önce `data/backups/portfolio_pre_migration_<zaman>.db` yedeği alınır (SQLite `backup` API'si, son 5 tutulur). Yedek alınamazsa göç başlamaz.
  - Her göç kendi transaction'ında çalışır, sürüm kaydı aynı transaction'dadır. SQLite DDL'i her sürücüde geri alınamayabileceğinden göçler **idempotent** yazılır.
  - Hata yutulmaz: `SchemaMigrationError` yükselir; `app.py` bunu yakalayıp uygulamayı çevrimdışı modda açar ve log'a yazar.
  - Taze veritabanında `create_all` güncel şemayı kurar, mevcut göçler çalıştırılmadan uygulanmış işaretlenir.
  - **Yeni sütun/veri dönüşümü eklemek:** `MIGRATIONS` listesinin sonuna bir sonraki numarayla `Migration` ekleyin; numara ve sırayı değiştirmeyin. `create_all` var olan tabloya sütun eklemez.
- Bazı repository'ler kendi tablosunu `checkfirst=True` ile oluşturur (ör. nakit hareketi, bütçe pinleri).
- **BIGINT birincil anahtar:** SQLite `BIGINT` anahtarı otomatik artırmaz. `orm_models.py` içindeki `before_insert` dinleyicisi `id` boşsa `max(id)+1` atar (aynı flush içinde sayaç tutar); `id`'yi elle atayan repository'ler (fiyat, hisse, izleme listesi) etkilenmez. İki iş parçacığı aynı anda aynı tabloya yazarsa teorik çakışma olabilir; tek kullanıcılı masaüstünde kabul edilmiştir.
- Yabancı anahtarlar: `daily_prices`, `corporate_actions`, `trades` hisse silmeyi engeller (`RESTRICT`); izleme listesi öğeleri ve model işlemleri CASCADE. Hisse silmek için `PortfolioMaintenanceService.purge_stock_by_ticker` bağlı kayıtları doğru sırayla siler ([database_maintenance_and_scripts.md](database_maintenance_and_scripts.md)).

## 4. Sermaye Artırımı ve İşlem Düzeltmesi

Sermaye artırımı uygulandığında `trades.quantity` ve `price` bölünmüş değerleri tutar; özgün değerler `original_quantity` ve `original_price` sütunlarında salt okunur korunur ve her değişiklik `trade_adjustments`'a yazılır ([service_corporate_actions.md](service_corporate_actions.md)).

## 5. Önbellek Dosyaları

Mali tablo, TÜFE, değerleme ve KAP şirket listesi önbellekleri veritabanında değil `data/_cache/` altında JSON dosyalarıdır ([service_market_data_providers.md](service_market_data_providers.md)).

## 6. Testler

`tests/infrastructure/db/` (`test_database_engine.py`, `test_schema_migrations.py`, `test_orm_schema.py`, `test_sqlite_upserts.py`, `test_transaction_helper.py`, repository testleri, `test_cash_movement_dividend_repository.py`: id atama ve sütun göçü).
