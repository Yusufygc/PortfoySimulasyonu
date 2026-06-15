"""
YFinance Değerleme Provider — IMarketValuationProvider implementasyonu.

BIST hisseleri için anlık piyasa değeri, fiyat, hisse adedini çeker.
Dosya cache + kısa TTL ile canlı fiyat tazeliği korunur.

Cache: data/_cache/financials/valuation_{TICKER}.json
TTL: 1 saat
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from src.domain.ports.services.i_market_valuation_provider import MarketValuationUnavailable

logger = logging.getLogger(__name__)

_PROJECT_ROOT   = Path(__file__).parent.parent.parent.parent
_CACHE_DIR      = _PROJECT_ROOT / "data" / "_cache" / "financials"
CACHE_TTL_HOURS = 1
_BIST_SUFFIX    = ".IS"


def _cache_path(ticker: str) -> Path:
    return _CACHE_DIR / f"valuation_{ticker.upper()}.json"


def _is_cache_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    age_h = (time.time() - path.stat().st_mtime) / 3600
    return age_h < CACHE_TTL_HOURS


def _load_cache(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_cache(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _fetch_snapshot(ticker: str) -> dict[str, Any]:
    """yfinance üzerinden anlık piyasa verisi."""
    try:
        import yfinance as yf
    except ImportError:
        return _empty_snap(ticker, "yfinance kurulu değil")

    yf_ticker = f"{ticker}{_BIST_SUFFIX}"
    result: dict[str, Any] = {
        "ticker": ticker, "price": None, "market_cap": None,
        "shares_outstanding": None, "currency": "TRY", "error": None,
    }

    try:
        t    = yf.Ticker(yf_ticker)
        info = t.fast_info
        try:
            result["price"] = float(info.last_price)
        except Exception:
            pass
        try:
            mc = info.market_cap
            if mc:
                result["market_cap"] = float(mc)
        except Exception:
            pass
        try:
            so = info.shares
            if so:
                result["shares_outstanding"] = float(so)
        except Exception:
            pass

        if result["market_cap"] is None:
            p, so = result["price"], result["shares_outstanding"]
            if p is not None and so is not None:
                result["market_cap"] = p * so

        if result["price"] is None and result["market_cap"] is None:
            full = t.info
            result["price"]              = full.get("currentPrice") or full.get("previousClose")
            result["market_cap"]         = full.get("marketCap")
            result["shares_outstanding"] = full.get("sharesOutstanding")

    except Exception as exc:
        result["error"] = str(exc)
        logger.warning("yfinance hata [%s]: %s", yf_ticker, exc)

    return result


def _empty_snap(ticker: str, error: str = "") -> dict[str, Any]:
    return {
        "ticker": ticker, "price": None, "market_cap": None,
        "shares_outstanding": None, "currency": "TRY", "error": error,
    }


class YFinanceValuationProvider:
    """Anlık piyasa değerleme verisi — yfinance + dosya cache (1 saat TTL)."""

    def get_market_snapshot(self, ticker: str) -> dict[str, Any]:
        """
        Anlık fiyat, piyasa değeri, hisse adedi.
        Cache taze ise ağ çağrısı yapılmaz.
        """
        path = _cache_path(ticker)
        if _is_cache_fresh(path):
            cached = _load_cache(path)
            if cached is not None:
                return cached

        snap = _fetch_snapshot(ticker)
        if snap.get("market_cap") is not None:
            _save_cache(path, snap)
        elif snap.get("error"):
            logger.warning("Değerleme snapshot hatası [%s]: %s", ticker, snap["error"])

        return snap
