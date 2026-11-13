"""MarketAdjustmentController (tüm BIST sermaye artırımı düzeltmeleri) ve Ayarlar sekmesi testleri."""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import duckdb
import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

from src.application.services.corporate_actions.market_action_service import MarketCorporateActionService
from src.domain.models.market_corporate_action import MarketActionStatus
from src.infrastructure.market_data.duckdb_corporate_action_store import DuckDBCorporateActionStore
from src.infrastructure.market_data.duckdb_market_history_repo import DuckDBMarketHistoryRepository
from src.ui_qml.controllers.market_adjustment_controller import MarketAdjustmentController

QML_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"
START = date(2026, 1, 5)
DAYS = [d for d in (START + timedelta(days=i) for i in range(40)) if d.weekday() < 5]
SPLIT_DAY = DAYS[10]


class ImmediateExecutor:
    def submit(self, fn, *args, **kwargs):
        fn(*args, **kwargs)


def _capture(signal):
    received = []
    signal.connect(lambda *args: received.append(args))
    return received


@pytest.fixture
def container(tmp_path):
    path = tmp_path / "m.duckdb"
    con = duckdb.connect(str(path))
    con.execute("CREATE TABLE bist_stocks (ticker VARCHAR PRIMARY KEY, name VARCHAR)")
    con.execute(
        "CREATE TABLE daily_prices (ticker VARCHAR, price_date DATE, open_price DOUBLE, high_price DOUBLE, "
        "low_price DOUBLE, close_price DOUBLE, volume BIGINT, PRIMARY KEY (ticker, price_date))"
    )
    rows = []
    for ticker in ("SPLT", "FLAT", "FLT2"):
        con.execute("INSERT INTO bist_stocks VALUES (?, ?)", [ticker, ticker])
        for day in DAYS:
            price = (20.0 if day < SPLIT_DAY else 10.0) if ticker == "SPLT" else 5.0
            rows.append((ticker, day, price, price, price, price, 1000))
    con.executemany("INSERT INTO daily_prices VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
    con.close()
    store = DuckDBCorporateActionStore(path)
    history = DuckDBMarketHistoryRepository(path)
    return SimpleNamespace(
        market_corporate_action_service=MarketCorporateActionService(history, store),
        market_action_repo=store,
        history=history,
    )


def _ctrl(qapp, container):
    ctrl = MarketAdjustmentController(container=container)
    ctrl._executor = ImmediateExecutor()
    return ctrl


def test_scan_lists_candidate_and_confirm_changes_adjusted_prices(qapp, container):
    ctrl = _ctrl(qapp, container)
    notes, changed = _capture(ctrl.notification), _capture(ctrl.adjustmentsChanged)

    ctrl.scan()
    ctrl.refresh("CANDIDATE", "", 0)

    assert changed and "1 yeni aday" in notes[-1][1] and ctrl.isBusy is False
    assert ctrl.totalCount == 1
    row = ctrl.actions[0]
    assert row["ticker"] == "SPLT" and row["dateIso"] == SPLIT_DAY.isoformat()
    assert row["factorText"] == "0,5000" and row["status"] == "CANDIDATE" and row["canConfirm"] is True
    before = [b.close_price for b in container.history.get_price_series("SPLT", DAYS[0], DAYS[-1])]
    assert before[0] == 20.0  # onaya kadar fiyat değişmez

    ctrl.confirm("SPLT", row["dateIso"], "0,5")

    assert {b.close_price for b in container.history.get_price_series("SPLT", DAYS[0], DAYS[-1])} == {10.0}
    ctrl.refresh("CONFIRMED", "", 0)
    assert ctrl.actions[0]["isActive"] is True and ctrl.actions[0]["statusLabel"].startswith("Onaylı")


def test_confirm_with_custom_factor_ignore_and_reopen(qapp, container):
    ctrl = _ctrl(qapp, container)
    ctrl.scan()
    iso = SPLIT_DAY.isoformat()

    ctrl.confirm("SPLT", iso, "0,49")
    stored = container.market_action_repo.list_actions(ticker="SPLT")[0]
    assert stored.status == MarketActionStatus.CONFIRMED and stored.factor == pytest.approx(0.49)

    ctrl.reopen("SPLT", iso)
    assert container.market_action_repo.list_actions(ticker="SPLT")[0].status == MarketActionStatus.CANDIDATE

    ctrl.ignore("SPLT", iso)
    assert container.market_action_repo.list_actions(ticker="SPLT")[0].status == MarketActionStatus.IGNORED
    assert {b.close_price for b in container.history.get_price_series("SPLT", DAYS[0], DAYS[-1])} == {20.0, 10.0}


def test_invalid_input_is_reported_without_changes(qapp, container):
    ctrl = _ctrl(qapp, container)
    ctrl.scan()
    notes = _capture(ctrl.notification)

    ctrl.confirm("SPLT", "bozuk-tarih", "0,5")
    ctrl.confirm("SPLT", SPLIT_DAY.isoformat(), "abc")
    ctrl.confirm("SPLT", SPLIT_DAY.isoformat(), "-1")

    assert [n[0] for n in notes] == [False, False, False]
    assert container.market_action_repo.list_actions(ticker="SPLT")[0].status == MarketActionStatus.CANDIDATE


def test_refresh_filters_by_ticker_year_and_status(qapp, container):
    ctrl = _ctrl(qapp, container)
    ctrl.scan()

    ctrl.refresh("", "spl", 0)
    assert ctrl.totalCount == 1
    ctrl.refresh("", "FLAT", 0)
    assert ctrl.totalCount == 0
    ctrl.refresh("", "", 2027)
    assert ctrl.totalCount == 0
    ctrl.refresh("CONFIRMED", "", 0)
    assert ctrl.totalCount == 0


def test_controller_without_services_is_safe(qapp):
    ctrl = MarketAdjustmentController(container=None)
    notes = _capture(ctrl.notification)

    ctrl.scan()
    ctrl.refresh("", "", 0)
    ctrl.confirm("A", "2026-01-01", "0,5")

    assert ctrl.serviceAvailable is False and ctrl.actions == [] and notes and notes[-1][0] is False


def test_market_adjustment_tab_compiles_and_lists_candidates(qapp, container):
    ctrl = _ctrl(qapp, container)
    ctrl.scan()
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))
    warnings = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    engine.rootContext().setContextProperty("marketAdjustmentController", ctrl)
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / "components/SettingsMarketAdjustmentsTab.qml")))
    if not component.isReady():
        pytest.fail("\n".join(e.toString() for e in component.errors()))

    item = component.create()

    assert item is not None
    assert warnings == [], "\n".join(warnings)
    assert ctrl.totalCount == 1
