# src/application/services/reporting/excel_data_preparer.py

import logging
from decimal import Decimal
from typing import List, Iterable, Optional
import pandas as pd

from src.application.services.reporting.daily_history_models import (
    DailyPosition,
    DailyPortfolioSnapshot,
    PortfolioStatus,
    SUMMARY_ROW_LABEL,
)
from src.application.services.reporting.excel_dashboard_stats_calculator import ExcelDashboardStatsCalculator

logger = logging.getLogger(__name__)


def _sf(val: Optional[Decimal]) -> Optional[float]:
    """Decimal → float; None ve Decimal("0") her ikisi de doğru işlenir."""
    return float(val) if val is not None else None


def _latest_open_snapshot(snapshots):
    return next((s for s in reversed(snapshots) if s.status == PortfolioStatus.OPEN), snapshots[-1])


def _positions_on_date(positions, target_date):
    return {p.ticker: p for p in positions if p.date == target_date}


def _max_pnl_key(p):
    return p.unrealized_pnl_pct if p.unrealized_pnl_pct is not None else Decimal("-inf")


def _min_pnl_key(p):
    return p.unrealized_pnl_pct if p.unrealized_pnl_pct is not None else Decimal("inf")


def _format_pnl_pct_str(pos) -> str:
    if pos.unrealized_pnl_pct is None:
        return "N/A"
    return f"{float(pos.unrealized_pnl_pct * 100):.2f}%"


