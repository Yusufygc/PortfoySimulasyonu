"""`_piotroski` karakterizasyon testi: F-Score ve dokuz kriter refaktörden önce/sonra aynı kalmalı
(`golden/piotroski_golden.json`, refaktör öncesi koddan üretildi). Elle yazılmış sınır durumları ve tohumlu rastgele girdiler."""
from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from src.application.services.analysis.financials import metrics

GOLDEN_PATH = Path(__file__).parent / "golden" / "piotroski_golden.json"

KEYS = [
    "net_kar", "isletme_cf", "roa", "uv_borc_varlik", "cari_oran",
    "odenmis_sermaye", "brut_kar_marji", "varlik_devir_ytd",
]
PERIODS = ["2023/12", "2024/3", "2024/12", "2025/3"]


def _const(first: dict, second: dict) -> dict:
    """Her ölçü için `{dönem: değer}`; 2023/12 ve 2024/3 `first`, 2024/12 ve 2025/3 `second` değerini alır."""
    out = {}
    for key in KEYS:
        out[key] = {"2023/12": first.get(key), "2024/3": first.get(key),
                    "2024/12": second.get(key), "2025/3": second.get(key)}
    return out


IMPROVING_BEFORE = {"net_kar": 10, "isletme_cf": 5, "roa": 1.0, "uv_borc_varlik": 0.5, "cari_oran": 1.0,
                    "odenmis_sermaye": 100, "brut_kar_marji": 20, "varlik_devir_ytd": 0.4}
IMPROVING_AFTER = {"net_kar": 20, "isletme_cf": 30, "roa": 2.0, "uv_borc_varlik": 0.3, "cari_oran": 1.5,
                   "odenmis_sermaye": 100, "brut_kar_marji": 25, "varlik_devir_ytd": 0.6}
WORSENING_AFTER = {"net_kar": -5, "isletme_cf": -2, "roa": 0.5, "uv_borc_varlik": 0.7, "cari_oran": 0.8,
                   "odenmis_sermaye": 150, "brut_kar_marji": 10, "varlik_devir_ytd": 0.2}

HAND_CASES = {
    "all_improving": (_const(IMPROVING_BEFORE, IMPROVING_AFTER), PERIODS),
    "all_worsening": (_const(IMPROVING_BEFORE, WORSENING_AFTER), PERIODS),
    "unchanged_values_boundaries": (_const(IMPROVING_BEFORE, IMPROVING_BEFORE), PERIODS),
    "no_previous_year_period": (_const(IMPROVING_BEFORE, IMPROVING_AFTER), ["2024/12", "2025/3"]),
    "missing_metrics": ({}, PERIODS),
    "empty_periods": (_const(IMPROVING_BEFORE, IMPROVING_AFTER), []),
    "cash_flow_equal_to_profit": (_const({"net_kar": 10, "isletme_cf": 10}, {"net_kar": 10, "isletme_cf": 10}), PERIODS),
    "share_count_decrease": (_const({"odenmis_sermaye": 100}, {"odenmis_sermaye": 90}), PERIODS),
}


def _random_case(seed: int):
    rng = random.Random(seed)
    values = [None, -3, 0, 1, 2, 5]
    data = {key: {p: rng.choice(values) for p in PERIODS} for key in KEYS}
    return data, PERIODS


CASES = {**HAND_CASES, **{f"random_{seed:02d}": _random_case(seed) for seed in range(40)}}


@pytest.mark.parametrize("name", sorted(CASES))
def test_piotroski_output_is_unchanged(name):
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    data, periods = CASES[name]

    result = metrics._piotroski(data, periods)

    assert json.loads(json.dumps(result)) == golden[name]
