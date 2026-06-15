"""Değerleme saf-matematik modülü birim testleri."""
from __future__ import annotations

import pytest

from src.application.services.analysis.financials.valuation import compute_valuation


_SNAP = {
    "ticker": "FROTO",
    "price": 1000.0,
    "market_cap": 1_000_000.0,
    "shares_outstanding": 1_000.0,
    "currency": "TRY",
    "error": None,
}

_METRICS = {
    "ticker": "FROTO",
    "currency": "TRY",
    "periods": ["2024/3"],
    "net_kar_ttm":  {"2024/3": 80_000.0},
    "satis_ttm":    {"2024/3": 500_000.0},
    "favok_ttm":    {"2024/3": 100_000.0},
    "net_borc":     {"2024/3": 50_000.0},
    "ozkaynak":     {"2024/3": 300_000.0},
    "temettu_odeme": {"2024/3": -20_000.0},
}


class TestComputeValuation:
    def test_fk_calculation(self):
        result = compute_valuation(_METRICS, _SNAP)
        assert result["fk"] == pytest.approx(1_000_000 / 80_000, rel=1e-4)

    def test_pddd_calculation(self):
        result = compute_valuation(_METRICS, _SNAP)
        assert result["pddd"] == pytest.approx(1_000_000 / 300_000, rel=1e-4)

    def test_ev_favok_calculation(self):
        result = compute_valuation(_METRICS, _SNAP)
        ev = 1_000_000 + 50_000
        assert result["ev_favok"] == pytest.approx(ev / 100_000, rel=1e-4)

    def test_fs_calculation(self):
        result = compute_valuation(_METRICS, _SNAP)
        assert result["fs"] == pytest.approx(1_000_000 / 500_000, rel=1e-4)

    def test_temettu_verimi_calculation(self):
        result = compute_valuation(_METRICS, _SNAP)
        assert result["temettu_verimi"] == pytest.approx(20_000 / 1_000_000 * 100, rel=1e-4)

    def test_no_periods_returns_empty(self):
        result = compute_valuation({"periods": []}, _SNAP)
        assert result["fk"] is None
        assert result["error"] == ""

    def test_missing_market_cap_returns_empty(self):
        snap = {**_SNAP, "market_cap": None}
        result = compute_valuation(_METRICS, snap)
        assert result["fk"] is None
        assert result["error"] is not None

    def test_snap_error_returns_empty(self):
        snap = {**_SNAP, "error": "ağ hatası"}
        result = compute_valuation(_METRICS, snap)
        assert result["fk"] is None
        assert "ağ hatası" in (result["error"] or "")

    def test_zero_denominator_safe_div(self):
        m = {**_METRICS, "net_kar_ttm": {"2024/3": 0.0}}
        result = compute_valuation(m, _SNAP)
        assert result["fk"] is None

    def test_none_metric_returns_none_ratio(self):
        m = {**_METRICS, "net_kar_ttm": {}}
        result = compute_valuation(m, _SNAP)
        assert result["fk"] is None
