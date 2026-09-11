import sys
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytest.importorskip("PySide6")
from src.qt_compat.qtwidgets import QApplication

from src.application.services.simulation.dca_backtest import DCABacktestResult
from src.ui.widgets.planning.panels.dca_simulation_panel import DCASimulationPanel

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


@pytest.fixture
def dummy_container():
    mock_dca = MagicMock()
    mock_dca.run.return_value = DCABacktestResult(
        portfolio_value_series={date(2023, 1, 1): Decimal("60000")},
        total_invested=Decimal("60000"),
        final_value=Decimal("112500"),
        shares_by_ticker={"THYAO": Decimal("250")},
        total_return_pct=87.5,
        contribution_count=12,
    )
    return SimpleNamespace(dca_backtest_service=mock_dca)


def test_dca_simulation_panel_init(dummy_container):
    panel = DCASimulationPanel(container=dummy_container)
    assert panel._spin_contrib.value() == 5000.0
    assert panel._combo_period.count() >= 3


def test_dca_simulation_panel_done(dummy_container):
    panel = DCASimulationPanel(container=dummy_container)
    res = dummy_container.dca_backtest_service.run()
    panel._on_sim_done(res)
    assert panel._table.rowCount() == 1
    assert panel._table.item(0, 0).text() == "THYAO"
