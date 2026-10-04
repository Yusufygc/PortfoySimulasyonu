> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md) | Veri sahipliği: [data_architecture.md](data_architecture.md)

# Piyasa Veri Kaynakları ve Dayanıklılık

Bu sayfa uygulamanın dış veri kaynaklarını, bunları saran sağlayıcıları, önbellek davranışını ve ağ hatası dayanıklılığını özetler. Fiyatın veritabanına nasıl yazıldığı ve iki fiyat akışı için bkz. [service_portfolio_and_market.md](service_portfolio_and_market.md).

## 1. Kaynak Haritası

| Veri | Kaynak | Sağlayıcı (kod) | Önbellek |
|---|---|---|---|
| Günlük OHLCV (tüm BIST, ham) | Yahoo Finance (`yfinance`, `auto_adjust=False`) | `BistBulkDownloader`, `MarketDataSyncService` | DuckDB (`data/market_history.duckdb`) |
| Hisse listesi (BIST evreni) | TradingView Scanner API | `BistBulkDownloader.fetch_all_bist_tickers` | `bist_stocks` tablosu |
| Portföy hisseleri kapanışı | yfinance | `YFinanceMarketDataClient` (`yfinance_client.py`, `yfinance_price_client.py`) | SQLite `daily_prices` |
| Anlık fiyat | yfinance `fast_info` / `history` | `YFinancePriceLookupProvider` | SQLite `latest_prices` |
| Üst piyasa şeridi | yfinance | `YFinanceIndicatorProvider` (`MarketIndicatorsService`) | yok (her yenilemede) |
| Piyasa değeri, hisse adedi (Hisse 360) | yfinance | `YFinanceValuationProvider` | `data/_cache/financials/valuation_<TICKER>.json`, TTL 1 saat |
| Çeyreklik mali tablolar | İş Yatırım (JSON uç noktası) | `isyatirim_provider.py` | `data/_cache/financials/<TICKER>_<PB>.json`, TTL 12 saat |
| TÜFE (enflasyon) | TCMB EVDS | `EvdsTufeProvider` | `data/_cache/financials/tufe_index.json`, TTL 24 saat |
| Mevduat faizi, benchmark serileri | TCMB EVDS, yfinance, kazıma (countryeconomy, exchange-rates.org, macrotrends) | `AnalysisBenchmarkService`, `ScrapedBenchmarkProvider`, `EvdsClient` | bellek içi |
| KAP ortaklık yapısı | KAP (kamuya açık API) | `kap_shareholder_provider.py` | `data/_cache/kap/` (şirket listesi haftalık TTL), SQLite `kap_*` tabloları |
| Kurumsal aksiyon duyuruları | KAP kamuya açık duyuru listesi ve bildirim sayfaları | `kap_mkk_provider.py` | `corporate_action_candidates` tablosu |
| Optimizasyon fiyatları | DuckDB (eksik hissede yfinance) | `DuckDBOptimizationMarketDataProvider`, `YFinanceOptimizationMarketDataProvider` | DuckDB |
| BIST tatil takvimi | Kod içi liste (2020-2030) | `bist_holiday_calendar.py`, `BistHolidayProvider` | yok |
| Gemini (LLM) | Google Gemini API | `GeminiChatProvider`, `GeminiAdvisorChatProvider` | yok |
| AI_Core tahmin servisi | Yerel FastAPI (`AI_CORE_API_URL`) | `AICoreFastAPIClient` | yok |

Benchmark kodları (`AnalysisBenchmarkService`): `bist100` (XU100), `gold` (gram altın), `silver` (gram gümüş), `usd`, `euro`, `deposit` (TCMB mevduat, EVDS `TP.KTF10`), `cpi` (TÜFE, EVDS `TP.FG.J0`). EVDS anahtarı yoksa veya EVDS erişilemezse mevduat faizi `TCMB_DEPOSIT_RATE_FALLBACK` değerine (varsayılan %45) düşer.

## 2. Ticker Biçimi

Kanonik ticker uzantısızdır (`THYAO`). `.IS` yalnızca yfinance sınırında eklenir (`src/domain/ticker.py`: `clean_ticker`, `to_yf_symbol`). Endeks (`^XU100`), kur (`USDTRY=X`) ve zaten uzantılı semboller olduğu gibi kalır. Ayrıntı: [data_architecture.md](data_architecture.md).

## 3. Yeniden Deneme (`src/infrastructure/retry.py`)

`retry_call(operation, attempts=3, base_delay=1.0, is_retryable=..., label=...)` geçici hatalarda üstel bekleyerek (1 sn, 2 sn...) yeniden dener; son denemede veya kalıcı hatada özgün istisna fırlatılır.

