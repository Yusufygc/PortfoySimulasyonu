# 02 — Varlık Defteri

> Ana sayfa: [index.md](index.md) | Günlük: [log.md](log.md) | Önceki: [01_mimari_kararlar.md](01_mimari_kararlar.md) | Sonraki: [03_fiyat_ve_kur_hatti.md](03_fiyat_ve_kur_hatti.md)

Durum: **Uygulandı** (Aşama 2, 2026-11-01)

BIST dışı varlıkları (emtia, kripto, ABD hisseleri) tutan, mevcut `trades`/`stocks` hattından bağımsız defter. Model portföy örüntüsünü izler.

## 0. Uygulanan Dosyalar

| Katman | Dosya |
|---|---|
| Domain | `src/domain/models/asset.py`, `asset_trade.py`, `asset_position.py` (`AssetPosition` + `AssetLedger`), `asset_price.py` (`AssetPrice`, `AssetLatestPrice`, `FxRate`) |
| Port | `src/domain/ports/repositories/i_asset_repo.py`, `i_asset_trade_repo.py`, `i_asset_price_repo.py`, `i_fx_rate_repo.py`; `src/domain/ports/services/i_asset_symbol_verifier.py` |
| ORM | `orm_models.py`: `ORMAsset`, `ORMAssetTrade`, `ORMAssetPrice`, `ORMAssetLatestPrice`, `ORMFxRate` |
| Repository | `src/infrastructure/db/sqlalchemy/repositories/sa_asset_repository.py`, `sa_asset_trade_repository.py`, `sa_asset_price_repository.py`, `sa_fx_rate_repository.py` |
| Servis | `src/application/services/assets/asset_ledger_service.py`, `asset_catalog.py` |
| Container | `container_parts/repositories.py` (`asset_repo`, `asset_trade_repo`, `asset_price_repo`, `fx_rate_repo`), `container_parts/services.py` (`asset_ledger_service`) |
| Test | `tests/domain/test_asset_models.py`, `tests/infrastructure/db/test_asset_repositories.py`, `tests/application/services/assets/test_asset_ledger_service.py`, `tests/application/test_asset_container_wiring.py`, `test_orm_schema.py` eki |

## 0.1 Uygulama Sırasında Alınan Kararlar

- **Sembol doğrulama portu:** `AssetLedgerService` çevrimiçi doğrulamayı `IAssetSymbolVerifier` (`verify(yf_symbol) -> bool`) portuyla ister; doğrulayıcı verilmezse atlanır. yfinance gerçekleştirimi Aşama 3'te yazılıp container'a bağlanacak.
- **Pasife alma:** İşlem geçmişi olan varlık silinmez, pasife alınır; aynı sembol yeniden eklenirse mevcut kayıt yeniden etkinleştirilir. Geçmişsiz varlık silinir.
- **Satış doğrulaması:** Yeni işlem eklenirken ve işlem silinirken varlığın tüm işlemleri tarih-saat sırasıyla `AssetLedger` ile yeniden uygulanır; geriye dönük satış veya satışı besleyen alımı silme reddedilir.
- **Maliyet iki para biriminde:** `AssetPosition` hem varlık para biriminde (`total_cost`) hem her alımın kendi kuruyla TRY (`total_cost_try`) maliyet ve gerçekleşen K/Z tutar; TRY K/Z işlem anı kurunu yansıtır.
- **float yasağı:** `AssetTrade` ve fiyat kayıtları `float` kabul etmez; servis girdileri `Decimal` veya `str` olmalı, ondalık virgül kabul edilir.
- **Katalog yalnızca ons:** Kıymetli madenler katalogda yalnızca ons (USD/troy ons, vadeli kontrat) olarak vardır. Gram birimi (`AssetUnit.GRAM`) modelde var ama gram bazlı katalog girdisi yok; sağlayıcı fiyatı ons olduğundan gram değerlemesi için fiyat dönüşümü Aşama 3/4'te (ortak ons→gram sabiti) ele alınacak. Böylece yanlış değerleme riski kapatıldı.
- **Fiyat ve kur repo'ları** Aşama 2'de yazıldı (upsert, aralık, son fiyat); yenileme servisi ve kur servisi Aşama 3'te.
- **Göç gerekmedi:** Yalnızca yeni tablolar; `create_all` kurar, `schema_migrations.py` değişmedi.

## 1. Domain Modelleri (`src/domain/models/`)

