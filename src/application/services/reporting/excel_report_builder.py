# src/application/services/excel_report_builder.py

import logging
import shutil
from decimal import Decimal
from pathlib import Path
from typing import List, Iterable, Optional

import pandas as pd

from src.application.services.reporting.excel_formatter import ExcelFormatter
from src.application.services.reporting.daily_history_models import DailyPosition, DailyPortfolioSnapshot, ExportMode

logger = logging.getLogger(__name__)

class ExcelReportBuilder:
    def __init__(self, formatter: ExcelFormatter) -> None:
        self.formatter = formatter

    def build_and_save(
        self,
        file_path: Path,
        daily_positions: List[DailyPosition],
        daily_snapshots: List[DailyPortfolioSnapshot],
        mode: ExportMode
    ) -> None:
        detail_df = self._build_detail_df(daily_positions, daily_snapshots)
        summary_df = self._build_summary_df(daily_snapshots)
        stock_summary_df = self._build_stock_summary_df(daily_positions)
        dashboard_df = self._build_dashboard_df(daily_snapshots, daily_positions)

        if not file_path.exists() or mode == ExportMode.OVERWRITE:
            self._write_fresh_excel(file_path, summary_df, detail_df, stock_summary_df, dashboard_df)
        else:
            self._append_to_existing_excel(file_path, summary_df, detail_df, stock_summary_df, dashboard_df)

    def _format_pct(self, value: Optional[Decimal]) -> Optional[float]:
        if value is None:
            return None
        return float(value)

    def _build_dashboard_df(self, snapshots: List[DailyPortfolioSnapshot], positions: List[DailyPosition]) -> pd.DataFrame:
        if not snapshots:
            return pd.DataFrame()
        
        latest_snapshot = snapshots[-1]
        returns = [s.daily_return_pct for s in snapshots if s.daily_return_pct is not None]
        
        latest_date = latest_snapshot.date
        latest_positions = {}
        for p in positions:
            if p.date == latest_date:
                latest_positions[p.ticker] = p
        
        best_stock = max(latest_positions.values(), key=lambda p: p.unrealized_pnl_pct if p.unrealized_pnl_pct else Decimal('-inf')) if latest_positions else None
        worst_stock = min(latest_positions.values(), key=lambda p: p.unrealized_pnl_pct if p.unrealized_pnl_pct else Decimal('inf')) if latest_positions else None
        
        records = [
            {"Metrik": "Toplam Maliyet", "Değer": self._fmt_tr_money(latest_snapshot.total_cost_basis)},
            {"Metrik": "Güncel Portföy Değeri", "Değer": self._fmt_tr_money(latest_snapshot.total_value)},
            {"Metrik": "Toplam Kâr/Zarar (TL)", "Değer": self._fmt_tr_money(latest_snapshot.cumulative_pnl)},
            {"Metrik": "Toplam Getiri (%)", "Değer": self._fmt_tr_pct(latest_snapshot.cumulative_return_pct)},
        ]
        
        if best_stock:
            records.append({"Metrik": "En İyi Performans", "Değer": f"{best_stock.ticker} ({float(best_stock.unrealized_pnl_pct * 100):.2f}%)" if best_stock.unrealized_pnl_pct else "N/A"})
        if worst_stock:
            records.append({"Metrik": "En Kötü Performans", "Değer": f"{worst_stock.ticker} ({float(worst_stock.unrealized_pnl_pct * 100):.2f}%)" if worst_stock.unrealized_pnl_pct else "N/A"})
            
        return pd.DataFrame(records)

    def _fmt_tr_money(self, val: Optional[Decimal]) -> str:
        if val is None: return "0,00"
        s = f"{val:,.2f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")

    def _fmt_tr_pct(self, val: Optional[Decimal]) -> str:
        if val is None: return "%0,00"
        s = f"{val * 100:.2f}"
        return f"%{s.replace('.', ',')}"

    def _build_detail_df(self, positions: Iterable[DailyPosition], snapshots: Iterable[DailyPortfolioSnapshot]) -> pd.DataFrame:
        snapshot_map = {s.date: s for s in snapshots}
        positions_by_date = {}
        for p in positions:
            if p.date not in positions_by_date:
                positions_by_date[p.date] = []
            positions_by_date[p.date].append(p)
            
        records = []
        sorted_dates = sorted(positions_by_date.keys())
        
        for d in sorted_dates:
            day_positions = positions_by_date[d]
            day_positions.sort(key=lambda x: x.ticker)
            
            total_cost_basis = Decimal("0")
            total_position_value = Decimal("0")
            total_unrealized_pnl_tl = Decimal("0")
            
            for p in day_positions:
                records.append({
                    "Tarih": p.date,
                    "Hisse": p.ticker,
                    "Adet": p.quantity,
                    "Ort. Maliyet (TL)": float(p.avg_cost),
                    "Güncel Fiyat (TL)": float(p.close_price) if p.close_price else None,
                    "Toplam Maliyet (TL)": float(p.cost_basis),
                    "Pozisyon Değeri (TL)": float(p.position_value) if p.position_value else None,
                    "Günlük Fiyat Değ. (%)": self._format_pct(p.daily_price_change_pct),
                    "Günlük K/Z (TL)": float(p.daily_pnl_tl) if p.daily_pnl_tl is not None else None,
                    "Toplam K/Z (TL)": float(p.unrealized_pnl_tl) if p.unrealized_pnl_tl else None,
                    "Toplam K/Z (%)": self._format_pct(p.unrealized_pnl_pct),
                    "Portföy Ağırlığı (%)": self._format_pct(p.weight_pct),
                })
                
                if p.cost_basis: total_cost_basis += p.cost_basis
                if p.position_value: total_position_value += p.position_value
                if p.unrealized_pnl_tl: total_unrealized_pnl_tl += p.unrealized_pnl_tl

            snapshot = snapshot_map.get(d)
            total_unrealized_ratio = (total_unrealized_pnl_tl / total_cost_basis) if (total_cost_basis and total_cost_basis != 0) else None
            portfolio_daily_ret = snapshot.daily_return_pct if snapshot else None
            portfolio_daily_pnl = snapshot.daily_pnl if snapshot else None

            summary_row = {
                "Tarih": None,
                "Hisse": "GÜNLÜK TOPLAM ➤➤➤",
                "Adet": None,
                "Ort. Maliyet (TL)": None,
                "Güncel Fiyat (TL)": None,
                "Toplam Maliyet (TL)": float(total_cost_basis),
                "Pozisyon Değeri (TL)": float(total_position_value),
                "Günlük Fiyat Değ. (%)": self._format_pct(portfolio_daily_ret),
                "Günlük K/Z (TL)": float(portfolio_daily_pnl) if portfolio_daily_pnl is not None else None,
                "Toplam K/Z (TL)": float(total_unrealized_pnl_tl),
                "Toplam K/Z (%)": self._format_pct(total_unrealized_ratio),
                "Portföy Ağırlığı (%)": self._format_pct(Decimal("1.0")),
            }
            records.append(summary_row)

        return pd.DataFrame.from_records(records)

    def _build_stock_summary_df(self, positions: List[DailyPosition]) -> pd.DataFrame:
        if not positions:
            return pd.DataFrame()

        latest_positions = {}
        stock_days_count = {}

        for p in positions:
            latest_positions[p.ticker] = p
            stock_days_count[p.ticker] = stock_days_count.get(p.ticker, 0) + 1

        records = []
        for ticker, p in latest_positions.items():
            records.append({
                "Hisse": ticker,
                "Son Adet": p.quantity,
                "Ort. Maliyet (TL)": float(p.avg_cost),
                "Son Fiyat (TL)": float(p.close_price) if p.close_price else None,
                "Son Pozisyon Değeri (TL)": float(p.position_value) if p.position_value else None,
                "K/Z (TL)": float(p.unrealized_pnl_tl) if p.unrealized_pnl_tl else None,
                "K/Z (%)": self._format_pct(p.unrealized_pnl_pct),
                "Toplam Gün Sayısı": stock_days_count[ticker]
            })
        
        df = pd.DataFrame.from_records(records)
        if not df.empty:
            df = df.sort_values("Hisse").reset_index(drop=True)
        return df

    def _build_summary_df(self, snapshots: Iterable[DailyPortfolioSnapshot]) -> pd.DataFrame:
        records = []
        for s in snapshots:
            if s.status == "Hafta Sonu":
                continue

            records.append({
                "Tarih": s.date,
                "Portföy Değeri (TL)": float(s.total_value) if s.total_value else None,
                "Günlük Getiri (%)": self._format_pct(s.daily_return_pct),
                "Toplam Getiri (%)": self._format_pct(s.cumulative_return_pct),
                "Günlük K/Z (TL)": float(s.daily_pnl) if s.daily_pnl else None,
                "Toplam K/Z (TL)": float(s.cumulative_pnl) if s.cumulative_pnl else None,
            })
        df = pd.DataFrame.from_records(records)
        if not df.empty:
            df = df.sort_values("Tarih").reset_index(drop=True)
        return df

    def _write_fresh_excel(self, file_path: Path, summary_df: pd.DataFrame, detail_df: pd.DataFrame, 
                          stock_summary_df: pd.DataFrame, dashboard_df: pd.DataFrame) -> None:
        try:
            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                dashboard_df.to_excel(writer, sheet_name="Özet Panel", index=False)
                summary_df.to_excel(writer, sheet_name="Portföy Özeti", index=False)
                detail_df.to_excel(writer, sheet_name="Günlük Detaylar", index=False)
                stock_summary_df.to_excel(writer, sheet_name="Hisse Özeti", index=False)
                
                self.formatter.apply_formatting(writer, "Özet Panel", dashboard_df)
                self.formatter.apply_formatting(writer, "Portföy Özeti", summary_df)
                self.formatter.apply_formatting(writer, "Günlük Detaylar", detail_df)
                self.formatter.apply_formatting(writer, "Hisse Özeti", stock_summary_df)
                
        except PermissionError:
            raise PermissionError(f"Dosyaya yazılamadı: {file_path}\nDosya açık olabilir. Lütfen kapatıp tekrar deneyin.")

    def _append_to_existing_excel(self, file_path: Path, summary_df: pd.DataFrame, detail_df: pd.DataFrame,
                                  stock_summary_df: pd.DataFrame, dashboard_df: pd.DataFrame) -> None:
        try:
            with open(file_path, "r+"):
                pass
        except PermissionError:
            raise PermissionError(f"Dosya şu an açık: {file_path.name}\nLütfen Excel dosyasını kapatıp tekrar deneyin.")
        except Exception:
            pass

        try:
            with pd.ExcelFile(file_path, engine='openpyxl') as xls:
                sheet_names = xls.sheet_names
                
                existing_summary = pd.read_excel(xls, sheet_name="Portföy Özeti") if "Portföy Özeti" in sheet_names else pd.DataFrame()
                existing_detail = pd.read_excel(xls, sheet_name="Günlük Detaylar") if "Günlük Detaylar" in sheet_names else pd.DataFrame()
                existing_stock_sum = pd.read_excel(xls, sheet_name="Hisse Özeti") if "Hisse Özeti" in sheet_names else pd.DataFrame()
        except Exception as e:
            logger.warning(f"Eski dosya okunamadı: {e}. Dosya yedeklenip yeniden oluşturulacak.")
            backup_path = file_path.with_suffix(file_path.suffix + ".bak")
            shutil.copy(file_path, backup_path)
            self._write_fresh_excel(file_path, summary_df, detail_df, stock_summary_df, dashboard_df)
            return

        combined_summary = pd.concat([existing_summary, summary_df], ignore_index=True)
        if not combined_summary.empty and "Tarih" in combined_summary.columns:
            combined_summary = combined_summary.drop_duplicates(subset=["Tarih"], keep="last").sort_values("Tarih").reset_index(drop=True)

        combined_detail = pd.concat([existing_detail, detail_df], ignore_index=True)
        if not combined_detail.empty and "Tarih" in combined_detail.columns and "Hisse" in combined_detail.columns:
            combined_detail = combined_detail.drop_duplicates(subset=["Tarih", "Hisse"], keep="last").sort_values(["Tarih", "Hisse"]).reset_index(drop=True)
            
        combined_stock_sum = pd.concat([existing_stock_sum, stock_summary_df], ignore_index=True)
        if not combined_stock_sum.empty and "Hisse" in combined_stock_sum.columns:
            combined_stock_sum = combined_stock_sum.drop_duplicates(subset=["Hisse"], keep="last").sort_values("Hisse").reset_index(drop=True)
        
        try:
            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                dashboard_df.to_excel(writer, sheet_name="Özet Panel", index=False)
                combined_summary.to_excel(writer, sheet_name="Portföy Özeti", index=False)
                combined_detail.to_excel(writer, sheet_name="Günlük Detaylar", index=False)
                combined_stock_sum.to_excel(writer, sheet_name="Hisse Özeti", index=False)
                
                self.formatter.apply_formatting(writer, "Özet Panel", dashboard_df)
                self.formatter.apply_formatting(writer, "Portföy Özeti", combined_summary)
                self.formatter.apply_formatting(writer, "Günlük Detaylar", combined_detail)
                self.formatter.apply_formatting(writer, "Hisse Özeti", combined_stock_sum)
        except PermissionError:
            raise PermissionError(f"Dosyaya yazılamadı: {file_path}\nDosya açık olabilir. Lütfen kapatıp tekrar deneyin.")