class ExcelDataPreparer:
    def __init__(self) -> None:
        self._dashboard_stats_calculator = ExcelDashboardStatsCalculator()

    @staticmethod
    def normalize_date_column(df: pd.DataFrame, column: str = "Tarih") -> pd.DataFrame:
        if df.empty or column not in df.columns:
            return df

        normalized_df = df.copy()
        normalized_dates = pd.to_datetime(normalized_df[column], errors="coerce")
        normalized_df[column] = normalized_dates.dt.date
        normalized_df.loc[normalized_dates.isna(), column] = None
        return normalized_df

    def _format_pct(self, value: Optional[Decimal]) -> Optional[float]:
        return float(value) if value is not None else None

    def build_dashboard_df(
        self,
        snapshots: List[DailyPortfolioSnapshot],
        positions: List[DailyPosition],
    ) -> pd.DataFrame:
        if not snapshots:
            return pd.DataFrame()

        latest_snapshot = _latest_open_snapshot(snapshots)
        latest_positions = _positions_on_date(positions, latest_snapshot.date)

        best_stock = max(latest_positions.values(), key=_max_pnl_key, default=None)
        worst_stock = min(latest_positions.values(), key=_min_pnl_key, default=None)

        records = [
            {"Metrik": "Toplam Maliyet",           "Değer": self._fmt_tr_money(latest_snapshot.total_cost_basis)},
            {"Metrik": "Güncel Portföy Değeri",     "Değer": self._fmt_tr_money(latest_snapshot.total_value)},
            {"Metrik": "Toplam Kâr/Zarar (TL)",    "Değer": self._fmt_tr_money(latest_snapshot.cumulative_pnl)},
            {"Metrik": "Toplam Getiri (%)",         "Değer": self._fmt_tr_pct(latest_snapshot.cumulative_return_pct)},
        ]

        if best_stock:
            records.append({"Metrik": "En İyi Performans",  "Değer": f"{best_stock.ticker} ({_format_pnl_pct_str(best_stock)})"})
        if worst_stock:
            records.append({"Metrik": "En Kötü Performans", "Değer": f"{worst_stock.ticker} ({_format_pnl_pct_str(worst_stock)})"})

        return pd.DataFrame(records)

    def _fmt_tr_money(self, val: Optional[Decimal]) -> str:
        if val is None:
            return "—"
        s = f"{val:,.2f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")

    def _fmt_tr_pct(self, val: Optional[Decimal]) -> str:
        if val is None:
            return "—"
        s = f"{val * 100:.2f}"
        return f"%{s.replace('.', ',')}"

    @staticmethod
    def _num(value) -> float | None:
        if value is None or pd.isna(value):
            return None
        return float(value)

    @staticmethod
    def _fmt_date(value) -> str:
        if pd.isna(value):
            return "—"
        return pd.to_datetime(value).strftime("%d.%m.%Y")

    def _fmt_tl(self, value: float | None) -> str:
        if value is None:
            return "—"
        s = f"{value:,.2f}"
        return f"{s.replace(',', 'X').replace('.', ',').replace('X', '.')} TL"

    @staticmethod
    def _fmt_pct_value(value: float | None) -> str:
        if value is None:
            return "—"
        return f"%{value * 100:.2f}".replace(".", ",")

    def build_detail_df(
        self,
        positions: Iterable[DailyPosition],
        snapshots: Iterable[DailyPortfolioSnapshot],
    ) -> pd.DataFrame:
        snapshot_map = {s.date: s for s in snapshots}
        positions_by_date: dict = {}
        for p in positions:
            positions_by_date.setdefault(p.date, []).append(p)

        records = []
        for d in sorted(positions_by_date):
            day_positions = sorted(positions_by_date[d], key=lambda x: x.ticker)
            day_records, totals = self._detail_rows_for_day(day_positions)
            records.extend(day_records)
            records.append(self._detail_total_row(snapshot_map.get(d), totals))

        return pd.DataFrame.from_records(records)

    def _detail_rows_for_day(self, day_positions: list[DailyPosition]) -> tuple[list[dict], dict]:
        totals = {"cost_basis": Decimal("0"), "position_value": Decimal("0"), "unrealized_pnl": Decimal("0")}
        records = []
        for position in day_positions:
            records.append(self._detail_position_row(position))
            totals["cost_basis"] += position.cost_basis
            if position.position_value is not None:
                totals["position_value"] += position.position_value
            if position.unrealized_pnl_tl is not None:
                totals["unrealized_pnl"] += position.unrealized_pnl_tl
        return records, totals

    def _detail_position_row(self, position: DailyPosition) -> dict:
        return {
            "Tarih": position.date,
            "Hisse": position.ticker,
            "Adet": position.quantity,
            "Ort. Maliyet (TL)": float(position.avg_cost),
            "Güncel Fiyat (TL)": _sf(position.close_price),
            "Toplam Maliyet (TL)": float(position.cost_basis),
            "Pozisyon Değeri (TL)": _sf(position.position_value),
            "Günlük Fiyat Değ. (%)": self._format_pct(position.daily_price_change_pct),
            "Günlük K/Z (TL)": _sf(position.daily_pnl_tl),
            "Toplam K/Z (TL)": _sf(position.unrealized_pnl_tl),
            "Toplam K/Z (%)": self._format_pct(position.unrealized_pnl_pct),
            "Portföy Ağırlığı (%)": self._format_pct(position.weight_pct),
        }

    def _detail_total_row(self, snapshot: DailyPortfolioSnapshot | None, totals: dict) -> dict:
        total_unrealized_ratio = (
            totals["unrealized_pnl"] / totals["cost_basis"]
            if totals["cost_basis"] != 0 else None
        )
        return {
            "Tarih": None,
            "Hisse": SUMMARY_ROW_LABEL,
            "Adet": None,
            "Ort. Maliyet (TL)": None,
            "Güncel Fiyat (TL)": None,
            "Toplam Maliyet (TL)": float(totals["cost_basis"]),
            "Pozisyon Değeri (TL)": float(totals["position_value"]),
            "Günlük Fiyat Değ. (%)": self._format_pct(snapshot.daily_return_pct if snapshot else None),
            "Günlük K/Z (TL)": _sf(snapshot.daily_pnl if snapshot else None),
            "Toplam K/Z (TL)": float(totals["unrealized_pnl"]),
            "Toplam K/Z (%)": self._format_pct(total_unrealized_ratio),
            "Portföy Ağırlığı (%)": self._format_pct(Decimal("1.0")),
        }

    def build_stock_summary_df(self, positions: List[DailyPosition]) -> pd.DataFrame:
        if not positions:
            return pd.DataFrame()

        latest_positions: dict = {}
        stock_days_count: dict = {}
        for p in positions:
            latest_positions[p.ticker] = p
            stock_days_count[p.ticker] = stock_days_count.get(p.ticker, 0) + 1

        records = []
        for ticker, p in latest_positions.items():
            records.append({
                "Hisse":                    ticker,
                "Son Adet":                 p.quantity,
                "Ort. Maliyet (TL)":        float(p.avg_cost),
                "Son Fiyat (TL)":           _sf(p.close_price),
                "Son Pozisyon Değeri (TL)": _sf(p.position_value),
                "K/Z (TL)":                 _sf(p.unrealized_pnl_tl),
                "K/Z (%)":                  self._format_pct(p.unrealized_pnl_pct),
                "Toplam Gün Sayısı":        stock_days_count[ticker],
            })

        df = pd.DataFrame.from_records(records)
        if not df.empty:
            df = df.sort_values("Hisse").reset_index(drop=True)
        return df

    def build_summary_df(self, snapshots: Iterable[DailyPortfolioSnapshot]) -> pd.DataFrame:
        records = []
        for s in snapshots:
            if s.status != PortfolioStatus.OPEN:
                continue
            records.append({
                "Tarih":              s.date,
                "Portföy Değeri (TL)": _sf(s.total_value),
                "Günlük Getiri (%)":   self._format_pct(s.daily_return_pct),
                "Toplam Getiri (%)":   self._format_pct(s.cumulative_return_pct),
                "Günlük K/Z (TL)":    _sf(s.daily_pnl),
                "Toplam K/Z (TL)":    _sf(s.cumulative_pnl),
                "Toplam Maliyet (TL)": _sf(s.total_cost_basis),
            })
        df = pd.DataFrame.from_records(records)
        if not df.empty:
            df = df.sort_values("Tarih").reset_index(drop=True)
        return df

    def dashboard_stats(self, summary_df: pd.DataFrame, stock_summary_df: pd.DataFrame) -> dict:
        return self._dashboard_stats_calculator.dashboard_stats(summary_df, stock_summary_df)

    def top_holdings(self, stock_summary_df: pd.DataFrame) -> list[dict]:
        return self._dashboard_stats_calculator.top_holdings(stock_summary_df)
