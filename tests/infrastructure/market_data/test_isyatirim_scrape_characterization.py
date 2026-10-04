"""`_scrape` karakterizasyon testi: sağlayıcı grubu keşfi, çeyrek toplama ve istek sırası refaktörden önce/sonra aynı kalmalı.

Beklenen çıktılar `golden/isyatirim_scrape_golden.json` dosyasındadır (refaktör öncesi koddan üretildi). Ağ yoktur:
`_fetch_batch` sahte, bugünün tarihi 2026-10-04'e sabitlenmiştir.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest

from src.domain.ports.services.i_financial_statement_provider import FinancialStatementProviderUnavailable
from src.infrastructure.market_data import isyatirim_provider as provider

GOLDEN_PATH = Path(__file__).parent / "golden" / "isyatirim_scrape_golden.json"

ITEMS = [
    ("1A", "Dönen Varlıklar"),
    ("2A", "Özkaynaklar"),
    ("3C", "Satış Gelirleri"),
    ("4BA", "Yurtiçi Satışlar"),
    ("4CA", "Amortisman"),
]

# senaryo adı -> (grup başına en son verisi olan çeyrek, istenen çeyrek sayısı)
SCENARIOS = {
    "primary_group_latest_2026_6": ({"XI_29": (2026, 6)}, 6),
    "fallback_group_ufrs": ({"UFRS": (2026, 3)}, 5),
    "only_older_second_probe_batch": ({"XI_29": (2025, 6)}, 8),
    "single_batch": ({"XI_29": (2026, 9)}, 2),
    "no_data_raises": ({}, 4),
}


class _FrozenDate(datetime.date):
    @classmethod
    def today(cls):
        return cls(2026, 10, 4)


def _make_fake_fetch(latest_by_group, calls):
    def fake_fetch(session, ticker, quarters4, currency, group):
        padded = (quarters4 + [quarters4[-1]] * 4)[:4]
        calls.append([group, [list(q) for q in padded]])
        latest = latest_by_group.get(group)
        if latest is None:
            return None
        rows = []
        for code, desc in ITEMS:
            row = {"itemCode": code, "itemDescTr": desc}
            for i, (year, period) in enumerate(padded, start=1):
                row[f"value{i}"] = str(year * 10 + period) if (year, period) <= latest else ""
            rows.append(row)
        return rows

    return fake_fetch


def run_scenario(monkeypatch, name):
    latest_by_group, n_quarters = SCENARIOS[name]
    calls: list = []
    monkeypatch.setattr(provider, "_fetch_batch", _make_fake_fetch(latest_by_group, calls))
    monkeypatch.setattr(provider.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(datetime, "date", _FrozenDate)
    try:
        outcome = ["ok", provider._scrape("TEST", n_quarters, "TRY")]
    except FinancialStatementProviderUnavailable as exc:
        outcome = ["unavailable", str(exc)]
    return {"outcome": json.loads(json.dumps(outcome)), "calls": calls}


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_scrape_output_and_request_sequence_are_unchanged(monkeypatch, name):
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert run_scenario(monkeypatch, name) == golden[name]