Geçici sayılan hatalar (`is_transient_error`): `URLError`, `TimeoutError`, `ConnectionError`, `socket.timeout`, HTTP 408/429/500/502/503/504 (`HTTPError`), `requests` bağlantı/zaman aşımı/5xx ve `YFRateLimitError`. 4xx ve ayrıştırma hataları denenmez. `raise_for_transient_status(response)` ile `requests` yanıtındaki 429/5xx durumu hataya çevrilir.

Kullanan istemciler: yfinance indirme (`YFinanceMarketDataClient._download_dataframe`) ve optimizasyon verisi, EVDS, KAP (kamuya açık kaynak ve ortaklık), İş Yatırım toplu çekim, ölçüt kazıyıcısı ve `BistBulkDownloader` (burada her hata yeniden denenir: yfinance çoğu hatayı genel istisna olarak döndürür; bekleme 2 sn, 4 sn).

Bilinçli olarak denenmeyenler: tek hisse anlık fiyat sorguları (`YFinancePriceLookupProvider`) ve değerleme sağlayıcısı; arayüzü bekletmemek için hata `None` veya boş sonuç olarak döner.

Testlerde bekleme `tests/conftest.py` ile kapatılır (`retry._sleep` değiştirilir).

## 4. Hata Aileleri ve Geri Düşme

- `MARKET_DATA_FALLBACK_ERRORS` (`infrastructure/market_data/_errors.py`): yfinance, `urllib`, JSON ayrıştırma, `MarketDataUnavailableError` ve benzeri beklenen hataları tek ailede toplar; kontrolsüz `except Exception` kullanılmaz.
- İstemci hataları `MarketDataUnavailableError` ile sarılır; çağıran katman deterministik geri düşmeyi seçer (ör. EVDS yok -> sabit mevduat faizi; AI_Core yok -> demo sağlayıcı; İş Yatırım yok -> Hisse 360 yedek veri).
- `yfinance_lock`: yfinance çağrıları süreç genelinde serileştirilir. Kilit yeniden deneme beklemesi sırasında tutulmaz.
- yfinance zaman dilimi önbelleği geçici klasörde tutulur (`<temp>/portfoy-simulasyonu/yfinance-cache`).

## 5. DuckDB Okuyucuları

`DuckDBMarketHistoryRepository` (salt okunur, her çağrıda kısa ömürlü bağlantı) toplu okuma sunar: `list_tickers`, `get_price_series(_bulk)`, `get_latest_dates`, `find_price_breaks` ve sermaye artırımı faktörleriyle **düzeltilmiş** okuma. `DuckDBOptimizationMarketDataProvider` 504 günlük fiyatı ve kovaryans girdisini DuckDB'den çeker. Sahiplik ve yazma kuralları için [data_architecture.md](data_architecture.md), düzeltme formülleri için [market_corporate_actions.md](market_corporate_actions.md).

## 6. Seans ve Takvim

`BistMarketSessionService` normal gün 10:00-18:10, yarım gün 10:00-13:00 olarak seansı belirler. `MarketTradingCalendar` işlem günü ve yarım gün kararını verir; üretimde `BistTradingCalendarProvider` BIST resmi tatil takvimini kullanır. `MarketDataSyncService.get_last_completed_trading_day` son kapanmış işlem gününü hesaplar. Otomatik senkron: açılıştan 5 sn sonra ve hafta içi 18:15'te ([settings_and_system.md](settings_and_system.md)).

**Piyasa saati (`src/domain/market_clock.py`):** BIST takvimine bağlı "şimdi/bugün" (seans koruması, bugünkü fiyat kontrolü, işlem tarihi/saati varsayılanı, zamanlanmış senkron hedef günü, tarayıcı "bugün"ü) `date.today()` / `datetime.now()` yerine `market_today()`, `market_now()`, `market_time()` ile alınır. Bunlar `Europe/Istanbul` duvar saatini **saat dilimi bilgisi taşımayan** değer olarak döner (mevcut naive tarih/saat değerleriyle karşılaştırılabilir). `tzdata` yoksa Türkiye'nin sabit UTC+3 değeri kullanılır. Bilgisayar saat dilimi Türkiye'den farklıysa bu, seans penceresinin ve "bugün" gününün kaymasını önler. Yerel zamanın doğru olduğu yerler (sohbet saati, dosya adı damgası, kayıt oluşturma damgaları, tarama aralığı süresi) bilinçli olarak yerel saatte kalır. `tests/test_market_clock_guard.py` tamamen dönüştürülmüş modülleri korur.

## 7. Yeni Kaynak Eklerken

1. Domain'de port tanımla (`ports/services/`), `infrastructure/` altında uygula.
2. Ağ çağrısını `retry_call` ile sar; beklenen hataları `MarketDataUnavailableError`'a çevir.
3. Gerekirse dosya önbelleği ve TTL ekle (`data/_cache/`).
4. Container fabrikasına (`container_parts/market_clients.py`) kaydet.
5. Testte ağ kullanma; sahte yanıt veya `monkeypatch` kullan (`tests/test_repo_guards.py` canlı ağ çağrısını yasaklar).
