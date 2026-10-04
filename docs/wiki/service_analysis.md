# Analiz, Risk Metrikleri ve Benchmark Servisleri

> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md) | Karşılaştırma ekranı: [comparison_lab.md](comparison_lab.md)

Kod: `src/application/services/analysis/`. Bu sayfa portföy analizinin servis katmanını (kaynak çözümleme, seri üretimi, getiri ve risk metrikleri, benchmark) anlatır. Teknik göstergeler için [technical_analysis_and_screener.md](technical_analysis_and_screener.md), tek hisse analizi için [stock_360.md](stock_360.md).

## 1. Servis Haritası

| Servis | Görev |
|---|---|
| `AnalysisService` | Ana orkestratör: seçenekler, genel bakış, karşılaştırma, dağılım/risk görünümü. |
| `PortfolioAnalyticsService` | `AnalysisService`'e delege eden facade; ek olarak `get_chart_panels()` ve `get_extended_risk_metrics()` sunar. |
| `AnalysisSourceResolver` | Analiz kaynağını çözer: `dashboard` (ana portföy), `model:<id>` (model portföy); portföy seçenekleri, kaynak işlemleri, ilk işlem tarihi, hisse haritası. |
| `AnalysisBundleBuilder` | Bir filtre için işlemleri, nakit hareketlerini, fiyat serilerini ve portföy serisini tek pakette toplar (aynı veriyi birden çok görünüm için yeniden okumamak için). |
| `PortfolioSeriesBuilder` | Günlük portföy değer serisi ve zaman ağırlıklı getiri (TWR) serisi (aşağıya bakın). |
| `ComparisonPortfolioSeriesBuilder`, `comparison_chart_series` | Karşılaştırma için portföy ve hisse serilerini üretir (`ComparisonSeriesBuilder.build_global_series`). |
| `ComparisonService` | Saf pandas hesapları: seri hizalama, rasyo, drawdown, dönemsel getiri, risk/getiri. |
| `AnalysisBenchmarkService` | Benchmark serileri (aşağıya bakın). |
| `CurrencyConversionService` | Seriyi TL, USD veya reel (TÜFE'den arındırılmış) cinse çevirir. |
| `ReturnCalcService` | Belirli tarihte portföy değeri, iki tarih arası, haftalık ve aylık getiri ([service_portfolio_and_market.md](service_portfolio_and_market.md)). |
| `risk_metrics.py` | Saf risk/getiri metrik fonksiyonları. |

Filtre durumu `AnalysisFilterState`: başlangıç/bitiş tarihi, seçili hisseler, seçili benchmark'lar, `portfolio_source`, `comparison_portfolio_sources`, `currency_mode` (`TL`, `USD`, `REAL`).

## 2. Portföy Serisi ve TWR

`PortfolioSeriesBuilder.compute_portfolio_series` her takvim günü için portföy değerini (nakit + pozisyonların son bilinen fiyatla değeri) ve TWR endeksini (başlangıç 100) üretir:

- Nakit takibi varsa (nakit hareketi bulunan portföy) yalnızca **dış sermaye akışı** (yatırma/çekme) akış sayılır; alım/satım içeride kalır. Nakit takibi yoksa alım tutarı giriş, satış tutarı çıkış akışı sayılır.
- Gün getirisi: `(bugünkü değer - (dünkü değer + akış)) / (dünkü değer + akış)`; endeks bu getirilerle zincirlenir.
- **Temettü** nakde girer ama akış sayılmaz; bu yüzden TWR temettü kadar yükselir. Aynı tutarda yatırma getiri üretmez ([service_corporate_actions.md](service_corporate_actions.md)).
- Eksik fiyatlı günlerde son bilinen fiyat taşınır; hiç fiyatı olmayan açık pozisyon için uyarı üretilir. Model portföyler ve hisse filtreli görünümlerde nakit takibi kapalıdır.

## 3. Risk ve Getiri Metrikleri (`risk_metrics.py`)

Girdi: `Dict[date, Decimal]` seri; çıktı: `Optional[float]`.

| Grup | Metrikler |
|---|---|
| Getiri | `compute_return_pct`, `compute_relative_gap_pct`, günlük getiri vektörü |
| Risk | Yıllık volatilite, maksimum drawdown (`compute_max_drawdown_pct`), VaR (%95/%99, tarihsel), CVaR / Expected Shortfall |
| Risk ayarlı | Sharpe, Sortino, Calmar, Omega |
| Piyasa ilişkisi | Beta, Alpha, R-kare, izleme hatası (tracking error) |
| Dönemsellik | `compute_monthly_returns_matrix` (yıl -> ay -> getiri %) |
| Dağılım | `get_concentration_label`, `compute_position_snapshot` (ilk üç pozisyon ağırlığı, katkı) |

`PortfolioAnalyticsService.get_extended_risk_metrics()` (Sortino, Calmar, Omega, VaR, CVaR, R-kare, izleme hatası, aylık ısı haritası) ve `get_chart_panels()` (drawdown, dönemsel getiri, risk/getiri ham verisi) hazırdır ancak şu an QML arayüzüne bağlı değildir; Karşılaştırma ekranı kendi hesaplarını `ComparisonService` ile yapar. Yapay zekâ danışmanı `get_overview` ve `get_allocation_risk_view` çıktılarını kullanır.

## 4. Karşılaştırma Hesapları (`ComparisonService`)

1. `align_financial_series`: farklı tatil günlü varlıkları ortak tarih indeksinde dış birleştirme ve ileri doldurma (`ffill`) ile hizalar.
2. `calculate_asset_ratio`: `A / B` rasyosu, sıfıra bölme ve `NaN/inf` korumalı.
3. `calculate_drawdowns`: `DD = (fiyat - tarihsel zirve) / tarihsel zirve * 100`.
4. `calculate_risk_return_metrics`: günlük getiri standart sapmasından yıllık volatilite (`σ_daily * sqrt(252) * 100`) ve dönem toplam getirisi.
5. `calculate_periodic_returns`: aylık (`ME`) veya yıllık (`YE`) net getiri yüzdeleri.

## 5. Benchmark Kaynakları

| Kod | Tanım | Kaynak |
|---|---|---|
| `bist100` | BIST 100 | yfinance `XU100.IS` |
| `gold` / `silver` | Gram altın / gümüş (TL) | yfinance `XAUTRY=X` / `XAGTRY=X` |
| `usd` / `euro` | USD/TRY, EUR/TRY | yfinance `TRY=X` / `EURTRY=X` |
| `deposit` | Mevduat faizi | TCMB EVDS `TP.KTF10`; erişilemezse `TCMB_DEPOSIT_RATE_FALLBACK` |
| `cpi` | TÜFE | TCMB EVDS `TP.FG.J0` |

Yedek kazıma kaynakları (countryeconomy, exchange-rates.org, macrotrends) ve ağ davranışı için bkz. [service_market_data_providers.md](service_market_data_providers.md).

## 6. Veri Kapsamı Kuralları

- Analiz kaynağı net açık pozisyonlardan üretilir; tamamen satılmış hisseler otomatik filtre/dağılım listesine girmez, ancak satış nakdi ve kapatılmış işlemler seriye dahil kalır (nakit yeniden oynatımı için tüm ilgili işlemler korunur).
- Ana portföyün toplam değeri: nakit bakiye + açık pozisyon piyasa değeri.
- Silinmiş model portföy seçimi kalırsa kaynak `dashboard`'a normalize edilir.
- Fiyat uyarıları yalnızca analiz aralığında değerleme gerektiren hisseler için üretilir.
- Tarihsel seri `daily_prices` kapanışını kullanır; canlı fiyat tarihsel analize karışmaz.

## 7. Testler

`tests/application/test_analysis_service.py`, `tests/application/services/analysis/test_risk_metrics.py`, `tests/application/services/test_comparison_service.py`, `tests/application/test_return_calc_service.py`, `tests/application/test_dividend_cash_flow.py` (TWR ve temettü).
