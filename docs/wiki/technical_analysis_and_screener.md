> Ana sayfa: [index.md](index.md) | Analiz: [service_analysis.md](service_analysis.md) | Sayfa: [qml_pages_guide.md](qml_pages_guide.md)

# Teknik Analiz, Hisse Tarayıcı ve Golden Cross

Kod: `src/application/services/analysis/technical/`. Hesaplar saf, durumsuz, ağsız NumPy/Pandas fonksiyonlarıdır; veri okuma ve orkestrasyon servis sınıflarındadır. `pandas-ta`, `ta`, `quantstats` gibi bakımsız kütüphaneler bilerek kullanılmaz.

## 1. Göstergeler (`indicators.py`)

Her fonksiyon sıralı tarih indeksli `pd.Series` alır, aynı indekse hizalı seri döner; ısınma barları `NaN` olur.

| Gösterge | Fonksiyon | Not |
|---|---|---|
| SMA, EMA | `sma`, `ema` | EMA standart `ewm(adjust=False)`. |
| RSI | `rsi(closes, 14)` | Wilder yumuşatma; kayıp sıfırsa 100. |
| MACD | `macd(12, 26, 9)` | (çizgi, sinyal, histogram). |
| Bollinger | `bollinger_bands(20, 2)` | (üst, orta, alt). |
| ATR | `atr(high, low, close, 14)` | Wilder. |
| Stochastic | `stochastic_oscillator(14, 3)` | (%K, %D). |
| CCI | `cci(20)` | |
| VWAP | `vwap(20)` | Günlük bar için 20 günlük kayan pencere VWAP'ı. |
| OBV | `obv` | Kümülatif hacim. |
| **ADX** | `adx(high, low, close, 14)` | (ADX, +DI, -DI), Wilder yumuşatma; ADX trend gücünü ölçer (>25 güçlü), yönü +DI/-DI verir. |
| **Supertrend** | `supertrend(high, low, close, 10, 3.0)` | (çizgi, yön): yön +1 yükseliş (çizgi fiyatın altında), -1 düşüş; ATR ısınma süresince 0. |

Destek/direnç (`support_resistance.py`): ortalanmış rolling pencereyle fraktal pivot tepe/dip tespiti; güncel fiyata en yakın destek (altındaki en yüksek dip) ve direnç (üstündeki en düşük tepe) döner. Hisse 360 teknik seviyelerinde kullanılır.

Kapsam dışı göstergeler: Ichimoku ve Keltner ([roadmap.md](roadmap.md)).

## 2. Hisse Tarayıcı (`screener.py`, `ScreenerService`)

`ScreenerService.scan(filter_keys)` tüm BIST'i **DuckDB'den** (sermaye artırımı düzeltmeli) okur: evren `list_tickers()`, seri `get_price_series_bulk` (100'lük gruplar), son ~420 günlük pencere (EMA200 ısınması için). Canlı API çağrısı yapmaz. Gerçek veride 624 hisse yaklaşık 3-4 sn sürer.

Her hisse için son bar `IndicatorSnapshot` olarak özetlenir (RSI14, EMA200, MACD çizgi/sinyal ve bir önceki bar değerleri, hacim ve 20 günlük ortalaması, Bollinger alt/üst bant, ADX14, +DI14, -DI14, Supertrend yönü ve bir önceki yönü). High/Low/Hacim yoksa bu alanlar `None` kalır ve ilgili filtreler eşleşmez.

`SCREENER_FILTERS` içindeki 10 hazır strateji:

| Anahtar | Koşul |
|---|---|
| `rsi_oversold` | RSI < 35 |
| `rsi_oversold_above_ema200` | RSI < 35 ve kapanış > EMA200 |
| `rsi_overbought` | RSI > 65 |
| `macd_bullish_cross` | MACD çizgisi sinyali yukarı kesti |
| `macd_bullish_cross_volume_spike` | Yukarı kesişim ve hacim > 20 günlük ortalama |
| `volume_spike` | Hacim > 20 günlük ortalamanın 1,5 katı |
| `bollinger_lower_band_touch` | Kapanış alt bandın %2 yakınında veya altında |
| `bollinger_upper_band_touch` | Kapanış üst bandın %2 yakınında veya üstünde |
| `adx_strong_uptrend` | ADX > 25 ve +DI > -DI |
| `supertrend_buy_signal` | Supertrend son barda -1'den +1'e döndü |

Arayüz (`ScreenerController`): filtre listesi doğrudan `SCREENER_FILTERS`'tan üretilir; yeni filtre eklemek yalnızca bu sözlüğe (ve snapshot alanlarına) kayıt gerektirir. Tarama arka planda çalışır, sonuç hisse, tetikleyen strateji ve son fiyatla listelenir. Satıra çift tıklama grafiği, tek tıklama Hisse 360'ı açar. `scan_ticker` tek hisse için aynı filtreleri çalıştırır.

## 3. Golden / Death Cross (`golden_cross.py`, `TechnicalAnalysisService`)

- **Tanım:** EMA(50) EMA(200)'ü yukarı keserse Golden Cross (boğa), aşağı keserse Death Cross (ayı). EMA tohumu ilk `span` barın SMA'sıdır (TradingView uyumu; pandas varsayılanı ilk fiyatı tohum alıp tarih kaymasına yol açar). EMA200 için asgari bar sayısı uzun periyodun iki katıdır.
- **Tarama:** `scan_all` tüm BIST'i DuckDB'den (düzeltilmiş fiyat) 60'lık gruplarla okur ve yeni olayları idempotent upsert ile SQLite `cross_events` tablosuna yazar (`ticker, cross_date, cross_type` benzersiz; `short_ma`, `long_ma`, `close_price`, `detected_at`). Bozuk fiyat serileri (medyandan 1000 kat sapan) atlanır. `scan_ticker` tek hisse içindir.
- **Türetilmiş veri:** `cross_events` yeniden üretilebilir. Eski `stock_id` anahtarlı `golden_cross_events` tablosu açılışta silinir.
- **Arayüz** (`GoldenCrossController`, Hisse Tarayıcı > Golden Cross): son N gün ve tür filtresi, tek hisse olay geçmişi, tüm BIST taraması, "veriyi tamamla" (eksik bar tamamlama). Açılışta tarama son taramadan 24 saat geçmişse otomatik çalışır (`StartupJobsController`).

## 4. Testler

`tests/application/services/analysis/technical/`: göstergeler (`test_indicators.py`, `test_indicators_trend.py`), filtreler (`test_screener.py`, `test_screener_trend_filters.py`), tarayıcı servisi, Golden Cross, destek/direnç, teknik analiz servisi. ADX ve Supertrend sentetik yükseliş, düşüş, yatay ve dönüş senaryolarıyla doğrulanır.

## 5. Yeni Gösterge veya Filtre Eklemek

1. Göstergeyi `indicators.py`'ye saf fonksiyon olarak ekle ve birim test yaz.
2. Gerekli değerleri `IndicatorSnapshot` ve `build_snapshot`'a ekle (varsayılan `None`).
3. Koşulu saf bir `is_*` fonksiyonu olarak yaz ve `SCREENER_FILTERS`'a etiketiyle kaydet.
4. Arayüzde ek bir değişiklik gerekmez; açılır liste otomatik güncellenir.
