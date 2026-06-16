"""
valuation_provider.py — Piyasa Değerleme Veri Sağlayıcı (yfinance)

BIST hisseleri için anlık fiyat, piyasa değeri ve tarihsel kapanış verisini
yfinance üzerinden çeker.

ENTEGRASYON NOTU:
  Bu modül, asıl sisteme entegrasyon için tasarlanmıştır:
  - src/infrastructure/market_data/yfinance_client.py → YFinanceMarketDataClient
  - Asıl sistemde DI ile enjekte edilecek; bu modül yalnız lab standalone içindir.
  BIST suffix: .IS (ör: FROTO → FROTO.IS)

Kullanım:
    from valuation_provider import get_market_snapshot, compute_valuation
    snap = get_market_snapshot("FROTO")
    # snap == {"ticker": "FROTO", "price": 1234.0, "market_cap": 1.23e12,
    #          "shares_outstanding": 1e9, "currency": "TRY", "error": None}

    m = compute_metrics(raw)
    val = compute_valuation(m, snap)
    # val == {"fk": 12.5, "pddd": 3.2, "ev_favok": 7.8, "fs": 1.1}
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Optional

logger = logging.getLogger(__name__)

_BIST_SUFFIX = ".IS"


def get_market_snapshot(ticker: str) -> dict[str, Any]:
    """
    Anlık piyasa verisi: fiyat, piyasa değeri, hisse adedi.

    Args:
        ticker: BIST kodu (ör: "FROTO"). ".IS" suffix otomatik eklenir.

    Returns:
        {
          "ticker":             str,
          "price":              float | None,
          "market_cap":         float | None,   # TRY cinsinden
          "shares_outstanding": float | None,
          "currency":           str,
          "error":              str | None,      # hata mesajı varsa
        }
    """
    try:
        import yfinance as yf
    except ImportError:
        return _empty_snap(ticker, "yfinance kurulu değil")

    yf_ticker = f"{ticker}{_BIST_SUFFIX}"
    result: dict[str, Any] = {
        "ticker":             ticker,
        "price":              None,
        "market_cap":         None,
        "shares_outstanding": None,
        "currency":           "TRY",
        "error":              None,
    }

    try:
        t = yf.Ticker(yf_ticker)
        info = t.fast_info  # daha hızlı, önbelleğe alınmış

        # Fiyat
        try:
            result["price"] = float(info.last_price)
        except Exception:
            pass

        # Piyasa değeri
        try:
            mc = info.market_cap
            if mc:
                result["market_cap"] = float(mc)
        except Exception:
            pass

        # Hisse adedi
        try:
            so = info.shares
            if so:
                result["shares_outstanding"] = float(so)
        except Exception:
            pass

        # market_cap yoksa price × shares ile tahmin et
        if result["market_cap"] is None:
            p  = result["price"]
            so = result["shares_outstanding"]
            if p is not None and so is not None:
                result["market_cap"] = p * so

        if result["price"] is None and result["market_cap"] is None:
            # Fallback: full info
            full = t.info
            result["price"]              = full.get("currentPrice") or full.get("previousClose")
            result["market_cap"]         = full.get("marketCap")
            result["shares_outstanding"] = full.get("sharesOutstanding")

    except Exception as e:
        result["error"] = str(e)
        logger.warning("yfinance hata [%s]: %s", yf_ticker, e)

    return result


def get_price_history(
    ticker: str,
    start: date,
    end: date,
) -> dict[str, float]:
    """
    Tarihsel günlük kapanış fiyatları.

    Returns:
        {"YYYY-MM-DD": price, ...} — boş dict hata durumunda
    """
    try:
        import yfinance as yf
    except ImportError:
        return {}

    yf_ticker = f"{ticker}{_BIST_SUFFIX}"
    try:
        df = yf.download(
            yf_ticker, start=start, end=end,
            interval="1d", progress=False, auto_adjust=True,
        )
        if df.empty:
            return {}
        close = df["Close"]
        return {str(dt.date()): float(v) for dt, v in close.items()}
    except Exception as e:
        logger.warning("Tarihsel fiyat hatası [%s]: %s", yf_ticker, e)
        return {}


def compute_valuation(m: dict, snap: dict) -> dict[str, Any]:
    """
    Değerleme çarpanlarını hesaplar (metrics dict + market snapshot).

    F/K   = Market Cap / Net Kar TTM
    PD/DD = Market Cap / Özkaynak
    EV/FAVÖK = (Market Cap + Net Borç) / FAVÖK TTM
    F/S   = Market Cap / Satış TTM

    Args:
        m:    compute_metrics() çıktısı
        snap: get_market_snapshot() çıktısı

    Returns:
        {
          "period": str,           # hesaplamada kullanılan son dönem
          "fk":     float | None,
          "pddd":   float | None,
          "ev_favok": float | None,
          "fs":     float | None,
          "temettu_verimi": float | None,  # snap.price ve son temettü ile
          "market_cap":    float | None,
          "ev":            float | None,
        }
    """
    periods = m.get("periods", [])
    if not periods:
        return _empty_val()

    p0  = periods[0]  # en güncel dönem
    mc  = snap.get("market_cap")
    err = snap.get("error")

    if mc is None or err:
        return _empty_val(error=err or "piyasa verisi yok")

    def get(key: str) -> float | None:
        return m.get(key, {}).get(p0)

    nk_ttm    = get("net_kar_ttm")
    sttm      = get("satis_ttm")
    fvk_ttm   = get("favok_ttm")
    net_borc  = get("net_borc")
    ozkaynak  = get("ozkaynak")
    temettu   = get("temettu_odeme")
    price     = snap.get("price")

    def safe_div(a, b):
        if a is None or b is None or b == 0:
            return None
        return a / b

    ev = (mc + net_borc) if (net_borc is not None) else mc

    fk        = safe_div(mc, nk_ttm)
    pddd      = safe_div(mc, ozkaynak)
    ev_favok  = safe_div(ev, fvk_ttm)
    fs        = safe_div(mc, sttm)

    # Temettü verimi (son nakit_akim'daki temettu / market_cap)
    temettu_verimi: Optional[float] = None
    if temettu is not None and mc is not None and mc != 0:
        temettu_verimi = abs(temettu) / mc * 100

    return {
        "period":          p0,
        "fk":              fk,
        "pddd":            pddd,
        "ev_favok":        ev_favok,
        "fs":              fs,
        "temettu_verimi":  temettu_verimi,
        "market_cap":      mc,
        "ev":              ev,
        "error":           None,
    }


def _empty_snap(ticker: str, error: str = "") -> dict[str, Any]:
    return {
        "ticker":             ticker,
        "price":              None,
        "market_cap":         None,
        "shares_outstanding": None,
        "currency":           "TRY",
        "error":              error,
    }


def _empty_val(error: str = "") -> dict[str, Any]:
    return {
        "period":         None,
        "fk":             None,
        "pddd":           None,
        "ev_favok":       None,
        "fs":             None,
        "temettu_verimi": None,
        "market_cap":     None,
        "ev":             None,
        "error":          error,
    }
