"""Değerleme çarpanı hesaplamaları — saf, ağsız."""
from __future__ import annotations

from typing import Any, Optional


def _safe_div(a: float | None, b: float | None) -> Optional[float]:
    if a is None or b is None or b == 0:
        return None
    return a / b


def compute_valuation(m: dict, snap: dict) -> dict[str, Any]:
    """
    Değerleme çarpanları (metrics dict + market snapshot).

    F/K   = Market Cap / Net Kar TTM
    PD/DD = Market Cap / Özkaynak
    EV/FAVÖK = (Market Cap + Net Borç) / FAVÖK TTM
    F/S   = Market Cap / Satış TTM

    Returns dict ile anahtarlar: period, fk, pddd, ev_favok, fs,
    temettu_verimi, market_cap, ev, error.
    """
    periods = m.get("periods", [])
    if not periods:
        return _empty_val()

    p0  = periods[0]
    mc  = snap.get("market_cap")
    err = snap.get("error")

    if mc is None or err:
        return _empty_val(error=err or "piyasa verisi yok")

    def get(key: str) -> Optional[float]:
        return m.get(key, {}).get(p0)

    net_borc = get("net_borc")
    ev       = (mc + net_borc) if net_borc is not None else mc

    temettu  = get("temettu_odeme")
    temettu_verimi: Optional[float] = None
    if temettu is not None and mc and mc != 0:
        temettu_verimi = abs(temettu) / mc * 100

    return {
        "period":         p0,
        "fk":             _safe_div(mc, get("net_kar_ttm")),
        "pddd":           _safe_div(mc, get("ozkaynak")),
        "ev_favok":       _safe_div(ev, get("favok_ttm")),
        "fs":             _safe_div(mc, get("satis_ttm")),
        "temettu_verimi": temettu_verimi,
        "market_cap":     mc,
        "ev":             ev,
        "error":          None,
    }


def _empty_val(error: str = "") -> dict[str, Any]:
    return {
        "period": None, "fk": None, "pddd": None,
        "ev_favok": None, "fs": None, "temettu_verimi": None,
        "market_cap": None, "ev": None, "error": error,
    }
