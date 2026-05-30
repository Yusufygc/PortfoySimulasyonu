from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pandas as pd

from src.application.services.reporting.excel_formatter import ExcelFormatter
from src.application.services.reporting.daily_history_models import ExportMode
from src.application.services.reporting.model_portfolio_excel_export_service import (
    ModelPortfolioExcelExportService,
)
from src.domain.models.model_portfolio import ModelPortfolio, ModelPortfolioTrade, ModelTradeSide
from src.domain.models.stock import Stock


class FakeModelPortfolioService:
    def get_portfolio_by_id(self, portfolio_id):
        return ModelPortfolio(id=portfolio_id, name="deneme portföy", initial_cash=Decimal("100000"))

    def get_portfolio_summary(self, portfolio_id, price_map):
        return {
            "initial_cash": Decimal("100000"),
            "remaining_cash": Decimal("50000"),
            "positions_value": Decimal("62500"),
            "total_value": Decimal("112500"),
            "profit_loss": Decimal("12500"),
            "profit_loss_pct": Decimal("12.5"),
        }

    def get_positions_with_details(self, portfolio_id, price_map):
        return [
            {
                "stock_id": 1,
                "ticker": "FROTO.IS",
                "name": "FROTO.IS",
                "quantity": 10,
                "avg_cost": Decimal("100"),
                "total_cost": Decimal("1000"),
                "current_price": Decimal("125"),
                "current_value": Decimal("1250"),
                "profit_loss": Decimal("250"),
            },
            {
                "stock_id": 2,
                "ticker": "SISE.IS",
                "name": "SISE.IS",
                "quantity": 5,
                "avg_cost": Decimal("20"),
                "total_cost": Decimal("100"),
                "current_price": None,
                "current_value": None,
                "profit_loss": None,
            },
        ]

    def get_portfolio_trades(self, portfolio_id):
        return [
            ModelPortfolioTrade(
                id=1,
                portfolio_id=portfolio_id,
                stock_id=1,
                trade_date=date(2026, 5, 1),
                trade_time=None,
                side=ModelTradeSide.BUY,
                quantity=10,
                price=Decimal("100"),
            )
        ]


class FakeStockRepo:
    def get_stocks_by_ids(self, stock_ids):
        return [Stock(id=1, ticker="FROTO.IS", name="FROTO")]


def test_model_portfolio_excel_export_creates_expected_sheets(tmp_path):
    service = ModelPortfolioExcelExportService(
        model_portfolio_service=FakeModelPortfolioService(),
        stock_repo=FakeStockRepo(),
        formatter=ExcelFormatter(),
    )
    file_path = tmp_path / "model.xlsx"

    service.export_model_portfolio(1, {1: Decimal("125")}, file_path)

    sheets = pd.read_excel(file_path, sheet_name=None)
    assert set(sheets) == {"Özet", "Pozisyonlar", "İşlemler"}
    assert sheets["Pozisyonlar"].loc[0, "Hisse"] == "FROTO"
    assert sheets["İşlemler"].loc[0, "Hisse"] == "FROTO"
    assert sheets["Özet"].loc[sheets["Özet"]["Metrik"] == "K/Z (%)", "Değer"].iloc[0] == 0.125
    assert pd.isna(sheets["Pozisyonlar"].loc[1, "Güncel Fiyat (TL)"])


def test_model_portfolio_excel_export_rejects_empty_portfolio(tmp_path):
    empty_service = SimpleNamespace(
        get_portfolio_by_id=lambda portfolio_id: ModelPortfolio(id=portfolio_id, name="boş"),
        get_positions_with_details=lambda portfolio_id, price_map: [],
        get_portfolio_trades=lambda portfolio_id: [],
    )
    service = ModelPortfolioExcelExportService(
        model_portfolio_service=empty_service,
        stock_repo=FakeStockRepo(),
        formatter=ExcelFormatter(),
    )

    try:
        service.export_model_portfolio(1, {}, tmp_path / "empty.xlsx")
    except ValueError as exc:
        assert "raporlanacak" in str(exc)
    else:
        raise AssertionError("Expected ValueError for empty model portfolio")


def test_model_portfolio_history_export_uses_dashboard_report_builder(tmp_path):
    daily_positions = [SimpleNamespace(date=date(2026, 5, 1), ticker="FROTO.IS")]
    daily_snapshots = [SimpleNamespace(date=date(2026, 5, 1), status="Piyasa Açık")]
    simulation = SimpleNamespace(
        simulate_history=lambda portfolio_id, start_date, end_date: (daily_positions, daily_snapshots)
    )
    builder_calls = []
    builder = SimpleNamespace(
        build_and_save=lambda **kwargs: builder_calls.append(kwargs)
    )
    service = ModelPortfolioExcelExportService(
        model_portfolio_service=FakeModelPortfolioService(),
        stock_repo=FakeStockRepo(),
        formatter=ExcelFormatter(),
        history_simulation_service=simulation,
        report_builder=builder,
    )
    file_path = tmp_path / "history.xlsx"

    service.export_model_portfolio_history(
        portfolio_id=7,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 26),
        file_path=file_path,
        mode=ExportMode.OVERWRITE,
    )

    assert builder_calls == [
        {
            "file_path": file_path,
            "daily_positions": daily_positions,
            "daily_snapshots": daily_snapshots,
            "mode": ExportMode.OVERWRITE,
        }
    ]
