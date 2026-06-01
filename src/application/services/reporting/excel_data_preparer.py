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

logger = logging.getLogger(__name__)


def _sf(val: Optional[Decimal]) -> Optional[float]:
    """Decimal → float; None ve Decimal("0") her ikisi de doğru işlenir."""
    return float(val) if val is not None else None


class ExcelDataPreparer:
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

        latest_snapshot = next(
            (snapshot for snapshot in reversed(snapshots) if snapshot.status == PortfolioStatus.OPEN),
            snapshots[-1],
        )
        latest_date = latest_snapshot.date
        latest_positions = {p.ticker: p for p in positions if p.date == latest_date}

        best_stock  = max(
            latest_positions.values(),
            key=lambda p: p.unrealized_pnl_pct if p.unrealized_pnl_pct is not None else Decimal("-inf"),
            default=None,
        )
        worst_stock = min(
            latest_positions.values(),
            key=lambda p: p.unrealized_pnl_pct if p.unrealized_pnl_pct is not None else Decimal("inf"),
            default=None,
        )

        records = [
            {"Metrik": "Toplam Maliyet",           "Değer": self._fmt_tr_money(latest_snapshot.total_cost_basis)},
            {"Metrik": "Güncel Portföy Değeri",     "Değer": self._fmt_tr_money(latest_snapshot.total_value)},
            {"Metrik": "Toplam Kâr/Zarar (TL)",    "Değer": self._fmt_tr_money(latest_snapshot.cumulative_pnl)},
            {"Metrik": "Toplam Getiri (%)",         "Değer": self._fmt_tr_pct(latest_snapshot.cumulative_return_pct)},
        ]

        if best_stock:
            pct_str = f"{float(best_stock.unrealized_pnl_pct * 100):.2f}%" if best_stock.unrealized_pnl_pct is not None else "N/A"
            records.append({"Metrik": "En İyi Performans",  "Değer": f"{best_stock.ticker} ({pct_str})"})
        if worst_stock:
            pct_str = f"{float(worst_stock.unrealized_pnl_pct * 100):.2f}%" if worst_stock.unrealized_pnl_pct is not None else "N/A"
            records.append({"Metrik": "En Kötü Performans", "Değer": f"{worst_stock.ticker} ({pct_str})"})

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

            total_cost_basis       = Decimal("0")
            total_position_value   = Decimal("0")
            total_unrealized_pnl   = Decimal("0")

            for p in day_positions:
                records.append({
                    "Tarih":                  p.date,
                    "Hisse":                  p.ticker,
                    "Adet":                   p.quantity,
                    "Ort. Maliyet (TL)":      float(p.avg_cost),
                    "Güncel Fiyat (TL)":      _sf(p.close_price),
                    "Toplam Maliyet (TL)":    float(p.cost_basis),
                    "Pozisyon Değeri (TL)":   _sf(p.position_value),
                    "Günlük Fiyat Değ. (%)":  self._format_pct(p.daily_price_change_pct),
                    "Günlük K/Z (TL)":        _sf(p.daily_pnl_tl),
                    "Toplam K/Z (TL)":        _sf(p.unrealized_pnl_tl),
                    "Toplam K/Z (%)":         self._format_pct(p.unrealized_pnl_pct),
                    "Portföy Ağırlığı (%)":   self._format_pct(p.weight_pct),
                })

                total_cost_basis     += p.cost_basis
                if p.position_value is not None:
                    total_position_value += p.position_value
                if p.unrealized_pnl_tl is not None:
                    total_unrealized_pnl += p.unrealized_pnl_tl

            snapshot = snapshot_map.get(d)
            total_unrealized_ratio = (
                total_unrealized_pnl / total_cost_basis
                if total_cost_basis != 0 else None
            )

            records.append({
                "Tarih":                  None,
                "Hisse":                  SUMMARY_ROW_LABEL,
                "Adet":                   None,
                "Ort. Maliyet (TL)":      None,
                "Güncel Fiyat (TL)":      None,
                "Toplam Maliyet (TL)":    float(total_cost_basis),
                "Pozisyon Değeri (TL)":   float(total_position_value),
                "Günlük Fiyat Değ. (%)":  self._format_pct(snapshot.daily_return_pct if snapshot else None),
                "Günlük K/Z (TL)":        _sf(snapshot.daily_pnl if snapshot else None),
                "Toplam K/Z (TL)":        float(total_unrealized_pnl),
                "Toplam K/Z (%)":         self._format_pct(total_unrealized_ratio),
                "Portföy Ağırlığı (%)":   self._format_pct(Decimal("1.0")),
            })

        return pd.DataFrame.from_records(records)

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

    def build_chart_data_df(self, summary_df: pd.DataFrame) -> pd.DataFrame:
        if summary_df.empty:
            return pd.DataFrame()

        base_cols = ["Tarih", "Portföy Değeri (TL)", "Günlük Getiri (%)", "Toplam Getiri (%)"]
        chart_df = summary_df[[c for c in base_cols if c in summary_df.columns]].copy()
        daily_return = pd.to_numeric(chart_df["Günlük Getiri (%)"], errors="coerce")
        chart_df["Pozitif Günlük Getiri (%)"] = daily_return.where(daily_return >= 0)
        chart_df["Negatif Günlük Getiri (%)"] = daily_return.where(daily_return < 0)

        value = pd.to_numeric(chart_df["Portföy Değeri (TL)"], errors="coerce")
        running_peak = value.cummax()
        drawdown = (value - running_peak) / running_peak.where(running_peak != 0)
        chart_df["Drawdown (%)"] = drawdown.where(drawdown.notna(), 0).clip(upper=0)

        cost_basis_col = "Toplam Maliyet (TL)"
        if cost_basis_col in summary_df.columns:
            chart_df[cost_basis_col] = pd.to_numeric(summary_df[cost_basis_col], errors="coerce")
        else:
            chart_df[cost_basis_col] = None

        return chart_df[[
            "Tarih",
            "Portföy Değeri (TL)",
            "Pozitif Günlük Getiri (%)",
            "Negatif Günlük Getiri (%)",
            "Toplam Getiri (%)",
            "Drawdown (%)",
            cost_basis_col,
        ]]

    def dashboard_stats(self, summary_df: pd.DataFrame, stock_summary_df: pd.DataFrame) -> dict:
        stats = {
            "period": "Veri yok",
            "portfolio_sentence": "Portföy değeri grafiği için yeterli veri yok.",
            "return_sentence": "Getiri grafikleri için yeterli veri yok.",
            "allocation_sentence": "Hisse dağılımı için yeterli veri yok.",
            "rows": [],
            "top_holdings": [],
        }
        if not summary_df.empty:
            df = summary_df.copy()
            df["Tarih"] = pd.to_datetime(df["Tarih"], errors="coerce")
            df = df.dropna(subset=["Tarih"]).reset_index(drop=True)
            if not df.empty:
                first = df.iloc[0]
                last = df.iloc[-1]
                start_value = self._num(first.get("Portföy Değeri (TL)"))
                end_value = self._num(last.get("Portföy Değeri (TL)"))
                change_tl = end_value - start_value if start_value is not None and end_value is not None else None
                change_pct = change_tl / start_value if change_tl is not None and start_value else None

                value_series = pd.to_numeric(df["Portföy Değeri (TL)"], errors="coerce")
                peak_idx = value_series.idxmax() if value_series.notna().any() else None
                low_idx = value_series.idxmin() if value_series.notna().any() else None
                peak = df.loc[peak_idx] if peak_idx is not None else None
                low = df.loc[low_idx] if low_idx is not None else None

                daily_series = pd.to_numeric(df["Günlük Getiri (%)"], errors="coerce")
                best_idx = daily_series.idxmax() if daily_series.notna().any() else None
                worst_idx = daily_series.idxmin() if daily_series.notna().any() else None
                best = df.loc[best_idx] if best_idx is not None else None
                worst = df.loc[worst_idx] if worst_idx is not None else None

                stats["period"] = f"{self._fmt_date(first['Tarih'])} - {self._fmt_date(last['Tarih'])}"
                stats["rows"] = [
                    ("Rapor dönemi", stats["period"]),
                    ("Başlangıç değeri", self._fmt_tl(start_value)),
                    ("Bitiş değeri", self._fmt_tl(end_value)),
                    ("Dönem değişimi", f"{self._fmt_tl(change_tl)} / {self._fmt_pct_value(change_pct)}"),
                    (
                        "En yüksek değer",
                        f"{self._fmt_tl(self._num(peak['Portföy Değeri (TL)']))} ({self._fmt_date(peak['Tarih'])})" if peak is not None else "—",
                    ),
                    (
                        "En düşük değer",
                        f"{self._fmt_tl(self._num(low['Portföy Değeri (TL)']))} ({self._fmt_date(low['Tarih'])})" if low is not None else "—",
                    ),
                    ("Dönem sonu getiri", self._fmt_pct_value(self._num(last.get("Toplam Getiri (%)")))),
                ]
                stats["portfolio_sentence"] = (
                    f"Portföy {stats['period']} döneminde {self._fmt_tl(start_value)} seviyesinden "
                    f"{self._fmt_tl(end_value)} seviyesine geldi. Net değişim {self._fmt_tl(change_tl)} "
                    f"({self._fmt_pct_value(change_pct)})."
                )
                stats["return_sentence"] = (
                    f"En iyi günlük getiri {self._fmt_date(best['Tarih'])} tarihinde "
                    f"{self._fmt_pct_value(self._num(best['Günlük Getiri (%)']))}; en kötü günlük getiri "
                    f"{self._fmt_date(worst['Tarih'])} tarihinde {self._fmt_pct_value(self._num(worst['Günlük Getiri (%)']))}."
                    if best is not None and worst is not None
                    else stats["return_sentence"]
                )

        holdings = self.top_holdings(stock_summary_df)
        if holdings:
            stats["top_holdings"] = holdings
            leader = holdings[0]
            stats["allocation_sentence"] = (
                f"En büyük ağırlık {leader['ticker']} hissesinde: "
                f"{self._fmt_tl(leader['value'])} ({self._fmt_pct_value(leader['weight'])})."
            )
        return stats

    def top_holdings(self, stock_summary_df: pd.DataFrame) -> list[dict]:
        if stock_summary_df.empty or "Son Pozisyon Değeri (TL)" not in stock_summary_df.columns:
            return []
        df = stock_summary_df[["Hisse", "Son Pozisyon Değeri (TL)"]].copy()
        df["Son Pozisyon Değeri (TL)"] = pd.to_numeric(df["Son Pozisyon Değeri (TL)"], errors="coerce")
        df = df.dropna(subset=["Son Pozisyon Değeri (TL)"])
        total_value = df["Son Pozisyon Değeri (TL)"].sum()
        if total_value <= 0:
            return []
        df = df.sort_values("Son Pozisyon Değeri (TL)", ascending=False).reset_index(drop=True)
        top_rows = [
            {
                "ticker": row["Hisse"],
                "value": float(row["Son Pozisyon Değeri (TL)"]),
                "weight": float(row["Son Pozisyon Değeri (TL)"] / total_value),
            }
            for _, row in df.head(3).iterrows()
        ]
        remainder = float(df.iloc[3:]["Son Pozisyon Değeri (TL)"].sum())
        if remainder > 0:
            top_rows.append({"ticker": "Diğer", "value": remainder, "weight": remainder / total_value})
        return top_rows