| Model | Alanlar | Not |
|---|---|---|
| `AssetClass` (enum) | `US_STOCK`, `CRYPTO`, `PRECIOUS_METAL` | BIST ayrı defterden gelir; sınıf sekmesinde "BIST" olarak birleşik görünümde yer alır |
| `Asset` | `id`, `symbol`, `name`, `asset_class`, `quote_currency`, `yf_symbol`, `unit` (adet / gram / ons), `is_active` | `(asset_class, symbol)` benzersiz |
| `AssetTrade` | `id`, `asset_id`, `side` (BUY/SELL), `quantity: Decimal`, `price: Decimal`, `fx_rate_to_try: Decimal`, `trade_time`, `note` | Kesirli miktar; işlem anı kuru kayıtlıdır |
| `AssetPosition` | `asset_id`, `quantity: Decimal`, `avg_cost: Decimal` | Ağırlıklı ortalama maliyet; mantık `position.py:87-122` ile aynı, `Decimal` miktarla |
| `AssetLedger` | `positions`, `from_trades(trades)` | `Portfolio.from_trades` gibi event-sourced; türev değer saklanmaz |

Doğrulamalar: miktar ve fiyat > 0; satışta mevcut miktar aşılamaz (`ValueError`); fiyat ve miktar `Decimal`, `float` kabul edilmez.

## 2. Veritabanı (`src/infrastructure/db/sqlalchemy/orm_models.py`)

Yeni tablolar (SQLite, OLTP):

| Tablo | İçerik |
|---|---|
| `assets` | Varlık tanımı; `UniqueConstraint(asset_class, symbol)` |
| `asset_trades` | İşlem kayıtları; `quantity`, `price` → `Numeric(28,10)`; `fx_rate_to_try` |
| `asset_prices` | Günlük kapanış (varlık, tarih, kapanış, para birimi, kaynak) |
| `asset_latest_prices` | Varlık başına son fiyat ve zaman damgası |
| `fx_rates` | Kur serisi (çift, tarih, değer) |

- Anahtarlar `Integer` kullanılır; `max(id)+1` `before_insert` kancasına (yalnızca `BigInteger` `id` tablolarına uygulanır) gerek kalmaz.
- Yeni tabloları `create_all` kurar. Mevcut tabloya sütun eklenmediği için `schema_migrations.py` göçü gerekmez. Gerekirse göç numarası 4'tür ve otomatik yedek devrededir.
- Üretilmiş sütun kullanılmaz (`trades.total_amount` gibi); toplam hesaplama domain'dedir.

## 3. Port ve Repository

- Port: `src/domain/ports/repositories/` altında `IAssetRepository`, `IAssetTradeRepository`, `IAssetPriceRepository`, `IFxRateRepository`.
- Implementasyon: `src/infrastructure/db/sqlalchemy/repositories/sa_asset_repository.py` vb.
- Kayıt: `src/application/container_parts/repositories.py` (`RepositorySet`).

## 4. Servis (`src/application/services/assets/`)

`AssetLedgerService`:

- `add_asset(symbol, asset_class, ...)`: sembol çevrimiçi doğrulanır (yfinance), çakışma kontrolü.
- `remove_asset(asset_id)`: işlem geçmişi varsa pasife alır.
- `record_trade(asset_id, side, quantity, price, trade_time, fx_rate)`: doğrulama + kayıt.
- `get_ledger()`: `AssetLedger.from_trades`.

Kayıt: `src/application/container_parts/services.py`. Servis, dış istemcileri doğrudan çağırmaz; port arkasından kullanır (ARCHITECTURE_GATES).

## 5. Varlık Kataloğu (`asset_catalog.py`)

Hazır seçenekler:

| Varlık | Sınıf | yfinance sembolü | Birim |
|---|---|---|---|
| Altın | `PRECIOUS_METAL` | `GC=F` | ons (gram dönüşümü ile) |
| Gümüş | `PRECIOUS_METAL` | `SI=F` | ons |
| Platin | `PRECIOUS_METAL` | `PL=F` | ons |
| Paladyum | `PRECIOUS_METAL` | `PA=F` | ons |
| Bitcoin | `CRYPTO` | `BTC-USD` | adet |
| Ethereum | `CRYPTO` | `ETH-USD` | adet |

Kullanıcı ayrıca sembolle (ör. `AAPL`, `NVDA`) ABD hissesi veya başka bir kripto ekleyebilir; sembol çevrimiçi doğrulanır. Kataloğa diğer kripto ve emtialar sonradan eklenebilir; liste kesin değildir.

## 6. Dosya Boyutu ve Eşikler

Sınıf ≤ 300 satır / 20 metot, fonksiyon ≤ 50 satır / 5 parametre (ARCHITECTURE_GATES). Domain modelleri ayrı dosyalardadır.

## 7. Testler

- Domain: kesirli miktar, ortalama maliyet, aşırı satış, `from_trades` sıralaması.
- Repository: SQLite entegrasyon (geçici DB); benzersizlik ihlali.
- Servis: sahte repo ve sahte sembol doğrulayıcı.
