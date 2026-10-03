# Analiz ve Benchmark Servisleri

> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md)

Bu belge, `src/application/services/analysis` dizinindeki özellikleri detaylandırır.

## 1. Analiz Servisi (`AnalysisService`)

Bu servis, tek bir varlığın veya tüm portföyün risk, getiri ve benchmark'a göre performansını analiz eden genel merkezdir.
Bileşenleri:
- `ComparisonService`: Çoklu varlıkların ve rasyoların karşılaştırılmasını üstlenir. 
- `ReturnCalcService`: Zaman serisi bazında mutlak ve oransal getiri hesaplamalarını yapar.
- `RiskMetrics`: Sharpe rasyosu, volatilite, maksimum düşüş (Max Drawdown) gibi gelişmiş finansal metrikleri hesaplar.

## 2. Benchmark Mantığı ve Fallback

Kullanıcının portföy performansının iyi olup olmadığını anlaması için bir kıyaslama (benchmark) gerekir.
Desteklenen benchmark türleri:
- **Döviz / Altın:** Piyasa verisi (YFinance vb.) kullanılarak `BenchmarkService` üzerinden hesaplanır.
- **Mevduat (Risk-Free Rate):** Sabit getiri hesaplaması gerektirir. 

### Fallback Kaynaklar (TCMB)
Analiz motoru, internet kesintisi veya YFinance verisinin geç gelmesi durumunda bir fallback mekanizmasına sahiptir. Mevduat ve faiz verisi için çevresel değişkenlerden (örneğin `.env` dosyasındaki `TCMB_DEPOSIT_RATE_FALLBACK=45.0`) veri çekilir ve kullanılır.

## 3. Comparison Lab (Karşılaştırma Laboratuvarı)

Gelişmiş bir veri motoru olarak çalışan `ComparisonService`, UI katmanındaki Plotly grafikleriyle doğrudan haberleşir. Detaylı teknik özellikleri için `docs/wiki/comparison_lab.md` ve `analizSayfasi` belgelerine başvurulabilir.

```mermaid
graph LR
    A[Portföy Zaman Serisi] --> C[RiskMetrics]
    B[Benchmark Zaman Serisi] --> C
    C --> D[Sharpe Rasyosu]
    C --> E[Max Drawdown]
    C --> F[Volatilite]
```
## Faz 2 Notu (2026-06-02)

- `AnalysisBenchmarkService` EVDS concrete client yerine `EvdsSeriesProvider` protocol'üne bağlıdır; production `EvdsClient` container üzerinden structural provider olarak verilir.
- `AnalysisService` artık domain `Position` nesnelerine `_analysis_current_value` runtime attribute'u eklemez; current value bilgisi bundle içindeki `position_values_end` snapshot map'iyle taşınır.
- Currency conversion ve benchmark fallback davranışı mevcut public DTO sözleşmesi korunarak test edilmiştir.

## Faz 2D Notu (2026-06-02)

- `AnalysisService` orchestration servisi olarak kalır; bundle kurma `AnalysisBundleBuilder`, TL/USD/REAL dönüşümü `CurrencyConversionService`, karşılaştırma portföy serileri `ComparisonPortfolioSeriesBuilder` tarafından yapılır.
- Benchmark EVDS parsing yardımcı metodlara ayrıldı; veri akışı hatalarında broad exception noktaları log + empty series fallback contract olarak korunur.
- Public DTO shape ve UI-facing payload anahtarları değişmedi.

## Aktif Kapsam ve Nakit Dahil Toplam Deger Notu (2026-06-03)

- Analiz kaynak secimi ve hisse filtreleri event-sourced net acik pozisyon kapsamindan uretilir; tamamen satilmis hisseler otomatik filtre/holdings listesine girmez.
- Tarihsel portfoy serisi kapatilmis islemleri silmez; cash replay icin tum ilgili trade'ler korunur, fiyat uyarilari ise yalniz analiz araliginda degerleme gereken hisseler icin uretilir.
- Ana portfoy `Toplam Portfoy Degeri` nakit bakiye + acik pozisyon piyasa degeri olarak hesaplanir.
- Silinmis model portfoy secimi stale kalirsa analiz kaynagi dashboard'a normalize edilir ve karsilastirma serisi olarak tekrar eklenmez.

## Teknik Göstergeler ve Hisse Tarayıcı (2026-10-03)

- **Göstergeler** (`src/application/services/analysis/technical/indicators.py`, saf NumPy/Pandas): SMA, EMA, RSI, MACD, Bollinger, ATR, Stochastic, CCI, VWAP, OBV, **ADX** (Wilder, `adx` -> ADX, +DI, -DI) ve **Supertrend** (`supertrend` -> çizgi, yön +1/-1; ATR 10, çarpan 3).
- **Tarayıcı** (`screener.py`, `ScreenerService`): `IndicatorSnapshot` son bar değerlerini taşır; `SCREENER_FILTERS` 10 hazır filtre içerir. Yeni filtreler: `adx_strong_uptrend` (ADX > 25 ve +DI > -DI) ve `supertrend_buy_signal` (yön son barda -1'den +1'e döndü).
- ADX ve Supertrend High/Low serisi ister; yalnızca kapanışı olan hisselerde snapshot alanları `None` kalır ve bu filtreler eşleşmez. DuckDB'den gelen tüm BIST taraması OHLC içerir (gerçek veride 624 hisse ~3,6 sn).
- Kapsam dışı: Ichimoku ve Keltner kanalları (plan §9.13).
