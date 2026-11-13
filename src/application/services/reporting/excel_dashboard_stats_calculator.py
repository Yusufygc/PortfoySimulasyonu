from __future__ import annotations

import pandas as pd
from typing import NamedTuple


class _PeriodValues(NamedTuple):
    start_value: "float | None"
    end_value: "float | None"
    change_tl: "float | None"
    change_pct: "float | None"


class ExcelDashboardStatsCalculator:
    def dashboard_stats(self, summary_df: pd.DataFrame, stock_summary_df: pd.DataFrame) -> dict:
        stats = self._empty_stats()
        if not summary_df.empty:
            self._fill_summary_stats(stats, summary_df)

        holdings = self.top_holdings(stock_summary_df)
        if holdings:
            stats["top_holdings"] = holdings
            leader = holdings[0]
            stats["allocation_sentence"] = (
                f"En büyük ağırlık {leader['ticker']} hissesinde: "
                f"{self._fmt_tl(leader['value'])} ({self._fmt_pct_value(leader['weight'])})."
            )
        return stats

    @staticmethod
    def _empty_stats() -> dict:
        return {
            "period": "Veri yok",
            "portfolio_sentence": "Portföy değeri grafiği için yeterli veri yok.",
            "return_sentence": "Getiri grafikleri için yeterli veri yok.",
            "allocation_sentence": "Hisse dağılımı için yeterli veri yok.",
            "rows": [],
            "top_holdings": [],
        }

    def _fill_summary_stats(self, stats: dict, summary_df: pd.DataFrame) -> None:
        df = summary_df.copy()
        df["Tarih"] = pd.to_datetime(df["Tarih"], errors="coerce")
        df = df.dropna(subset=["Tarih"]).reset_index(drop=True)
        if df.empty:
            return

        first = df.iloc[0]
        last = df.iloc[-1]
        start_value = self._num(first.get("Portföy Değeri (TL)"))
        end_value = self._num(last.get("Portföy Değeri (TL)"))
        change_tl = end_value - start_value if start_value is not None and end_value is not None else None
        change_pct = change_tl / start_value if change_tl is not None and start_value else None
        peak, low, best, worst = self._summary_extremes(df)

        stats["period"] = f"{self._fmt_date(first['Tarih'])} - {self._fmt_date(last['Tarih'])}"
        stats["rows"] = self._summary_rows(
            stats["period"], last,
            _PeriodValues(start_value, end_value, change_tl, change_pct),
            peak, low,
        )
        stats["portfolio_sentence"] = (
            f"Portföy {stats['period']} döneminde {self._fmt_tl(start_value)} seviyesinden "
            f"{self._fmt_tl(end_value)} seviyesine geldi. Net değişim {self._fmt_tl(change_tl)} "
            f"({self._fmt_pct_value(change_pct)})."
        )
        if best is not None and worst is not None:
            stats["return_sentence"] = (
                f"En iyi günlük getiri {self._fmt_date(best['Tarih'])} tarihinde "
                f"{self._fmt_pct_value(self._num(best['Günlük Getiri (%)']))}; en kötü günlük getiri "
                f"{self._fmt_date(worst['Tarih'])} tarihinde {self._fmt_pct_value(self._num(worst['Günlük Getiri (%)']))}."
            )

    def _summary_rows(
        self,
        period: str,
        last,
        pv: _PeriodValues,
        peak,
        low,
    ) -> list[tuple[str, str]]:
        return [
            ("Rapor dönemi", period),
            ("Başlangıç değeri", self._fmt_tl(pv.start_value)),
            ("Bitiş değeri", self._fmt_tl(pv.end_value)),
            ("Dönem değişimi", f"{self._fmt_tl(pv.change_tl)} / {self._fmt_pct_value(pv.change_pct)}"),
            (
                "En yüksek değer",
                f"{self._fmt_tl(self._num(peak['Portföy Değeri (TL)']))} ({self._fmt_date(peak['Tarih'])})"
                if peak is not None
                else "—",
            ),
            (
                "En düşük değer",
                f"{self._fmt_tl(self._num(low['Portföy Değeri (TL)']))} ({self._fmt_date(low['Tarih'])})"
                if low is not None
                else "—",
            ),
            ("Dönem sonu getiri", self._fmt_pct_value(self._num(last.get("Toplam Getiri (%)")))),
        ]

    @staticmethod
    def _summary_extremes(df: pd.DataFrame) -> tuple:
        value_series = pd.to_numeric(df["Portföy Değeri (TL)"], errors="coerce")
        peak_idx = value_series.idxmax() if value_series.notna().any() else None
        low_idx = value_series.idxmin() if value_series.notna().any() else None
        daily_series = pd.to_numeric(df["Günlük Getiri (%)"], errors="coerce")
        best_idx = daily_series.idxmax() if daily_series.notna().any() else None
        worst_idx = daily_series.idxmin() if daily_series.notna().any() else None
        return (
            df.loc[peak_idx] if peak_idx is not None else None,
            df.loc[low_idx] if low_idx is not None else None,
            df.loc[best_idx] if best_idx is not None else None,
            df.loc[worst_idx] if worst_idx is not None else None,
        )

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
        return self._holding_rows(df, total_value)

    @staticmethod
    def _holding_rows(df: pd.DataFrame, total_value: float) -> list[dict]:
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

    @staticmethod
    def _fmt_tl(value: float | None) -> str:
        if value is None:
            return "—"
        text = f"{value:,.2f}"
        return f"{text.replace(',', 'X').replace('.', ',').replace('X', '.')} TL"

    @staticmethod
    def _fmt_pct_value(value: float | None) -> str:
        if value is None:
            return "—"
        return f"%{value * 100:.2f}".replace(".", ",")
