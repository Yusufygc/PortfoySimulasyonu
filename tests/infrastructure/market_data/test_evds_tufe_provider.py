"""EvdsTufeProvider cache/TTL birim testleri — ağ çağrısı yapılmaz."""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import date

import pytest

from src.infrastructure.market_data.evds_tufe_provider import (
    EvdsTufeProvider,
    _is_cache_fresh,
    _load_cache,
    _save_cache,
    _parse_items,
    CACHE_TTL_HOURS,
)
from src.domain.ports.services.i_inflation_data_provider import InflationDataUnavailable


_CACHE_PATH = "src.infrastructure.market_data.evds_tufe_provider._CACHE_FILE"

_SAMPLE_ITEMS = [
    {"Tarih": "01-01-2024", "TP.FG.J0": "1402,83"},
    {"Tarih": "01-02-2024", "TP.FG.J0": "1468,22"},
    {"Tarih": "01-03-2024", "TP.FG.J0": "1532,0"},
]

_PARSED = {"2024-01": 1402.83, "2024-02": 1468.22, "2024-03": 1532.0}


# ---------------------------------------------------------------------------
# _parse_items
# ---------------------------------------------------------------------------

def test_parse_items_comma_decimal():
    result = _parse_items(_SAMPLE_ITEMS)
    assert result["2024-01"] == pytest.approx(1402.83)
    assert result["2024-02"] == pytest.approx(1468.22)


def test_parse_items_skips_missing():
    result = _parse_items([{"Tarih": "01-01-2024"}])
    assert result == {}


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
    path = tmp_path / "tufe.json"
    _save_cache(path, _PARSED)
    loaded = _load_cache(path)
    assert loaded == _PARSED


def test_load_cache_missing(tmp_path):
    assert _load_cache(tmp_path / "no.json") is None


def test_load_cache_corrupt(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json }{")
    assert _load_cache(p) is None


# ---------------------------------------------------------------------------
# EvdsTufeProvider.get_monthly_tufe
# ---------------------------------------------------------------------------

def test_returns_cached_when_fresh(tmp_path):
    cache_file = tmp_path / "tufe_index.json"
    _save_cache(cache_file, _PARSED)
    client = MagicMock()

    with patch(_CACHE_PATH, cache_file):
        provider = EvdsTufeProvider(evds_client=client)
        result   = provider.get_monthly_tufe(date(2024, 1, 1), date(2024, 3, 31))

    client.get_series.assert_not_called()
    assert result == _PARSED


def test_fetches_when_cache_stale(tmp_path):
    import os
    cache_file = tmp_path / "tufe_index.json"
    _save_cache(cache_file, _PARSED)
    stale = time.time() - (CACHE_TTL_HOURS * 3600 + 60)
    os.utime(cache_file, (stale, stale))

    client = MagicMock()
    client.get_series.return_value = _SAMPLE_ITEMS

    with patch(_CACHE_PATH, cache_file):
        provider = EvdsTufeProvider(evds_client=client)
        result   = provider.get_monthly_tufe(date(2024, 1, 1), date(2024, 3, 31))

    client.get_series.assert_called_once()
    assert "2024-01" in result


def test_raises_when_no_cache_and_api_fails(tmp_path):
    cache_file = tmp_path / "tufe_index.json"
    client = MagicMock()
    client.get_series.side_effect = Exception("ağ yok")

    with patch(_CACHE_PATH, cache_file):
        provider = EvdsTufeProvider(evds_client=client)
        with pytest.raises(InflationDataUnavailable):
            provider.get_monthly_tufe(date(2024, 1, 1), date(2024, 3, 31))


def test_saves_cache_after_fetch(tmp_path):
    cache_file = tmp_path / "tufe_index.json"
    client = MagicMock()
    client.get_series.return_value = _SAMPLE_ITEMS

    with patch(_CACHE_PATH, cache_file):
        provider = EvdsTufeProvider(evds_client=client)
        provider.get_monthly_tufe(date(2024, 1, 1), date(2024, 3, 31))

    saved = _load_cache(cache_file)
    assert saved is not None
    assert "2024-01" in saved
