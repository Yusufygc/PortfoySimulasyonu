from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Mapping

import pandas as pd

from src.application.services.reporting.daily_history_models import ExportMode
from src.application.services.reporting.excel_formatter import ExcelFormatter
from src.domain.models.model_portfolio import ModelTradeSide


class ModelPortfolioExcelExportService:
    """Exports a selected model portfolio snapshot to Excel."""

    def __init__(
        self,
        model_portfolio_service,
        stock_repo,
        formatter: ExcelFormatter,
        history_simulation_service=None,
        report_builder=None,
    ) -> None:
        self._model_portfolio_service = model_portfolio_service
        self._stock_repo = stock_repo
        self._formatter = formatter
        self._history_simulation_service = history_simulation_service
        self._report_builder = report_builder

    def export_model_portfolio_history(
        self,
        portfolio_id: int,
        start_date: date,
        end_date: date,
        file_path: str | Path,
        mode: ExportMode = ExportMode.OVERWRITE,
    ) -> None:
        if self._history_simulation_service is None or self._report_builder is None:
            raise RuntimeError("Model portföy tarihsel rapor servisi yapılandırılmamış.")

        daily_positions, daily_snapshots = self._history_simulation_service.simulate_history(
            portfolio_id=portfolio_id,
            start_date=start_date,
            end_date=end_date,
        )
        if not daily_positions and not daily_snapshots:
            raise ValueError("Belirtilen tarih aralığında gösterilecek veri bulunamadı.")

        self._report_builder.build_and_save(
            file_path=Path(file_path),
            daily_positions=daily_positions,
            daily_snapshots=daily_snapshots,
            mode=mode,
        )

    def export_model_portfolio(
        self,
        portfolio_id: int,
        price_map: Mapping[int, Decimal],
        file_path: str | Path,
    ) -> None:
        portfolio = self._model_portfolio_service.get_portfolio_by_id(portfolio_id)
        if portfolio is None:
            raise ValueError("Model portföy bulunamadı.")

        positions = self._model_portfolio_service.get_positions_with_details(portfolio_id, dict(price_map))
        trades = self._model_portfolio_service.get_portfolio_trades(portfolio_id)
        if not positions and not trades:
            raise ValueError("Bu model portföyde raporlanacak pozisyon veya işlem bulunamadı.")

        summary = self._model_portfolio_service.get_portfolio_summary(portfolio_id, dict(price_map))
        stock_map = self._stock_map_for_trades(trades)

        dataframes = {
            "Özet": self._summary_df(portfolio.name, summary),
            "Pozisyonlar": self._positions_df(positions),
            "İşlemler": self._trades_df(trades, stock_map),
        }

        path = Path(file_path)
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            for sheet_name, df in dataframes.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                self._formatter.apply_formatting(writer, sheet_name, df)

    def _stock_map_for_trades(self, trades) -> dict[int, object]:
        stock_ids = sorted({trade.stock_id for trade in trades})
        stocks = self._stock_repo.get_stocks_by_ids(stock_ids) if stock_ids else []
        return {stock.id: stock for stock in stocks if stock.id is not None}

    @staticmethod
    def _summary_df(portfolio_name: str, summary: dict) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"Metrik": "Portföy", "Değer": portfolio_name},
                {"Metrik": "Rapor Tarihi", "Değer": date.today()},
                {"Metrik": "Başlangıç Nakit (TL)", "Değer": _decimal_or_none(summary.get("initial_cash"))},
                {"Metrik": "Kalan Nakit (TL)", "Değer": _decimal_or_none(summary.get("remaining_cash"))},
                {"Metrik": "Pozisyon Değeri (TL)", "Değer": _decimal_or_none(summary.get("positions_value"))},
                {"Metrik": "Toplam Değer (TL)", "Değer": _decimal_or_none(summary.get("total_value"))},
                {"Metrik": "K/Z (TL)", "Değer": _decimal_or_none(summary.get("profit_loss"))},
                {"Metrik": "K/Z (%)", "Değer": _percent_or_none(summary.get("profit_loss_pct"))},
            ]
        )

    @staticmethod
    def _positions_df(positions: list[dict]) -> pd.DataFrame:
        rows = []
        for pos in positions:
            rows.append(
                {
                    "Hisse": _display_ticker(pos.get("name") or pos.get("ticker") or ""),
                    "Lot": pos.get("quantity"),
                    "Ort. Maliyet (TL)": _decimal_or_none(pos.get("avg_cost")),
                    "Toplam Maliyet (TL)": _decimal_or_none(pos.get("total_cost")),
                    "Güncel Fiyat (TL)": _decimal_or_none(pos.get("current_price")),
                    "Güncel Değer (TL)": _decimal_or_none(pos.get("current_value")),
                    "K/Z (TL)": _decimal_or_none(pos.get("profit_loss")),
                }
            )
        return pd.DataFrame(rows)

    @staticmethod
    def _trades_df(trades, stock_map: dict[int, object]) -> pd.DataFrame:
        rows = []
        for trade in trades:
            stock = stock_map.get(trade.stock_id)
            ticker = stock.ticker if stock else str(trade.stock_id)
            rows.append(
                {
                    "Tarih": trade.trade_date,
                    "İşlem": "ALIM" if trade.side == ModelTradeSide.BUY else "SATIM",
                    "Hisse": _display_ticker(ticker),
                    "Lot": trade.quantity,
                    "Fiyat (TL)": _decimal_or_none(trade.price),
                    "Tutar (TL)": _decimal_or_none(trade.total_amount),
                }
            )
        return pd.DataFrame(rows)


def _decimal_or_none(value) -> float | None:
    return float(value) if value is not None else None


def _percent_or_none(value) -> float | None:
    return float(value) / 100 if value is not None else None


def _display_ticker(value: str | None) -> str:
    text = (value or "").strip()
    return text[:-3] if text.upper().endswith(".IS") else text
