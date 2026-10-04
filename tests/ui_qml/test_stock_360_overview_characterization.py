"""`Stock360Controller._load_local_overview_and_technical` karakterizasyon testi: şirket adı/sektör çözümü, genel bakış ve teknik
seviye alanları refaktörden önce/sonra aynı kalmalı (`golden/stock_360_overview_golden.json`, refaktör öncesi koddan)."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.ui_qml.controllers.stock_360_controller import Stock360Controller

GOLDEN_PATH = Path(__file__).parent / "golden" / "stock_360_overview_golden.json"

OVERVIEW = SimpleNamespace(
    last_price=312.456, last_price_date=date(2026, 10, 2), daily_change_pct=2.345,
    volume=12_345_678, week52_low=210.5, week52_high=330.0,
)
TECH_BULL_OVERBOUGHT = SimpleNamespace(
    rsi14=72.46, macd_line=1.2345, macd_signal=0.8, sma50=300.0, sma200=280.0, ema20=305.5,
    support=290.0, resistance=330.0,
)
TECH_BEAR_OVERSOLD = SimpleNamespace(
    rsi14=28.0, macd_line=-0.5, macd_signal=-0.2, sma50=250.0, sma200=270.0, ema20=255.0,
    support=240.0, resistance=275.0,
)
TECH_SPARSE = SimpleNamespace(
    rsi14=None, macd_line=None, macd_signal=None, sma50=None, sma200=None, ema20=None,
    support=None, resistance=None,
)
TECH_NO_SMA200 = SimpleNamespace(
    rsi14=50.0, macd_line=0.1, macd_signal=0.1, sma50=100.0, sma200=None, ema20=99.0,
    support=90.0, resistance=110.0,
)


class _Service:
    """Hisse 360 servisinin sahte uygulaması; `plain_ticker_only` ise `.IS` sürümünde veri döner."""

    def __init__(self, stock=None, catalog_name=None, overview=None, technical=None, suffix_only=False):
        self._stock, self._catalog, self._ov, self._tech, self._suffix_only = stock, catalog_name, overview, technical, suffix_only

    def _pick(self, ticker, value):
        return value if (ticker.endswith(".IS") or not self._suffix_only) else None

    def get_stock_by_ticker(self, ticker):
        return self._pick(ticker, self._stock)

    def get_company_name(self, ticker):
        return self._catalog

    def get_overview(self, ticker):
        return self._pick(ticker, self._ov)

    def get_technical_levels(self, ticker):
        return self._pick(ticker, self._tech)


def _with_service(**kwargs):
    return SimpleNamespace(services=SimpleNamespace(stock_360_service=_Service(**kwargs)), stock_lookup_service=None)


STOCK_WITH_SECTOR = SimpleNamespace(name="Test Holding A.Ş.", sector="Bankacılık")
STOCK_NO_SECTOR = SimpleNamespace(name=None, sector=None)
FLAT_OVERVIEW = SimpleNamespace(
    last_price=50.0, last_price_date=date(2026, 9, 30), daily_change_pct=None,
    volume=999, week52_low=50.0, week52_high=50.0,
)
FALLING_OVERVIEW = SimpleNamespace(
    last_price=90.0, last_price_date=date(2026, 9, 30), daily_change_pct=-1.5,
    volume=2_500_000_000, week52_low=80.0, week52_high=120.0,
)

# senaryo -> (container üretici, ticker)
SCENARIOS = {
    "stock_with_sector_bull_overbought": (
        lambda: _with_service(stock=STOCK_WITH_SECTOR, overview=OVERVIEW, technical=TECH_BULL_OVERBOUGHT), "THYAO"),
    "stock_without_sector_bear_oversold": (
        lambda: _with_service(stock=STOCK_NO_SECTOR, overview=FALLING_OVERVIEW, technical=TECH_BEAR_OVERSOLD), "BIMAS"),
    "catalog_name_defaults_when_no_data": (
        lambda: _with_service(catalog_name="Katalog Şirketi", overview=None, technical=None), "ASELS"),
    "sparse_technical_values": (
        lambda: _with_service(stock=STOCK_WITH_SECTOR, overview=OVERVIEW, technical=TECH_SPARSE), "GARAN"),
    "missing_sma200_is_balanced": (
        lambda: _with_service(stock=STOCK_WITH_SECTOR, overview=FLAT_OVERVIEW, technical=TECH_NO_SMA200), "EREGL"),
    "data_only_under_dot_is_suffix": (
        lambda: _with_service(stock=STOCK_WITH_SECTOR, overview=OVERVIEW, technical=TECH_BULL_OVERBOUGHT,
                              suffix_only=True), "KCHOL"),
    "no_service_uses_defaults": (lambda: SimpleNamespace(services=SimpleNamespace(), stock_lookup_service=None), "SISE"),
    "lookup_service_only": (
        lambda: SimpleNamespace(services=None, stock_lookup_service=SimpleNamespace(find_stock=lambda t: STOCK_WITH_SECTOR)),
        "TUPRS"),
    "no_container": (lambda: None, "AKBNK"),
}


def run_scenario(name: str) -> dict:
    make_container, ticker = SCENARIOS[name]
    controller = Stock360Controller(container=make_container())
    emitted: list[int] = []
    controller.overviewChanged.connect(lambda: emitted.append(1))

    controller._load_local_overview_and_technical(ticker)

    state = {k: v for k, v in vars(controller).items() if isinstance(v, (str, int, float, bool, type(None)))}
    return {"state": state, "overview_changed_emits": len(emitted)}


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_local_overview_and_technical_is_unchanged(name):
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert json.loads(json.dumps(run_scenario(name))) == golden[name]
