"""Grafik için mum ve hacim kaynakları (saf fonksiyonlar).

`ChartController` bu modüldeki yükleyicileri sırayla dener: DuckDB piyasa geçmişi (tüm BIST, sermaye artırımı
düzeltmeli), SQLite portföy fiyatları (DuckDB'de olmayan hisseler) ve yalnızca konteynersiz (çevrimdışı) modda
demo veri. Her yükleyici `(mumlar, hacimler, şirket adı)` üçlüsü döner; veri yoksa `None` ya da boş liste.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

Candles = list[dict[str, Any]]
Loaded = tuple[Candles, Candles, str]

_HISTORY_YEARS = 3
_UP_VOLUME_COLOR = "rgba(8, 153, 129, 0.4)"
_DOWN_VOLUME_COLOR = "rgba(242, 54, 69, 0.4)"
_DEFAULT_SQLITE_VOLUME = 250000


def _candle(date_text: str, open_: float, high: float, low: float, close: float) -> dict[str, Any]:
    return {"time": date_text, "open": round(open_, 2), "high": round(high, 2),
            "low": round(low, 2), "close": round(close, 2)}


def _volume(date_text: str, value: float, open_: float, close: float) -> dict[str, Any]:
    return {"time": date_text, "value": value,
            "color": _UP_VOLUME_COLOR if close >= open_ else _DOWN_VOLUME_COLOR}


def load_market_history_candles(lookup, ticker: str) -> Loaded | None:
    """DuckDB piyasa geçmişinden günlük mumlar; veri yoksa veya okuma hatasında `None`."""
    try:
        end_date = datetime.now().date()
        bars = lookup.get_market_bars(ticker, end_date - timedelta(days=365 * _HISTORY_YEARS), end_date)
        if not bars:
            return None
        company_name = lookup.get_market_company_name(ticker) or ticker
        candles: Candles = []
        volumes: Candles = []
        prev_close = None
        for bar in bars:
            close = bar.close_price
            open_ = bar.open_price if bar.open_price else (prev_close if prev_close is not None else close)
            high = bar.high_price if bar.high_price else max(open_, close)
            low = bar.low_price if bar.low_price else min(open_, close)
            prev_close = close
            date_text = bar.price_date.strftime("%Y-%m-%d")
            candles.append(_candle(date_text, open_, high, low, close))
            volumes.append(_volume(date_text, float(bar.volume or 0), open_, close))
        logger.info("DuckDB'den %s icin %d adet 1D mum verisi yuklendi.", ticker, len(candles))
        return candles, volumes, company_name
    except Exception as exc:
        logger.warning("DuckDB fiyat verisi okunamadi (%s): %s", ticker, exc)
        return None


def _synthetic_ohlc(close: float, prev_close: float | None) -> tuple[float, float, float]:
    """Açılış/yüksek/düşük kaydı olmayan günler için kapanıştan türetilen yaklaşık değerler."""
    open_ = prev_close if prev_close is not None else close
    spread = max(abs(close - open_), close * 0.008)
    return open_, max(open_, close) + spread * 0.35, max(0.01, min(open_, close) - spread * 0.35)


def _price_ohlc(price, prev_close: float | None) -> tuple[float, float, float, float]:
    """`(açılış, yüksek, düşük, kapanış)`; OHLC kaydı eksikse kapanıştan türetilir."""
    close = float(price.close_price)
    if price.open_price is not None and price.high_price is not None and price.low_price is not None:
        return float(price.open_price), float(price.high_price), float(price.low_price), close
    return (*_synthetic_ohlc(close, prev_close), close)


def _price_volume(price) -> float:
    has_volume = price.volume is not None and price.volume > 0
    return float(price.volume if has_volume else _DEFAULT_SQLITE_VOLUME)


def load_price_series_candles(lookup, ticker: str) -> Loaded:
    """SQLite fiyat serisinden günlük mumlar. Hisse bulunamazsa boş; bulunup fiyat yoksa yalnızca şirket adı döner."""
    company_name = ticker
    candles: Candles = []
    volumes: Candles = []
    try:
        stock = lookup.find_stock(ticker) if lookup else None
        if not stock:
            return candles, volumes, company_name
        company_name = (getattr(stock, "name", None) or stock.ticker).replace(".IS", "").strip()
        end_date = datetime.now().date()
        prices = lookup.get_price_series(stock.id, end_date - timedelta(days=365 * _HISTORY_YEARS), end_date)
        prev_close = None
        for price in sorted(prices or [], key=lambda p: p.price_date):
            open_, high, low, close = _price_ohlc(price, prev_close)
            prev_close = close
            date_text = price.price_date.strftime("%Y-%m-%d")
            candles.append(_candle(date_text, open_, high, low, close))
            volumes.append(_volume(date_text, _price_volume(price), open_, close))
        if candles:
            logger.info("SQLite'tan %s icin %d adet 1D mum verisi yuklendi.", ticker, len(candles))
    except Exception as exc:
        logger.warning("Fiyat verisi cekilirken hata: %s", exc)
    return candles, volumes, company_name


def demo_candles(ticker: str) -> Loaded:
    """Çevrimdışı (konteynersiz) mod için rastgele yürüyüşlü ~1 yıllık demo mumlar."""
    base_price = 285.0 if "THY" in ticker else (110.0 if "GARAN" in ticker else 150.0)
    today = datetime.now().date()
    np.random.seed(abs(hash(ticker)) % (2**32))
    candles: Candles = []
    volumes: Candles = []
    current_price = base_price
    for offset in range(260, -1, -1):
        day = today - timedelta(days=offset)
        if day.weekday() >= 5:
            continue
        open_ = current_price
        close = open_ * (1 + np.random.normal(0.001, 0.02))
        high = max(open_, close) * (1 + abs(np.random.normal(0, 0.008)))
        low = min(open_, close) * (1 - abs(np.random.normal(0, 0.008)))
        date_text = day.strftime("%Y-%m-%d")
        candles.append(_candle(date_text, open_, high, low, close))
        volumes.append(_volume(date_text, int(np.random.uniform(500000, 3500000)), open_, close))
        current_price = close
    return candles, volumes, ticker


def last_price_summary(candles: Candles) -> tuple[str, bool, str] | None:
    """Son mumdan `(fiyat metni, artışta mı, yüzde değişim metni)`; mum yoksa `None`."""
    if not candles:
        return None
    last = candles[-1]
    last_close = last["close"]
    prev_close = candles[-2]["close"] if len(candles) > 1 else last["open"]
    diff = last_close - prev_close
    diff_pct = (diff / prev_close) * 100 if prev_close > 0 else 0.0
    sign = "+" if diff >= 0 else ""
    return f"₺{last_close:,.2f}", diff >= 0, f"{sign}{diff_pct:.2f}%"
