# 03 — Fiyat ve Kur Hattı

> Ana sayfa: [index.md](index.md) | Günlük: [log.md](log.md) | Önceki: [02_varlik_defteri.md](02_varlik_defteri.md) | Sonraki: [04_portfoyum_sayfasi.md](04_portfoyum_sayfasi.md)

Durum: Aşama 3 **Uygulandı** (2026-11-01); birleşik servis ve gram değerleme (Aşama 4) **Taslak**

## 0. Aşama 3'te Uygulananlar

| Konu | Dosya |
|---|---|
| Sembol çözümleyici | `src/domain/asset_symbols.py` (`resolve_yf_symbol`) |
| Ortak ölçü sabiti | `src/domain/units.py` (`TROY_OUNCE_GRAMS = 31.1034768`, `ounce_price_to_gram_price`); `benchmark_service.py` ve `market_indicators_service.py` artık bunu kullanır |
| Port | `src/domain/ports/services/i_asset_price_provider.py` (`get_latest`, `get_history`); model `AssetQuote` (`asset_price.py`) |
| yfinance gerçekleştirimi | `src/infrastructure/market_data/yfinance_asset_price_provider.py` (`YFinanceAssetPriceProvider`: fiyat + `IAssetSymbolVerifier`) |
| Piyasa takvimi | `src/application/services/assets/asset_market_calendar.py` |
| Yenileme | `src/application/services/assets/asset_price_refresh_service.py` |
| Kur | `src/application/services/assets/fx_rate_service.py` |
| Container | `MarketClientSet.asset_price_provider`; `ServiceSet.asset_price_refresh_service`, `fx_rate_service`; `AssetLedgerService` doğrulayıcıyı alır |
| Test | `tests/domain/test_asset_symbols_and_units.py`, `tests/application/services/assets/test_asset_market_calendar.py`, `test_asset_fx_and_refresh_services.py`, `tests/infrastructure/market_data/test_yfinance_asset_price_provider.py` |

Davranış notları:

- **Sembol kuralı:** `BTC` → `BTC-USD`; `AAPL` → `AAPL`; `GC=F`, `^IXIC`, `BRK.B`, `BTC-USD` olduğu gibi. Hiçbiri `.IS` almaz. BIST yolundaki `to_yf_symbol` ve `normalize_lookup_ticker` değişmedi.
- **Son fiyat:** önce dakika barı (`period=1d`, `interval=1m`); piyasa kapalıysa son günlük kapanışa (`5d`, `1d`) düşülür. Alınamayan semboller sonuçtan düşer, istisna fırlatılmaz. Geçmiş (`get_history`) ve doğrulama (`verify`) ağ hatasında `MarketDataUnavailableError` yükseltir; `AssetLedgerService` bunu "kaynağa ulaşılamıyor" doğrulama hatasına çevirir.
- **Duyarlılık:** Yahoo dakika ve günlük değerleri float32 kalıntısı taşır (`3898.9` → `3898.89990234`); fiyatlar 7 anlamlı haneye yuvarlanır (küçük kripto fiyatları duyarlılığını korur).
- **Seans takvimi:** kripto 7/24; ABD hissesi New York 09:30-16:00 hafta içi; metal vadeli CME (pazar 18:00 ET - cuma 17:00 ET, günlük 17:00-18:00 ET mola). Resmî tatiller modellenmez. `tzdata` yoksa seans hep açık sayılır (uyarı loglanır).
- **Yenileme:** `refresh_latest(only_open=True)` seansı kapalı sınıfları atlar ve `AssetRefreshResult` (güncellenen / atlanan / alınamayan) döner; `backfill_history(asset_id)` yeni varlık için varsayılan 365 günlük kapanış geçmişini çeker. Tüm zaman kaynakları `market_clock` veya enjekte edilen saat.
- **Kur:** `FxRateService.get_rate` doğrudan, yoksa ters kuru (`1/x`) kullanır; aynı para biriminde 1. `refresh_latest(["USD","EUR"])` güncel kuru `fx_rates` tablosuna yazar; `backfill` geçmiş kuru yazar. Kur sembolü: USD tabanlı `TRY=X`, diğerleri `EURTRY=X`.
- **Canlı doğrulama (2026-11-01, salt okunur):** `BTC-USD`, `GC=F`, `AAPL`, `TRY=X`, `EURTRY=X` fiyat verdi; geçersiz sembol atıldı; `GC=F` için dakika barı yokken günlük kapanışa düşüldü.

### Aşama 4'e bırakılanlar

