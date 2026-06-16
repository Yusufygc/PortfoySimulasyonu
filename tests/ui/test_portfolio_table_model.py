from decimal import Decimal

import pytest

pytest.importorskip("PySide6")
from src.qt_compat.qtcore import Qt

from src.domain.models.position import Position
from src.ui.portfolio_table_model import PortfolioTableModel, PortfolioTableData
from src.ui.shared.locale_tr import L10N


def test_portfolio_table_model_uses_requested_header_order():
    model = PortfolioTableModel(
        PortfolioTableData(
            positions=[],
            price_map={},
            ticker_map={},
            previous_close_map={},
        )
    )

    headers = [
        model.headerData(column, Qt.Horizontal)
        for column in range(model.columnCount())
    ]

    assert headers == [
        L10N.HISSE_BASLIK,
        L10N.MALIYET_FIYATI,
        L10N.GUNCEL_FIYAT,
        L10N.GUNLUK_DEGISIM_YUZDESI,
        L10N.LOT_SAYISI,
        L10N.PIYASA_DEGERI,
        L10N.TOPLAM_DEGISIM_YUZDESI,
        L10N.KAR_ZARAR_MIKTARI,
    ]


def test_portfolio_table_model_displays_daily_and_total_change_percentages():
    model = PortfolioTableModel(
        PortfolioTableData(
            positions=[Position(stock_id=1, total_quantity=10, total_cost=Decimal("100"))],
            price_map={1: Decimal("12")},
            ticker_map={1: "ASELS.IS"},
            previous_close_map={1: Decimal("11")},
        )
    )

    assert model.data(model.index(0, 1)) == "10.00"
    assert model.data(model.index(0, 2)) == "12.00"
    assert model.data(model.index(0, 3)) == "%+9.09"
    assert model.data(model.index(0, 4)) == "10"
    assert model.data(model.index(0, 5)) == "120.00"
    assert model.data(model.index(0, 6)) == "%+20.00"
    assert model.data(model.index(0, 7)) == "+20.00"


def test_portfolio_table_model_returns_dash_without_previous_close():
    model = PortfolioTableModel(
        PortfolioTableData(
            positions=[Position(stock_id=1, total_quantity=10, total_cost=Decimal("100"))],
            price_map={1: Decimal("12")},
            ticker_map={1: "ASELS.IS"},
            previous_close_map={},
        )
    )

    assert model.data(model.index(0, 3)) == "-"
