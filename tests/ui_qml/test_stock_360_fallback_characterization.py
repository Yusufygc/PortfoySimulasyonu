"""`get_fallback_financials` karakterizasyon testi: çevrimdışı örnek veri kümesi refaktörden önce/sonra birebir aynı kalmalı
(`golden/stock_360_fallback_financials_golden.json`, refaktör öncesi koddan üretildi)."""
from __future__ import annotations

import json
from pathlib import Path

from src.ui_qml.controllers.stock_360_fallback import get_fallback_financials

GOLDEN_PATH = Path(__file__).parent / "golden" / "stock_360_fallback_financials_golden.json"


def test_fallback_financials_dataset_is_unchanged():
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert json.loads(json.dumps(get_fallback_financials("BIMAS"))) == golden


def test_fallback_financials_does_not_depend_on_ticker():
    assert get_fallback_financials("BIMAS") == get_fallback_financials("THYAO")


def test_fallback_financials_returns_independent_copies():
    first = get_fallback_financials("BIMAS")
    first["raw_data"]["isletme_cf"]["2025/3"] = 0

    assert get_fallback_financials("BIMAS")["raw_data"]["isletme_cf"]["2025/3"] == 12_000_000_000
