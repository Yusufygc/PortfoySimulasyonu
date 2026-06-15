"""IsyatirimProvider cache/TTL birim testleri — ağ çağrısı yapılmaz."""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.infrastructure.market_data.isyatirim_provider import (
    IsyatirimProvider,
    _cache_path,
    _is_cache_fresh,
    _load_cache,
    _save_cache,
    CACHE_TTL_HOURS,
)
from src.domain.ports.services.i_financial_statement_provider import (
    FinancialStatementProviderUnavailable,
)


# ---------------------------------------------------------------------------
# _cache_path
# ---------------------------------------------------------------------------

def test_cache_path_uppercase(tmp_path):
    with patch("src.infrastructure.market_data.isyatirim_provider._CACHE_DIR", tmp_path):
        p = _cache_path("froto", "try")
    assert p.name == "FROTO_TRY.json"
    assert p.parent == tmp_path


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
    f = tmp_path / "x.json"
    f.write_text("{}")
    stale_mtime = time.time() - (CACHE_TTL_HOURS * 3600 + 60)
    import os
    os.utime(f, (stale_mtime, stale_mtime))
    assert not _is_cache_fresh(f)


# ---------------------------------------------------------------------------
# _load_cache / _save_cache round-trip
# ---------------------------------------------------------------------------

def test_save_and_load_cache(tmp_path):
    data = {"ticker": "FROTO", "periods": ["2024/3"]}
    p = tmp_path / "FROTO_TRY.json"
    _save_cache(p, data)
    loaded = _load_cache(p)
    assert loaded == data


def test_load_cache_missing(tmp_path):
    result = _load_cache(tmp_path / "missing.json")
    assert result is None


def test_load_cache_corrupt(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json }{")
    result = _load_cache(p)
    assert result is None


# ---------------------------------------------------------------------------
# IsyatirimProvider.get_financial_data — cache hit
# ---------------------------------------------------------------------------

_MINIMAL_RAW = {
    "ticker": "FROTO",
    "currency": "TRY",
    "periods": ["2024/3"],
    "sections": {"bilanco": {}, "gelir": {}, "dipnot": {}, "nakit_akim": {}},
}


def test_get_financial_data_returns_cache_when_fresh(tmp_path):
    cache_file = tmp_path / "FROTO_TRY.json"
    _save_cache(cache_file, _MINIMAL_RAW)

    with (
        patch("src.infrastructure.market_data.isyatirim_provider._CACHE_DIR", tmp_path),
        patch("src.infrastructure.market_data.isyatirim_provider._scrape") as mock_scrape,
    ):
        provider = IsyatirimProvider()
        result = provider.get_financial_data("FROTO", n_quarters=4, currency="TRY")

    mock_scrape.assert_not_called()
    assert result["ticker"] == "FROTO"


def test_get_financial_data_scrapes_when_cache_stale(tmp_path):
    cache_file = tmp_path / "FROTO_TRY.json"
    _save_cache(cache_file, _MINIMAL_RAW)
    stale_mtime = time.time() - (CACHE_TTL_HOURS * 3600 + 60)
    import os
    os.utime(cache_file, (stale_mtime, stale_mtime))

    fresh_data = dict(_MINIMAL_RAW, periods=["2024/6"])

    with (
        patch("src.infrastructure.market_data.isyatirim_provider._CACHE_DIR", tmp_path),
        patch(
            "src.infrastructure.market_data.isyatirim_provider._scrape",
            return_value=fresh_data,
        ) as mock_scrape,
    ):
        provider = IsyatirimProvider()
        result = provider.get_financial_data("FROTO", n_quarters=4, currency="TRY")

    mock_scrape.assert_called_once()
    assert result["periods"] == ["2024/6"]


def test_get_financial_data_raises_on_scrape_failure(tmp_path):
    with (
        patch("src.infrastructure.market_data.isyatirim_provider._CACHE_DIR", tmp_path),
        patch(
            "src.infrastructure.market_data.isyatirim_provider._scrape",
            side_effect=FinancialStatementProviderUnavailable("ağ hatası"),
        ),
    ):
        provider = IsyatirimProvider()
        with pytest.raises(FinancialStatementProviderUnavailable):
            provider.get_financial_data("XXXX", n_quarters=4, currency="TRY")


def test_get_financial_data_saves_cache_after_scrape(tmp_path):
    fresh_data = dict(_MINIMAL_RAW)

    with (
        patch("src.infrastructure.market_data.isyatirim_provider._CACHE_DIR", tmp_path),
        patch(
            "src.infrastructure.market_data.isyatirim_provider._scrape",
            return_value=fresh_data,
        ),
    ):
        provider = IsyatirimProvider()
        provider.get_financial_data("FROTO", n_quarters=4, currency="TRY")

    cached = _load_cache(tmp_path / "FROTO_TRY.json")
    assert cached is not None
    assert cached["ticker"] == "FROTO"
