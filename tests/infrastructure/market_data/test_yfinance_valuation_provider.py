"""YFinanceValuationProvider cache/TTL birim testleri — yfinance mock ile."""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.infrastructure.market_data.yfinance_valuation_provider import (
    YFinanceValuationProvider,
    _cache_path,
    _is_cache_fresh,
    _load_cache,
    _save_cache,
    CACHE_TTL_HOURS,
)

_CACHE_DIR_PATCH = "src.infrastructure.market_data.yfinance_valuation_provider._CACHE_DIR"

_SNAP = {
    "ticker": "FROTO",
    "price": 1000.0,
    "market_cap": 1_000_000.0,
    "shares_outstanding": 1000.0,
    "currency": "TRY",
    "error": None,
}


# ---------------------------------------------------------------------------
# _cache_path
# ---------------------------------------------------------------------------

def test_cache_path_uppercase(tmp_path):
    with patch(_CACHE_DIR_PATCH, tmp_path):
        p = _cache_path("froto")
    assert p.name == "valuation_FROTO.json"


# ---------------------------------------------------------------------------
# _is_cache_fresh
# ---------------------------------------------------------------------------

def test_is_cache_fresh_missing(tmp_path):
    assert not _is_cache_fresh(tmp_path / "nonexistent.json")


def test_is_cache_fresh_recent(tmp_path):
    f = tmp_path / "x.json"
    f.write_text("{}")
    assert _is_cache_fresh(f)


def test_is_cache_fresh_old(tmp_path):
    import os
    f = tmp_path / "x.json"
    f.write_text("{}")
    stale = time.time() - (CACHE_TTL_HOURS * 3600 + 60)
    os.utime(f, (stale, stale))
    assert not _is_cache_fresh(f)


# ---------------------------------------------------------------------------
# _load_cache / _save_cache
# ---------------------------------------------------------------------------

def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / "v.json"
    _save_cache(path, _SNAP)
    loaded = _load_cache(path)
    assert loaded == _SNAP


def test_load_cache_missing(tmp_path):
    assert _load_cache(tmp_path / "no.json") is None


def test_load_cache_corrupt(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json }{")
    assert _load_cache(p) is None


# ---------------------------------------------------------------------------
# YFinanceValuationProvider.get_market_snapshot
# ---------------------------------------------------------------------------

def test_returns_cached_when_fresh(tmp_path):
    cache_file = tmp_path / "valuation_FROTO.json"
    _save_cache(cache_file, _SNAP)

    with patch(_CACHE_DIR_PATCH, tmp_path):
        provider = YFinanceValuationProvider()
        with patch(
            "src.infrastructure.market_data.yfinance_valuation_provider._fetch_snapshot",
        ) as mock_fetch:
            result = provider.get_market_snapshot("FROTO")

    mock_fetch.assert_not_called()
    assert result["ticker"] == "FROTO"


def test_fetches_when_cache_stale(tmp_path):
    import os
    cache_file = tmp_path / "valuation_FROTO.json"
    _save_cache(cache_file, _SNAP)
    stale = time.time() - (CACHE_TTL_HOURS * 3600 + 60)
    os.utime(cache_file, (stale, stale))

    fresh = {**_SNAP, "price": 1200.0}
    with patch(_CACHE_DIR_PATCH, tmp_path):
        with patch(
            "src.infrastructure.market_data.yfinance_valuation_provider._fetch_snapshot",
            return_value=fresh,
        ):
            provider = YFinanceValuationProvider()
            result   = provider.get_market_snapshot("FROTO")

    assert result["price"] == 1200.0


def test_saves_cache_after_fetch(tmp_path):
    with patch(_CACHE_DIR_PATCH, tmp_path):
        with patch(
            "src.infrastructure.market_data.yfinance_valuation_provider._fetch_snapshot",
            return_value=_SNAP,
        ):
            provider = YFinanceValuationProvider()
            provider.get_market_snapshot("FROTO")

    saved = _load_cache(tmp_path / "valuation_FROTO.json")
    assert saved is not None
    assert saved["market_cap"] == 1_000_000.0


def test_returns_snap_without_caching_on_error(tmp_path):
    error_snap = {**_SNAP, "market_cap": None, "error": "yfinance down"}

    with patch(_CACHE_DIR_PATCH, tmp_path):
        with patch(
            "src.infrastructure.market_data.yfinance_valuation_provider._fetch_snapshot",
            return_value=error_snap,
        ):
            provider = YFinanceValuationProvider()
            result   = provider.get_market_snapshot("FROTO")

    assert result["error"] == "yfinance down"
    assert not (tmp_path / "valuation_FROTO.json").exists()
