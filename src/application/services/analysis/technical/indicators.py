"""
Teknik analiz indikatörleri — saf, vektörize NumPy/Pandas fonksiyonları.

Harici kütüphane (`pandas-ta`, `ta`) kullanılmaz (bkz. TRANSFORMATION_PLAN.md §9.2) —
bakım riski ve NumPy/Pandas sürüm kırılganlığı nedeniyle özel implementasyon seçildi.

Her fonksiyon:
- Girdi: `pd.Series` (Index=tarih, sıralı asc, value=sayısal), IO yok, durumsuz.
- Çıktı: aynı index'e hizalı `pd.Series` (veya birden fazla seri).
- Isınma (warmup) dönemindeki barlar NaN döner (veri yetersiz), çağıran taraf filtreler.

Not: Buradaki EMA, pandas'ın standart `ewm(adjust=False)` formülünü kullanır
(ilk değer seed). `golden_cross.py`'deki `_ema_tv`, TradingView ile tam hizalama
için ayrı bir seed stratejisi (ilk `span` barın SMA'sı) kullanır — cross-detection
dışı genel amaçlı indikatörler için burada standart EMA yeterlidir.
"""
from __future__ import annotations

import pandas as pd


def sma(closes: pd.Series, period: int) -> pd.Series:
    """Basit hareketli ortalama (Simple Moving Average)."""
    return closes.rolling(window=period, min_periods=period).mean()


def ema(closes: pd.Series, period: int) -> pd.Series:
    """Üstel hareketli ortalama (Exponential Moving Average, standart ewm)."""
    return closes.ewm(span=period, adjust=False, min_periods=period).mean()


def rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index — Wilder'ın smoothing yöntemi (ewm alpha=1/period).

    avg_loss == 0 olan barlarda (tüm hareket kazanç) RSI 100 döner.
    """
    delta = closes.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss
    result = 100.0 - (100.0 / (1.0 + rs))
    return result.where(avg_loss != 0, 100.0)


def macd(
    closes: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD hattı, sinyal hattı ve histogramı döner: (macd_line, signal_line, histogram)."""
    ema_fast = ema(closes, fast_period)
    ema_slow = ema(closes, slow_period)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def bollinger_bands(
    closes: pd.Series,
    period: int = 20,
    num_std: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Bantları: (upper_band, middle_band, lower_band). middle_band = SMA(period)."""
    middle = sma(closes, period)
    std = closes.rolling(window=period, min_periods=period).std(ddof=0)
    upper = middle + num_std * std
    lower = middle - num_std * std
    return upper, middle, lower


def atr(highs: pd.Series, lows: pd.Series, closes: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range — Wilder'ın smoothing yöntemi (ewm alpha=1/period, adjust=False)."""
    prev_close = closes.shift(1)
    true_range = pd.concat(
        [
            highs - lows,
            (highs - prev_close).abs(),
            (lows - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def stochastic_oscillator(
    highs: pd.Series,
    lows: pd.Series,
    closes: pd.Series,
    k_period: int = 14,
    d_period: int = 3,
) -> tuple[pd.Series, pd.Series]:
    """Stochastic Osilatör: (%K, %D). %D, %K'nın d_period'lık basit ortalamasıdır.

    highest_high == lowest_low olan barlarda (dönem boyunca fiyat sabit) %K nötr 50 döner.
    """
    lowest_low = lows.rolling(window=k_period, min_periods=k_period).min()
    highest_high = highs.rolling(window=k_period, min_periods=k_period).max()
    price_range = highest_high - lowest_low

    percent_k = ((closes - lowest_low) / price_range) * 100.0
    percent_k = percent_k.where(price_range != 0, 50.0)
    percent_d = percent_k.rolling(window=d_period, min_periods=d_period).mean()
    return percent_k, percent_d


def cci(highs: pd.Series, lows: pd.Series, closes: pd.Series, period: int = 20) -> pd.Series:
    """Commodity Channel Index. Dönem boyunca fiyat sabitse (ortalama sapma=0) CCI 0 döner."""
    typical_price = (highs + lows + closes) / 3.0
    sma_tp = typical_price.rolling(window=period, min_periods=period).mean()
    mean_abs_dev = typical_price.rolling(window=period, min_periods=period).apply(
        lambda window: (window - window.mean()).abs().mean(), raw=False
    )
    result = (typical_price - sma_tp) / (0.015 * mean_abs_dev)
    return result.where(mean_abs_dev != 0, 0.0)


def vwap(
    highs: pd.Series,
    lows: pd.Series,
    closes: pd.Series,
    volumes: pd.Series,
    period: int = 20,
) -> pd.Series:
    """Hacim Ağırlıklı Ortalama Fiyat — N günlük kayan pencere (rolling VWAP).

    Not: Bu proje günlük (EOD) bar kullanır; klasik "seans VWAP'ı" gün-içi tick
    verisi gerektirir ve burada uygulanamaz. Bunun yerine yaygın kullanılan
    `period` günlük kayan pencereli VWAP formülü uygulanır (typical_price * volume
    toplamı / volume toplamı).
    """
    typical_price = (highs + lows + closes) / 3.0
    price_volume = typical_price * volumes
    rolling_pv = price_volume.rolling(window=period, min_periods=period).sum()
    rolling_volume = volumes.rolling(window=period, min_periods=period).sum()
    result = rolling_pv / rolling_volume
    return result.where(rolling_volume != 0, float("nan"))


def obv(closes: pd.Series, volumes: pd.Series) -> pd.Series:
    """On-Balance Volume — serinin başından itibaren kümülatif, dönemsiz."""
    direction = closes.diff().apply(lambda delta: 1.0 if delta > 0 else (-1.0 if delta < 0 else 0.0))
    if len(direction) > 0:
        direction.iloc[0] = 0.0
    return (direction * volumes).cumsum()
