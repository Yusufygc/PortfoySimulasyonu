# Test Stratejisi (Testing Strategy)

> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md)

Bu belge, uygulamanın test kültürünü ve `tests/` dizininin mimarisini açıklar.

## 1. Test Piramidi ve Kapsam (Coverage)

Portföy Simülasyonu projesi, regülasyonlara ve katı finansal hesaplamalara (Portföy P&L, Sharpe, Optimizasyon) dayandığı için yüksek bir test disiplinine sahiptir.

- **Birim Testleri (Unit Tests):** `tests/domain` altında saf (veritabanı veya API bağlantısı olmayan) matematiksel hesaplamaları test eder.
- **Servis Testleri (Application Tests):** `tests/application` altındadır. Dış bağımlılıklar (SQLAlchemy Repoları, YFinance istemcileri) `pytest-mock` kullanılarak mock'lanır ve iş kuralları (Use-Case) test edilir.
- **Arayüz Testleri (UI Tests):** `pytest-qt` eklentisi kullanılarak PyQt widget'larının oluşturulması, sinyallerin (signal) tetiklenmesi ve ekrandaki renk/boyut değişiklikleri test edilir.

## 2. Fixture ve Mock Yaklaşımı (`conftest.py`)

Testlerde sürekli olarak "Sahte Portföy", "Sahte Hisseler" ve "Sahte Fiyat Verisi" üretmek kod tekrarına yol açar. Bu yüzden `tests/conftest.py` dosyası paylaşılan (shared) test verilerini (Fixture) barındırır.

Örnek Mock Yaklaşımı:
Bir optimizasyon servisi test edilirken YFinance API'si asla gerçek bir HTTP isteği atmaz. `MarketDataProvider` arayüzünü uygulayan bir Mock Sınıf veya `mocker.patch` kullanılarak sabit test verileri döndürülür. Bu, testlerin (internetsiz ortamlarda bile) hızlı ve tekrarlanabilir (reproducible) olmasını sağlar.

## 3. Komutlar

Testleri çalıştırmak için proje kurallarındaki standart `pytest` komutları kullanılır:

```bash
# Tüm testleri çalıştırır
python -m pytest tests/

# Sadece spesifik bir klasörü veya dosyayı çalıştırır
python -m pytest tests/application/
```

Her refactoring işleminden sonra (ve yeni özellik eklenmeden önce) testlerin çalıştırılıp yeşil (Passed) olduğu kanıtlanmalıdır.

## 4. Faz 4 UI Regresyon Kapıları

Faz 4 UI refactor'larında aşağıdaki test yüzeyleri zorunlu kabul edilir:

- `tests/ui/test_worker.py`: ortak `Worker` success/error/finished sinyal sırası.
- `tests/application/test_event_bus.py`: `GlobalEventBus` import ve `prices_updated` signal sözleşmesi.
- `tests/ui/test_price_event_publisher.py`: boş fiyat payload'unun emit edilmemesi ve Decimal fiyatların korunması.
- `tests/ui/test_style_manifest.py`: QSS manifest sağlığı, token çözümleme ve inline stylesheet guard.
- İlgili sayfa testleri: dashboard, comparison, analysis, stock detail, settings, model portfolio.

Refactor sonunda hızlı doğrulama `tests/ui -q`, tam doğrulama ise `tests -q` ile yapılır. `.pytest_cache` permission warning bilinen ortam uyarısıdır; test sonucunu failed yapmadığı sürece blocker değildir.

## 5. Faz 5 Test / QA Guard Standardı

Faz 5 ile test altyapısı davranış değiştirmeden sertleştirildi:

- `pytest.ini` marker katalogunu tanımlar: `ui`, `integration`, `network`, `manual`.
- Default test komutu `manual` ve `network` marker'lı testleri çalıştırmaz; canlı veri kontrolleri açık tercih ile koşulur.
- `tests/conftest.py` ortak fixture yüzeyini taşır: `qapp`, `drain_qt_events`, `fake_event_bus`, `fixed_today` ve temel domain builder fixture'ları.
- UI async testlerinde dağınık `QThreadPool.globalInstance().waitForDone()` ve `processEvents()` çağrıları yerine `drain_qt_events` kullanılır.
- Manuel benchmark kontrolü `tests/infrastructure/market_data/test_benchmark_fetch_manual.py` altında tutulur ve `manual + network` marker'larıyla default suite dışında kalır.

Kalite guard'ları `tests/ui/test_refactor_guards.py` altındadır:

- `src/ui` içinde özel `QThread` sınıfı veya importu yoktur.
- UI fiyat event yayını doğrudan `prices_updated.emit` ile değil `publish_prices_updated` helper'ı ile yapılır.
- UI büyük sınıf eşiği için yalnız belgelenmiş Faz 5 istisnaları kabul edilir: `RiskProfilePage`, `WatchlistPage`, `NewStockTradeDialog`.
- Otomatik testler canlı HTTP helper'larını doğrudan çağıramaz; canlı kontroller manuel/network marker'ı ister.

Faz 5 baseline: `pytest --collect-only -q` -> **305 collected**; `tests/ui -q` -> **91 passed**; `tests/domain tests/application tests/infrastructure -q` -> **214 passed**. `.pytest_cache` permission warning ortam kaynaklı bilinen uyarıdır.

## 6. Faz 6 Production Guard ve CI

Faz 6 ile test stratejisine production hazırlık guard'ları eklendi:

- `tests/infrastructure/test_production_guards.py` repo içinde gerçek secret literal'ları ve build preflight statik koşullarını denetler.
- `tests/infrastructure/test_logger_setup.py` logger handler tekrarını, env level override davranışını, secret redaction'ı ve global exception hook'u kapsar.
- `tests/infrastructure/db/test_database_engine.py` SQLAlchemy engine'in DB pool ayarlarını `MySQLConfig` üzerinden aldığını doğrular.
- `.github/workflows/tests.yml` Windows + Python 3.11 üzerinde `pip check`, `pytest --collect-only -q` ve `pytest tests -q` çalıştırır.

CI default suite, `pytest.ini` içindeki `not manual and not network` filtresi nedeniyle canlı network/manual testleri çalıştırmaz. Nuitka build CI'da koşmaz; release öncesi `python scripts/build_preflight.py` ile manuel doğrulanır.
