> Ana sayfa: [index.md](index.md) | Varlık defteri: [service_asset_ledger.md](service_asset_ledger.md) | Veri kaynakları: [service_market_data_providers.md](service_market_data_providers.md)

# Varlık Fiyatları, Kur ve Grafik

BIST dışı varlıkların (kripto, emtia, ABD hissesi) sembol çözümü, fiyat sağlayıcısı, piyasa takvimi, yenileme, kur ve Genel Bakış grafiği için fiyat serisi. BIST fiyat hattı ([service_portfolio_and_market.md](service_portfolio_and_market.md)) bu sayfadaki kurallardan etkilenmez.

## 1. Sembol Çözümleme

`src/domain/asset_symbols.py` `resolve_yf_symbol`: `BTC` -> `BTC-USD`; `AAPL` -> `AAPL`; `GC=F`, `^IXIC`, `BRK.B`, `BTC-USD` olduğu gibi. Hiçbiri `.IS` almaz. BIST yolundaki `to_yf_symbol` (`domain/ticker.py`) ve `normalize_lookup_ticker` (`price_lookup_service.py`) değişmedi; `.IS` yalnızca BIST yolunda eklenir. Varlığın `yf_symbol` alanı kaydedilir ve yfinance'e olduğu gibi verilir.

## 2. Fiyat Sağlayıcı

- Port: `src/domain/ports/services/i_asset_price_provider.py` (`get_latest`, `get_history`) ve `i_asset_symbol_verifier.py` (`verify`).
- Gerçekleştirim: `src/infrastructure/market_data/yfinance_asset_price_provider.py` (`YFinanceAssetPriceProvider`: fiyat + doğrulayıcı); `retry_call` ve `YFinanceGate` kullanır.
- **Son fiyat:** önce dakika barı (`period=1d`, `interval=1m`); piyasa kapalıysa son günlük kapanışa (`5d`, `1d`) düşülür. Alınamayan semboller sonuçtan düşer, istisna fırlatılmaz. `get_history` ve `verify` ağ hatasında `MarketDataUnavailableError` yükseltir.
- **Duyarlılık:** Yahoo dakika/günlük değerleri float32 kalıntısı taşır (`3898.9` -> `3898.89990234`); fiyatlar 7 anlamlı haneye yuvarlanır (`DAILY_SIGNIFICANT_DIGITS = 7`), küçük kripto fiyatlarının duyarlılığı korunur.

## 3. Piyasa Takvimi ve Yenileme

`asset_market_calendar.py`: kripto 7/24; ABD hissesi New York 09:30-16:00 hafta içi; metal vadeli CME (pazar 18:00 ET - cuma 17:00 ET, günlük 17:00-18:00 ET mola). Resmî tatiller modellenmez. `tzdata` yoksa seans hep açık sayılır (uyarı loglanır). BIST kuralları (`live_price_rule`, `CurrentPriceResolver`, `BistMarketSessionService`) varlıklar için kullanılmaz.

`AssetPriceRefreshService` (`asset_price_refresh_service.py`):

- `refresh_latest(only_open=True)`: seansı kapalı sınıfları atlar, `AssetRefreshResult` (güncellenen / atlanan / alınamayan) döner.
- `backfill_history(asset_id)`: yeni varlık için varsayılan 365 günlük kapanış geçmişi.
- `cached_price`: arayüz için ağsız son fiyat.

Tetik: `AssetsController(autostart=True)` 5 dakikada bir sessiz `refresh_latest(only_open=True)` çalıştırır; `PriceRefreshController.pricesChanged` Portföyüm'ü yeniden okutur (`app.py` `_wire_price_refresh`). Zaman kaynakları `market_clock` veya enjekte saattir ([service_market_data_providers.md](service_market_data_providers.md)).

## 4. Kur

`FxRateService` (`fx_rate_service.py`): `get_rate` doğrudan, yoksa ters kuru (`1/x`) kullanır; aynı para biriminde 1. `refresh_latest(["USD","EUR"])` güncel kuru `fx_rates`'e yazar; `backfill` geçmiş kuru yazar. Kur sembolü USD için `TRY=X`, diğerleri `EURTRY=X`. İşlem anı kuru işlemle birlikte (`fx_rate_to_try`) saklanır. Ons->gram sabiti tek yerdedir: `src/domain/units.py` (`TROY_OUNCE_GRAMS = 31.1034768`, `ounce_price_to_gram_price`); `benchmark_service.py` ve `market_indicators_service.py` bunu kullanır.

## 5. Genel Bakış Grafiği

`AssetChartService` (`src/application/services/assets/asset_chart_service.py`) sembolü (`BTC` veya `BTC-USD`, büyük/küçük harf fark etmez) defterdeki varlığa eşler ve `asset_prices` kapanışlarını (3 yıl, yalnızca yerel veritabanı, ağ yok) döner. `ChartController._load_candles` sırası: DuckDB piyasa geçmişi -> SQLite BIST fiyatları -> varlık defteri (`load_asset_candles`). BIST yolu ve karakterizasyon testleri değişmedi; BIST'te bulunan kod her zaman önceliklidir.

- Varlık fiyatı yalnızca kapanış olarak saklanır; açılış/yüksek/düşük kapanıştan türetilir, hacim yoktur. 1 USD altı fiyatlarda 6 hane hassasiyet korunur.
- Son fiyat metni varlığın para birimini gösterir (`$`, `€`); TRY biçimi değişmedi.
- Hızlı seçici (`chartController.quickAssets`) varlık defterindeki sembolleri listeler; varlık eklenince `refreshAssets` ile yenilenir.

## 6. Bilinen Sınırlar

- Haftalık/aylık yeniden örnekleme 2 ondalıkta yuvarlar; çok düşük fiyatlı kriptoda haftalık/aylık mumlar kaba kalır.
- Emtia vadeli kontrat fiyatıdır; spot ile fark olabilir.
- Resmî tatiller (ABD, CME) modellenmez; kapalı piyasada son kapanış gösterilir.
- Gram birimli katalog girdisi yok; gram değerleme yolu (`Asset.unit_price`) hazırdır.

Testler: `tests/domain/test_asset_symbols_and_units.py`, `tests/application/services/assets/test_asset_market_calendar.py`, `test_asset_fx_and_refresh_services.py`, `test_asset_chart_service.py`, `tests/infrastructure/market_data/test_yfinance_asset_price_provider.py`, `tests/ui_qml/test_chart_asset_path.py`.