- **Gram birimi:** `AssetUnit.GRAM` varlıkta sağlayıcı fiyatı ons olduğundan değerlemede `ounce_price_to_gram_price` uygulanacak; birleşik serviste "birim başına fiyat" kuralı yazılacak.
- **`PriceRefreshController.pricesChanged` bağlantısı:** yenileme servisleri hazır; arayüz denetleyicisi Aşama 5'te yazılınca bağlanacak. Varlık eklenince geçmiş doldurma çağrısı da orada orkestre edilecek.
- Fiyat yenileme zamanlayıcısı ve seans dışı davranışın arayüz göstergesi.

## 1. Sembol Çözümleme

Mevcut durumda iki tutarsız kural var:

- `src/domain/ticker.py:23` `to_yf_symbol`: `^`, `=` veya `.` içeren sembolü olduğu gibi bırakır, diğer her şeye `.IS` ekler. `GC=F` çalışır, `AAPL` ve `BTC-USD` bozulur.
- `src/application/services/market/price_lookup_service.py:14` `normalize_lookup_ticker`: nokta yoksa `.IS` ekler; `GC=F` bile `GC=F.IS` olur.

**Çözüm:** `AssetSymbolResolver` (sınıfa duyarlı, tek nokta). Varlık defterinin `yf_symbol` alanı kaydedilir ve olduğu gibi yfinance'e verilir; `.IS` yalnızca BIST yolunda eklenmeye devam eder. BIST yolundaki mevcut fonksiyonlara dokunulmaz.

## 2. Fiyat Sağlayıcı

- Port: `IAssetPriceProvider` (`src/domain/ports/services/`): `get_latest(symbols)`, `get_history(symbol, start, end)`.
- Implementasyon: yfinance tabanlı; mevcut `yfinance_price_lookup_provider.py` ve `yfinance_client.py` mantığı, `retry_call` ve `YFinanceGate` yeniden kullanılır.
- DuckDB `market_history` yalnızca BIST içindir; varlık fiyatları SQLite'ta `asset_prices` / `asset_latest_prices` içinde tutulur.

## 3. Yenileme Servisi

`AssetPriceRefreshService` (`src/application/services/assets/`):

- Varlık eklenince geçmiş fiyat backfill edilir.
- Sınıf bazlı takvim ve seans:

| Sınıf | Takvim |
|---|---|
| Kripto | 7/24; hafta sonu da güncel |
| ABD hisse | ABD piyasa saatleri (İstanbul saatiyle yaklaşık 16:30-23:00), tatiller |
| Kıymetli maden (vadeli) | Yaklaşık 24 saat, hafta içi |

- BIST kuralları (`live_price_rule`, `CurrentPriceResolver`, `BistMarketSessionService`) varlıklar için **kullanılmaz**.
- Tarih ve saat işlemleri `market_clock` üzerinden yapılır (`tests/test_market_clock_guard.py`).
- Yenileme tetiği: mevcut `PriceRefreshController.pricesChanged` yeni controller'a bağlanır (`src/ui_qml/app.py` `_wire_price_refresh`).

## 4. Kur

`FxRateService`:

- Ana kur: `TRY=X` (USD/TRY); gerekirse `EURTRY=X`. Bu semboller piyasa şeridi için zaten çekiliyor (`market_indicators_service.py`).
- İşlem anı kuru işlemle birlikte (`fx_rate_to_try`) saklanır; güncel kur `fx_rates` tablosundan veya son çekimden gelir.
- TRY/USD gösterim anahtarı toplamları bu servisle çevirir.
- **Ons→gram sabiti** iki yerde kopyalı: `market_indicators_service.py:12` (31.1035) ve `benchmark_service.py:38` (31.1034768). Tek ortak sabite çıkarılır.

## 5. Eksik Veri Davranışı

Mevcut `Portfolio.total_market_value` fiyatı olmayan pozisyonu sessizce atlar. Yeni birleşik servis bunu yapmaz: eksik fiyat veya kur varsa ilgili satır "fiyat yok" olarak işaretlenir ve toplam "kısmi" etiketi taşır.

## 6. Testler

- Sembol çözümleyici: BIST, ABD hisse, kripto, vadeli kontrat örnekleri.
- Yenileme servisi: sahte sağlayıcı, sınıf bazlı takvim, backfill.
- Kur: sahte sağlayıcı, eksik kur durumu.
- Gerçek ağ çağrısı yok (`tests/test_repo_guards.py`); canlı yoklama gerekirse `@pytest.mark.network`.
