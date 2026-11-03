> Ana sayfa: [index.md](index.md) | Fiyat ve kur: [service_asset_prices_fx.md](service_asset_prices_fx.md) | Sayfa: [qml_pages_guide.md](qml_pages_guide.md) | Veri modeli: [database_schema_and_orm.md](database_schema_and_orm.md)

# Varlık Defteri ve Birleşik Portföy

BIST dışı varlıkları (kıymetli maden, kripto, ABD hissesi) tutan, ana `trades`/`stocks` hattından **bağımsız** defter ve bu defterle BIST portföyünü tek TRY özetinde birleştiren servis. Portföyüm sayfasının veri kaynağıdır ([qml_pages_guide.md](qml_pages_guide.md)).

## 1. Neden Ayrı Defter

Mevcut BIST hattı BIST + TRY + tam sayı lot varsayar: `to_yf_symbol` her sembole `.IS` ekler, `trades.quantity` `BigInteger` ve `total_amount` üretilmiş sütundur, `uq_stocks_ticker` aynı kodun iki sınıfta kullanılmasını engeller (BIST'te `LINK`, `SILVR` gibi kodlar vardır), tek TRY nakit defteri ve BIST seans kuralı zorunludur. Bu hattı genişletmek TWR, nakit, optimizasyon, Excel, AI araçları ve senkronizasyonu etkilerdi. Seçilen yol model portföy örüntüsü gibi ayrı defterdir; ana BIST portföyüne dokunulmaz.

Kapsam kararları:

- **Nakit bağı yok:** Varlık alımı BIST TRY nakdini düşürmez; USD varlık alımının finansmanı ayrı bir soru açar.
- **Analiz sınırı:** Birleşik TWR, risk metrikleri, optimizasyon evreni, Excel raporu, AI danışman araçları ve benchmark listesi yalnızca BIST portföyünde kalır ([roadmap.md](roadmap.md)).
- **Emtia vadeli kontrattır:** `GC=F`, `SI=F`, `PL=F`, `PA=F` spot'tan küçük sapma gösterebilir; arayüzde not düşülür.

## 2. Domain (`src/domain/models/`)

| Model | Not |
|---|---|
| `AssetClass` | `US_STOCK`, `CRYPTO`, `PRECIOUS_METAL`; BIST ayrı defterden gelir |
| `Asset` (`asset.py`) | `symbol`, `name`, `asset_class`, `quote_currency`, `yf_symbol`, `unit` (adet/gram/ons), `is_active`; `(asset_class, symbol)` benzersiz; `unit_price` gram birimli madende ons fiyatını gram fiyatına çevirir |
| `AssetTrade` | BUY/SELL, `quantity` ve `price` `Decimal`, `fx_rate_to_try` (işlem anı kuru), `trade_time`, `note`; `float` kabul edilmez |
| `AssetPosition`, `AssetLedger` (`asset_position.py`) | Ağırlıklı ortalama maliyet; `AssetLedger.from_trades` event-sourced (türev değer saklanmaz). Maliyet hem varlık para biriminde hem her alımın kendi kuruyla TRY tutulur |
| `AssetPrice`, `AssetLatestPrice`, `FxRate`, `AssetQuote` (`asset_price.py`) | Günlük kapanış, son fiyat, kur ve sağlayıcı yanıtı |
| `AllocationClass`, `HoldingValuation`, `AllocationSlice`, `UnifiedSummary`, `daily_gain` (`unified_portfolio.py`) | Birleşik değerleme modelleri; `AllocationClass` BIST hissesi ve nakdi de içerir |

Doğrulamalar: miktar ve fiyat > 0; satışta mevcut miktar aşılamaz; geriye dönük satış veya satışı besleyen alımı silme reddedilir.

## 3. Veritabanı

SQLite (OLTP); yeni tabloları `create_all` kurar, `schema_migrations.py` göçü gerekmedi. Ayrıntı: [database_schema_and_orm.md](database_schema_and_orm.md).

| Tablo | İçerik |
|---|---|
| `assets` | Varlık tanımı |
| `asset_trades` | İşlemler; `quantity`, `price` `Numeric(28,10)` |
| `asset_prices` | Günlük kapanış (varlık, tarih, kapanış, para birimi, kaynak) |
| `asset_latest_prices` | Varlık başına son fiyat ve zaman damgası |
| `fx_rates` | Kur serisi (çift, tarih, değer) |

Anahtarlar `Integer`'dır (BIGINT `max(id)+1` kancasına gerek yok). Üretilmiş sütun kullanılmaz. Varlık fiyatları DuckDB'de değil SQLite'tadır; DuckDB yalnızca BIST içindir ([data_architecture.md](data_architecture.md)).

## 4. `AssetLedgerService` (`src/application/services/assets/asset_ledger_service.py`)

- `add_asset(symbol, name, asset_class, quote_currency, **options)` (`options`: `yf_symbol`, `unit`) / `add_catalog_asset(key)`: sembol `IAssetSymbolVerifier` portuyla çevrimiçi doğrulanır (doğrulayıcı yoksa atlanır); ağ hatası "kaynağa ulaşılamıyor" doğrulama hatasına çevrilir.
- `remove_asset(id)`: işlem geçmişi varsa pasife alır (aynı sembol yeniden eklenirse etkinleştirilir), geçmişsizse siler.
- `record_trade(asset_id, side, quantity, price, **options)` (`options`: `trade_date` varsayılan bugün, `trade_time`, `fx_rate_to_try`, `note`; kalite eşiği için seçenek sözlüğü kullanılır) ve `delete_trade(...)`: varlığın tüm işlemleri tarih-saat sırasıyla `AssetLedger` ile yeniden uygulanarak doğrulanır.
- `get_ledger()`, `list_assets()`, `get_trades()`. Girdiler `Decimal` veya `str`; ondalık virgül kabul edilir.

### Katalog (`asset_catalog.py`)

| Anahtar | Varlık | yfinance | Birim |
|---|---|---|---|
| `XAU` / `XAG` / `XPT` / `XPD` | Altın / Gümüş / Platin / Paladyum | `GC=F` / `SI=F` / `PL=F` / `PA=F` | ons (USD) |
| `BTC` / `ETH` / `SOL` / `XRP` | Kripto | `BTC-USD`, `ETH-USD`, `SOL-USD`, `XRP-USD` | adet |

ABD hisseleri (NASDAQ/NYSE) katalogda yoktur; kullanıcı sembolle ekler ve sembol çevrimiçi doğrulanır. Gram birimi (`AssetUnit.GRAM`) modelde vardır ama gram katalog girdisi yoktur.

## 5. Birleşik Portföy (`UnifiedPortfolioService`)

`get_summary(display_currency)` BIST açık pozisyonları + BIST TRY nakdi + varlık defterini tek TRY özetine (`UnifiedSummary`) çevirir.

| Parça | Dosya |
|---|---|
| BIST okuyucu | `bist_holdings_reader.py` (`PortfolioService` + `CurrentPriceResolver`) |
| Varlık okuyucu | `asset_holdings_reader.py` |
| Servis | `unified_portfolio_service.py` |

Kurallar:

- **Birleşim:** Toplam değer = pozisyon değerleri + BIST nakdi. Container `CurrentPriceResolver` ve `StockLookupService` örneklerini paylaşır.
- **Varlık fiyatı:** son fiyat ile son günlük kapanıştan tarihi daha yeni olan seçilir (eşitse son fiyat). Değer = `miktar x birim fiyat x güncel kur`.
- **Maliyet ve K/Z:** TRY maliyet her alımın kendi kuruyla tutulur; `unrealized_pl_try` kur farkını da içerir.
- **Eski veri işaretlenir:** fiyat (kripto 3 gün, diğerleri 7 gün) veya kur (7 gün) eşikten eskiyse pozisyon son bilinen değerle gösterilir ama `is_stale` olur; özet `stale_symbols` taşır ve Portföyüm uyarı satırı gösterir.
- **Eksik veri sessizce atlanmaz:** fiyat veya kur yoksa pozisyon TRY maliyetiyle değerlenir, `is_priced=False` olur; özet `is_partial` ve `unpriced_symbols` taşır. (`Portfolio.total_market_value` ise fiyatsız pozisyonu atlar; iki davranış bilinçli olarak farklıdır.)
- **Günlük kazanç:** varlığın kendi para biriminde günlük değişim; kazanç = bugünkü değer - önceki kapanış değeri (`değer - değer/(1+yüzde/100)`); kur hareketi dahil değil.
- **Dağılım:** sınıf bazlı dilimler (BIST, ABD hisse, kripto, emtia, nakit), değere göre azalan; `weight_pct` toplam değere (nakit dahil) göredir.
- **Gösterim:** yalnızca TRY ve USD; kur yoksa TRY'ye düşer ve `display_unavailable=True` olur.

**Tek hesap yolu:** Eski `DashboardController` değerlemesi (yaklaşık günlük kazanç `değer x yüzde`) 2026-11-01'de kaldırıldı; portföy rakamlarının tek kaynağı bu servistir. `DashboardController` yalnızca BIST işlemleri, sermaye, BIST haftalık/aylık getiri ve Excel raporunu sunar. Piyasa kapalı günde günlük K/Z kartı "Son İşlem Günü" etiketiyle gösterilir.

### Ortak nakit havuzu (E5.2)

Tüm alım-satımlar tek nakit havuzundan yapılır; havuz para birimine göre tutulur (TL ve USD), bakiye saklanmaz, olaylardan türetilir.

| Parça | Görev |
|---|---|
| `FxConversion` / `FxConversionService` | TL <-> USD döviz al/sat (`buy_usd`, `sell_usd`); kur kullanıcıdan (verilmezse güncel kur), ücret TL. Alım TL bakiyesini, satım USD bakiyesini aşamaz. İç transfer: TWR dış akışı değildir. |
| `CashPoolService` | `try_balance`, `usd_balance`, `balances`; `usd_timeline_valid` silme/ekleme sonrası USD bakiyesinin hiçbir anda eksiye düşmediğini sorar. |
| `PooledCashMovementRepository` | BIST'in TL nakit görünümü: gerçek hareketler + döviz çevirmelerinin TL bacağı + TL ile ödenen nakde bağlı varlık işlemleri (sentetik, negatif kimlikli WITHDRAW/DEPOSIT). `PortfolioService`, nakit servisi ve analiz/TWR bu depoyu okur; böylece BIST alım gücü ve TWR havuzla tutarlıdır. |
| `AssetTrade.cash_linked` | Yeni işlemler `True` (havuzu etkiler); göç 5 ile mevcut kayıtlar `False` kalır ve nakde dokunmaz. |

Kurallar: varlık alımı **ödeme para biriminin** (`Asset.settlement_currency`, şimdilik fiyat para birimi) bakiyesini aşamaz; USD yetmezse "Önce Döviz Al ile TL'den USD alın" hatası verilir (otomatik çevirme yoktur). Desteklenen nakit para birimleri TRY ve USD; başka birimle ödenen varlık reddedilir. Satış ödeme para birimine net gelir (tutar - ücret) ekler. Nakde bağlı USD satışını veya döviz alımını silmek, sonraki USD ödemelerini eksiye düşürüyorsa reddedilir. TL girişini silmek (döviz satımı, TL ile satılan varlık) sonraki BIST alımı, nakit çekimi ya da TL ile ödenen varlık alımını yetersiz bakiyeye düşürüyorsa reddedilir (`CashPoolService.ensure_try_after_removal`, mevcut zaman çizelgesi doğrulayıcısı ve sentetik hareket kimlikleriyle). Sıfırlama döviz çevirmelerini de siler.

### Birleşik özette nakit (E5.4)

`UnifiedSummary.cash_try` TL nakdi (ortak havuz: döviz çevirme ve TL ile ödenen varlıklar düşülmüş), `usd_cash` USD nakdi, `usd_cash_try` güncel USD/TRY kuruyla TL karşılığıdır; toplam değer ve CASH dilimi ikisini de içerir (`cash_weight_pct`). USD kuru yoksa USD nakit TL toplamına katılamaz, özet kısmi (`unpriced_symbols` içinde `USD`) olur. TL/USD gösterim anahtarı toplamı çevirmeye devam eder; nakit kartı USD nakdi ayrıca USD cinsinden yazar.

### Gram altın ve işlem para birimi (E5.3)

`Asset.trade_currency` (boşsa fiyat para birimi) işlemin ödendiği nakit para birimini belirler (`Asset.settlement_currency`); işlem fiyatı, ücret ve maliyet bu birimdedir. Katalogdaki **altın, gümüş, platin ve paladyum gram birimlidir ve TL ile işlem görür**: sağlayıcı fiyatı USD/ons (`GC=F` vb.) kalır, değerleme sırasında `ons fiyatı / 31,1035 x USDTRY` ile TL/gram'a çevrilir (`AssetHoldingsReader`), alım TL nakitten düşer, arayüz önerilen fiyatı TL/gram verir. Kur gerekmez (işlem kuru 1). Eski ons kayıtları değişmeden kalır (göç 6 mevcut varlıklara boş `trade_currency` verir); katalogdaki `XAU` zaten ekliyse gram altın için önce eski kaydı kaldırmak gerekir.

Günlük değişim yüzdesi USD fiyat serisinden gelir (kur hareketini içermez); K/Z ise TL maliyete göre hesaplandığından kur etkisini içerir.

### Pozisyon okuma servisi (`PositionQueryService`)

`src/application/services/portfolio/position_query_service.py`; domain modeli `position_snapshot.py` (`PositionSnapshot`, `PortfolioPositions`).

- **Tek kaynak:** ana portföy pozisyonu `BistHoldingsReader` ile (Portföyüm'le aynı kod yolu) değerlenir; Hisse Detay ve Model Portföy ekranları aynı servisten okur. Aynı pozisyonun değeri, maliyeti ve K/Z'si Portföyüm, Hisse Detay ve Excel geçmişinde birebir aynıdır (`tests/application/test_position_query_service.py`).
- **Model portföy:** `model_positions(portfolio_id)` fiyatı çözer (çözümleyici, canlı önbellek, son kapanış), önceki kapanışa göre günlük değişimi ve toplam değere göre ağırlığı hesaplar. Eskiden Hisse Detay model bağlamında ağırlığı yalnızca nakde böldüğünden şişkin çıkıyordu; düzeldi.
- **Fiyat:** `quote(ticker, stock_id)` sırasıyla çözümleyici, canlı önbellek, DuckDB piyasa geçmişi, SQLite kapanışı.
- **Ağırlık tanımları:** Portföyüm'de `weight_pct` BIST + varlık defteri + nakit toplamına, Hisse Detay'da yalnızca BIST portföyü + nakde göredir; Excel geçmişinde ağırlık nakit hariç pozisyon toplamınadır. Üç tanım bilinçli olarak ayrıdır.
- **Emir ön izlemesi:** `src/domain/models/trade_impact.py::preview_order` (lot, ağırlıklı ortalama maliyet, nakit sonrası, yetersiz nakit/lot kararı); denetleyici yalnızca biçimler.

## 6. Container ve Test

`RepositorySet`: `asset_repo`, `asset_trade_repo`, `asset_price_repo`, `fx_rate_repo`. `ServiceSet`: `asset_ledger_service`, `asset_price_refresh_service`, `fx_rate_service`, `unified_portfolio_service`, `asset_chart_service`.

Testler: `tests/domain/test_asset_models.py`, `test_unified_portfolio_models.py`; `tests/infrastructure/db/test_asset_repositories.py`; `tests/application/services/assets/test_asset_ledger_service.py`, `test_unified_portfolio_service.py`; `tests/application/test_asset_container_wiring.py`.

Sınıf başına eşikler ve gerçek ağ çağrısı yasağı için bkz. [code_quality_guardrails.md](code_quality_guardrails.md) ve [testing_strategy.md](testing_strategy.md).
