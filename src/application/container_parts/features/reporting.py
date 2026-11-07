"""Geçmiş simülasyonu ve Excel raporları."""
from __future__ import annotations

from src.application.container_parts.features._context import BuildContext
from src.application.services.reporting.excel_export_service import ExcelExportService
from src.application.services.reporting.excel_formatter import ExcelFormatter
from src.application.services.reporting.excel_report_builder import ExcelReportBuilder
from src.application.services.reporting.model_portfolio_excel_export_service import ModelPortfolioExcelExportService
from src.application.services.simulation.history_simulation_service import HistorySimulationService
from src.application.services.simulation.model_portfolio_history_simulation_service import (
    ModelPortfolioHistorySimulationService,
)

PROVIDES = (
    "history_simulation_service", "model_portfolio_history_simulation_service", "excel_formatter",
    "excel_report_builder", "excel_export_service", "model_portfolio_excel_export_service",
)


def build(ctx: BuildContext) -> dict:
    r, m = ctx.repositories, ctx.market_clients
    history = HistorySimulationService(
        portfolio_repo=r.portfolio_repo, price_repo=r.price_repo, stock_repo=r.stock_repo,
        trading_calendar=m.trading_calendar,
    )
    model_history = ModelPortfolioHistorySimulationService(
        model_portfolio_repo=r.model_portfolio_repo, price_repo=r.price_repo, stock_repo=r.stock_repo,
        trading_calendar=m.trading_calendar,
    )
    formatter = ExcelFormatter()
    builder = ExcelReportBuilder(formatter=formatter)
    return {
        "history_simulation_service": history,
        "model_portfolio_history_simulation_service": model_history,
        "excel_formatter": formatter,
        "excel_report_builder": builder,
        "excel_export_service": ExcelExportService(simulation_service=history, report_builder=builder),
        "model_portfolio_excel_export_service": ModelPortfolioExcelExportService(
            model_portfolio_service=ctx.services["model_portfolio_service"], stock_repo=r.stock_repo,
            formatter=formatter, history_simulation_service=model_history, report_builder=builder,
        ),
    }
