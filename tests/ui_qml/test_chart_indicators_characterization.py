"""`ChartController._calculate_indicators` karakterizasyon testi: seri uzunlukları, Golden/Death Cross işaretçileri ve tüm
çıktının SHA-256 özeti refaktörden önce/sonra aynı kalmalı (`golden/chart_indicators_golden.json`, refaktör öncesi koddan)."""
from __future__ import annotations

import hashlib
import importlib
import json
import math
from datetime import date, timedelta
from pathlib import Path

import pytest

from src.ui_qml.controllers.chart_controller import ChartController

GOLDEN_PATH = Path(__file__).parent / "golden" / "chart_indicators_golden.json"


def _candles(closes: list[float], start: date = date(2024, 1, 1)) -> list[dict]:
    result = []
    for index, close in enumerate(closes):
        open_ = closes[index - 1] if index else close
        result.append({
            "time": (start + timedelta(days=index)).isoformat(),
            "open": round(open_, 2),
            "high": round(max(open_, close) + 0.7, 2),
            "low": round(min(open_, close) - 0.6, 2),
            "close": round(close, 2),
        })
    return result


def _wave(count: int) -> list[float]:
    return [100 + 30 * math.sin(i / 25) + i * 0.05 for i in range(count)]


SERIES = {
    "empty": [],
    "single_bar": [100.0],
    "short_70_bars": [100 + i * 0.4 + (i % 7) * 0.5 for i in range(70)],
    "wave_420_bars_with_crosses": _wave(420),
    "rising_300_bars_no_cross": [100 + i * 0.3 for i in range(300)],
    "falling_then_rising_260_bars": [200 - i * 0.6 if i < 130 else 122 + (i - 130) * 0.9 for i in range(260)],
}


def _raising_detect(*args, **kwargs):
    raise RuntimeError("tespit hatası")


# (seri, detect_crosses yerine konan sahte; None = gerçek)
CASES = {name: (name, None) for name in SERIES}
CASES["wave_420_sma_fallback_only"] = ("wave_420_bars_with_crosses", lambda *a, **k: [])
CASES["wave_420_detect_raises"] = ("wave_420_bars_with_crosses", _raising_detect)


def _patch_detect_crosses(monkeypatch, replacement) -> None:
    """`detect_crosses` adı hangi modülde aranıyorsa orada (refaktör öncesi/sonrası) yamalanır."""
    for module_name in ("src.ui_qml.controllers.chart_indicators", "src.ui_qml.controllers.chart_controller"):
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue
        if hasattr(module, "detect_crosses"):
            monkeypatch.setattr(module, "detect_crosses", replacement)


def run_case(name: str, monkeypatch) -> dict:
    series_name, replacement = CASES[name]
    if replacement is not None:
        _patch_detect_crosses(monkeypatch, replacement)
    result = ChartController(container=None)._calculate_indicators(_candles(SERIES[series_name]))
    return {
        "keys": sorted(result),
        "lengths": {
            key: (len(value) if isinstance(value, list) else {k: len(v) for k, v in sorted(value.items())})
            for key, value in sorted(result.items())
        },
        "markers": result["markers"],
        "last_sma20": result["sma20"][-1:] ,
        "last_rsi": result["rsi"][-1:],
        "sha256": hashlib.sha256(json.dumps(result, sort_keys=True).encode("utf-8")).hexdigest(),
    }


@pytest.mark.parametrize("name", sorted(CASES))
def test_indicator_output_is_unchanged(name, monkeypatch):
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert json.loads(json.dumps(run_case(name, monkeypatch))) == golden[name]
