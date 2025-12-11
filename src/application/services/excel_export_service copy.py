# src/application/services/excel_export_service.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Iterable, Union
import shutil # Dosya yedekleme için

import pandas as pd

# Domain importları
from src.domain.models.daily_price import DailyPrice
from src.domain.repositories.portfolio_repository import IPortfolioRepository
from src.domain.repositories.price_repository import IPriceRepository
from src.domain.repositories.stock_repository import IStockRepository
from src.domain.services_interfaces.i_market_data_client import IMarketDataClient


class ExportMode(str, Enum):
    OVERWRITE = "overwrite"
    APPEND = "append"


@dataclass
class DailyPosition:
    date: date
    ticker: str
    quantity: int
    avg_cost: Decimal
    cost_basis: Decimal
    close_price: Optional[Decimal]
    position_value: Optional[Decimal]
    daily_price_change_pct: Optional[Decimal]
    unrealized_pnl_tl: Optional[Decimal]
    unrealized_pnl_pct: Optional[Decimal]
    weight_pct: Optional[Decimal]


@dataclass
class DailyPortfolioSnapshot:
    date: date
    total_value: Optional[Decimal]
    daily_return_pct: Optional[Decimal]
    cumulative_return_pct: Optional[Decimal]
    daily_pnl: Optional[Decimal]
    cumulative_pnl: Optional[Decimal]
    status: str


class ExcelExportService:
    def __init__(
        self,
        portfolio_repo: IPortfolioRepository,
        price_repo: IPriceRepository,
        stock_repo: IStockRepository,
        market_data_client: IMarketDataClient,
    ) -> None:
        self.portfolio_repo = portfolio_repo
        self.price_repo = price_repo
        self.stock_repo = stock_repo
        self.market_data_client = market_data_client

    def export_history(
        self,
        start_date: date,
        end_date: date,
        file_path: Union[str, Path],
        mode: ExportMode = ExportMode.OVERWRITE,
    ) -> None:
        file_path = Path(file_path)
        
        # 1. Veriyi Hazırla
        daily_positions, daily_snapshots = self._build_daily_history(start_date, end_date)
        
        # 2. DataFrame'leri Oluştur
        detail_df = self._build_detail_df(daily_positions, daily_snapshots)
        summary_df = self._build_summary_df(daily_snapshots)
        stock_summary_df = self._build_stock_summary_df(daily_positions)

        # 3. Yazma İşlemi
        # Eğer dosya yoksa, mod ne olursa olsun taze yaz
        if not file_path.exists():
            self._write_fresh_excel(file_path, summary_df, detail_df, stock_summary_df)
            return

        if mode == ExportMode.OVERWRITE:
            self._write_fresh_excel(file_path, summary_df, detail_df, stock_summary_df)
        else:
            self._append_to_existing_excel(file_path, summary_df, detail_df, stock_summary_df)

    def _build_daily_history(self, start_date: date, end_date: date):
        if end_date < start_date:
            start_date, end_date = end_date, start_date

        all_trades = self.portfolio_repo.get_all_trades()
        relevant_trades = [t for t in all_trades if t.trade_date <= end_date]

        if not relevant_trades:
            return [], []

        from datetime import time as dt_time
        relevant_trades.sort(key=lambda t: (t.trade_date, getattr(t, "trade_time", None) or dt_time.min))

        stocks = self.stock_repo.get_all_stocks()
        ticker_map = {s.id: s.ticker for s in stocks}

        positions_state = {}
        trade_idx = 0
        n_trades = len(relevant_trades)

        daily_positions = []
        daily_snapshots = []
        last_close_by_stock = {}
        last_portfolio_value = None
        base_portfolio_value = None

        cur = start_date
        while cur <= end_date:
            # 1. İşlemleri Uygula
            while trade_idx < n_trades and relevant_trades[trade_idx].trade_date <= cur:
                t = relevant_trades[trade_idx]
                stock_id = t.stock_id
                qty = int(t.quantity)
                price = Decimal(str(t.price))

                if stock_id not in positions_state:
                    positions_state[stock_id] = {"qty": Decimal("0"), "total_cost": Decimal("0")}

                state = positions_state[stock_id]
                cur_qty = state["qty"]
                
                if t.side == "BUY":
                    state["qty"] += Decimal(qty)
                    state["total_cost"] += (Decimal(qty) * price)
                elif t.side == "SELL":
                    avg_cost = (state["total_cost"] / cur_qty) if cur_qty != 0 else Decimal("0")
                    sell_qty = min(Decimal(qty), cur_qty)
                    state["qty"] -= sell_qty
                    state["total_cost"] -= (avg_cost * sell_qty)
                    if state["qty"] == 0:
                        state["total_cost"] = Decimal("0")
                
                trade_idx += 1

            # 2. Fiyatları Çek (Eksikse Tamamla)
            active_stock_ids = [sid for sid, st in positions_state.items() if st["qty"] > 0]
            prices_for_day = self.price_repo.get_prices_for_date(cur)
            
            is_weekend = cur.weekday() >= 5
            if not is_weekend and active_stock_ids:
                missing_ids = [sid for sid in active_stock_ids if sid not in prices_for_day]
                if missing_ids:
                    missing_tickers = [ticker_map.get(sid) for sid in missing_ids if sid in ticker_map]
                    if missing_tickers:
                        try:
                            fetched_prices = self.market_data_client.get_closing_prices(
                                stock_ids=missing_ids, tickers=missing_tickers, price_date=cur
                            )
                            new_daily_prices = []
                            for sid, price in fetched_prices.items():
                                prices_for_day[sid] = price
                                new_daily_prices.append(DailyPrice(
                                    id=None, stock_id=sid, price_date=cur, close_price=price
                                ))
                            if new_daily_prices:
                                self.price_repo.upsert_daily_prices_bulk(new_daily_prices)
                        except Exception:
                            pass

            # 3. Hesaplamalar
            has_prices = bool(prices_for_day)
            day_positions_list = []
            portfolio_value = None

            if has_prices:
                total_value = Decimal("0")
                temp_positions = []

                for stock_id, state in positions_state.items():
                    qty = int(state["qty"])
                    if qty <= 0: continue

                    avg_cost = (state["total_cost"] / state["qty"]) if state["qty"] != 0 else Decimal("0")
                    cost_basis = avg_cost * Decimal(qty)
                    
                    close_price = prices_for_day.get(stock_id)

                    if close_price:
                        pos_val = Decimal(qty) * close_price
                        total_value += pos_val
                        
                        last_c = last_close_by_stock.get(stock_id)
                        daily_chg = ((close_price / last_c) - 1) if (last_c and last_c != 0) else None
                        
                        unrealized_tl = (close_price - avg_cost) * Decimal(qty)
                        unrealized_pct = (unrealized_tl / cost_basis) if cost_basis != 0 else None
                    else:
                        pos_val, daily_chg, unrealized_tl, unrealized_pct = None, None, None, None

                    temp_positions.append({
                        "ticker": ticker_map.get(stock_id, f"ID_{stock_id}"),
                        "qty": qty,
                        "avg_cost": avg_cost,
                        "cost_basis": cost_basis,
                        "close_price": close_price,
                        "pos_val": pos_val,
                        "daily_chg": daily_chg,
                        "unr_tl": unrealized_tl,
                        "unr_pct": unrealized_pct
                    })

                for tmp in temp_positions:
                    w_pct = (tmp["pos_val"] / total_value) if (tmp["pos_val"] and total_value) else None
                    day_positions_list.append(DailyPosition(
                        date=cur,
                        ticker=tmp["ticker"],
                        quantity=tmp["qty"],
                        avg_cost=tmp["avg_cost"],
                        cost_basis=tmp["cost_basis"],
                        close_price=tmp["close_price"],
                        position_value=tmp["pos_val"],
                        daily_price_change_pct=tmp["daily_chg"],
                        unrealized_pnl_tl=tmp["unr_tl"],
                        unrealized_pnl_pct=tmp["unr_pct"],
                        weight_pct=w_pct
                    ))
                
                if total_value > 0:
                    portfolio_value = total_value
                    last_close_by_stock = prices_for_day.copy()
            else:
                portfolio_value = last_portfolio_value if last_portfolio_value else None

            # Getiri hesapları
            daily_pnl, daily_ret, cum_pnl, cum_ret = None, None, None, None
            if portfolio_value:
                if not base_portfolio_value: base_portfolio_value = portfolio_value
                
                if last_portfolio_value:
                    daily_pnl = portfolio_value - last_portfolio_value
                    daily_ret = (daily_pnl / last_portfolio_value) if last_portfolio_value else None
                
                if base_portfolio_value:
                    cum_pnl = portfolio_value - base_portfolio_value
                    cum_ret = (cum_pnl / base_portfolio_value) if base_portfolio_value else None

            status = "Normal" if has_prices else ("Hafta Sonu" if is_weekend else "Veri Yok")
            
            if day_positions_list:
                daily_positions.extend(day_positions_list)
            
            daily_snapshots.append(DailyPortfolioSnapshot(
                date=cur, total_value=portfolio_value, 
                daily_return_pct=daily_ret, cumulative_return_pct=cum_ret,
                daily_pnl=daily_pnl, cumulative_pnl=cum_pnl, status=status
            ))

            if portfolio_value: last_portfolio_value = portfolio_value
            cur += timedelta(days=1)

        return daily_positions, daily_snapshots

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
                    "Ticker": p.ticker,
                    "Lot": p.quantity,
                    "Ortalama Maliyet": float(p.avg_cost),
                    "Güncel Fiyat": float(p.close_price) if p.close_price else None,
                    "Pozisyon Değeri": float(p.position_value) if p.position_value else None,
                    "Maliyet Esası": float(p.cost_basis),
                    "Günlük Fiyat Değişim %": float(p.daily_price_change_pct) if p.daily_price_change_pct else None,
                    "Gerç. Olmayan K/Z (TL)": float(p.unrealized_pnl_tl) if p.unrealized_pnl_tl else None,
                    "Gerç. Olmayan K/Z %": float(p.unrealized_pnl_pct) if p.unrealized_pnl_pct else None,
                    "Portföy Ağırlığı %": float(p.weight_pct) if p.weight_pct else None,
                })
                
                if p.cost_basis: total_cost_basis += p.cost_basis
                if p.position_value: total_position_value += p.position_value
                if p.unrealized_pnl_tl: total_unrealized_pnl_tl += p.unrealized_pnl_tl

            snapshot = snapshot_map.get(d)
            total_unrealized_pct = (total_unrealized_pnl_tl / total_cost_basis) if total_cost_basis != 0 else None
            portfolio_daily_ret = snapshot.daily_return_pct if snapshot else None
            
            summary_row = {
                "Tarih": d,
                "Ticker": ">>> GÜNLÜK TOPLAM <<<",
                "Lot": None,
                "Ortalama Maliyet": None,
                "Güncel Fiyat": None,
                "Pozisyon Değeri": float(total_position_value),
                "Maliyet Esası": float(total_cost_basis),
                "Günlük Fiyat Değişim %": float(portfolio_daily_ret) if portfolio_daily_ret is not None else None,
                "Gerç. Olmayan K/Z (TL)": float(total_unrealized_pnl_tl),
                "Gerç. Olmayan K/Z %": float(total_unrealized_pct) if total_unrealized_pct is not None else None,
                "Portföy Ağırlığı %": 1.0,
            }
            records.append(summary_row)

        df = pd.DataFrame.from_records(records)
        cols = [
            "Tarih", "Ticker", "Lot", "Ortalama Maliyet", "Güncel Fiyat", 
            "Pozisyon Değeri", "Maliyet Esası", "Günlük Fiyat Değişim %", 
            "Gerç. Olmayan K/Z (TL)", "Gerç. Olmayan K/Z %", "Portföy Ağırlığı %"
        ]
        if not df.empty:
            df = df[cols]
        return df

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
                "Ticker": ticker,
                "Son Lot": p.quantity,
                "Ort. Maliyet": float(p.avg_cost),
                "Son Fiyat": float(p.close_price) if p.close_price else None,
                "Son Pozisyon Değeri": float(p.position_value) if p.position_value else None,
                "Toplam Gerç.Olmayan K/Z (TL)": float(p.unrealized_pnl_tl) if p.unrealized_pnl_tl else None,
                "Toplam Gerç.Olmayan K/Z %": float(p.unrealized_pnl_pct) if p.unrealized_pnl_pct else None,
                "Gün Sayısı": stock_days_count[ticker]
            })
        
        df = pd.DataFrame.from_records(records)
        if not df.empty:
            df = df.sort_values("Ticker").reset_index(drop=True)
        return df

    def _build_summary_df(self, snapshots: Iterable[DailyPortfolioSnapshot]) -> pd.DataFrame:
        records = []
        for s in snapshots:
            records.append({
                "Tarih": s.date,
                "Portföy Değeri": float(s.total_value) if s.total_value else None,
                "Günlük Getiri %": float(s.daily_return_pct) if s.daily_return_pct else None,
                "Toplam Getiri %": float(s.cumulative_return_pct) if s.cumulative_return_pct else None,
                "Günlük K/Z": float(s.daily_pnl) if s.daily_pnl else None,
                "Toplam K/Z": float(s.cumulative_pnl) if s.cumulative_pnl else None,
                "Durum": s.status,
            })
        df = pd.DataFrame.from_records(records)
        if not df.empty:
            df = df.sort_values("Tarih").reset_index(drop=True)
        return df

    def _write_fresh_excel(self, file_path: Path, summary_df: pd.DataFrame, detail_df: pd.DataFrame, stock_summary_df: pd.DataFrame) -> None:
        try:
            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                detail_df.to_excel(writer, sheet_name="StockDetails", index=False)
                summary_df.to_excel(writer, sheet_name="PortfolioSummary", index=False)
                stock_summary_df.to_excel(writer, sheet_name="StockSummary", index=False)
        except PermissionError:
            raise PermissionError(f"Dosyaya yazılamadı: {file_path}\nDosya açık olabilir. Lütfen kapatıp tekrar deneyin.")

    def _append_to_existing_excel(self, file_path: Path, summary_df: pd.DataFrame, detail_df: pd.DataFrame, stock_summary_df: pd.DataFrame) -> None:
        # GÜVENLİK KONTROLÜ: Dosya açık mı?
        try:
            # Sadece okumayı dene, açıksa hata verir
            with open(file_path, "r+"):
                pass
        except PermissionError:
            raise PermissionError(f"Dosya şu an açık: {file_path.name}\nLütfen Excel dosyasını kapatıp tekrar deneyin.")
        except Exception:
            pass # Dosya yoksa veya başka sorunsa devam et

        try:
            with pd.ExcelFile(file_path, engine='openpyxl') as xls:
                # Sayfaları oku, yoksa boş DataFrame oluştur
                sheet_names = xls.sheet_names
                
                existing_summary = pd.read_excel(xls, sheet_name="PortfolioSummary") if "PortfolioSummary" in sheet_names else pd.DataFrame()
                existing_detail = pd.read_excel(xls, sheet_name="StockDetails") if "StockDetails" in sheet_names else pd.DataFrame()
                existing_stock_sum = pd.read_excel(xls, sheet_name="StockSummary") if "StockSummary" in sheet_names else pd.DataFrame()
        except Exception as e:
            # Dosya bozuksa veya format çok eskiyse
            print(f"Eski dosya okunamadı: {e}. Dosya yedeklenip yeniden oluşturulacak.")
            backup_path = file_path.with_suffix(file_path.suffix + ".bak")
            shutil.copy(file_path, backup_path)
            self._write_fresh_excel(file_path, summary_df, detail_df, stock_summary_df)
            return

        # BİRLEŞTİRME VE TEMİZLEME
        
        # 1. Özet Tablo
        combined_summary = pd.concat([existing_summary, summary_df], ignore_index=True)
        if not combined_summary.empty and "Tarih" in combined_summary.columns:
            # Tarihe göre tekrar edenleri sil (son ekleneni tut)
            combined_summary = combined_summary.drop_duplicates(subset=["Tarih"], keep="last").sort_values("Tarih").reset_index(drop=True)

        # 2. Detay Tablo
        combined_detail = pd.concat([existing_detail, detail_df], ignore_index=True)
        if not combined_detail.empty and "Tarih" in combined_detail.columns and "Ticker" in combined_detail.columns:
            # Aynı gün aynı hisse için çift kaydı önle
            # Not: ">>> GÜNLÜK TOPLAM <<<" satırları da Ticker olduğu için mantık bozulmaz
            combined_detail = combined_detail.drop_duplicates(subset=["Tarih", "Ticker"], keep="last").sort_values(["Tarih", "Ticker"]).reset_index(drop=True)
            
        # 3. Hisse Özet Tablosu
        combined_stock_sum = pd.concat([existing_stock_sum, stock_summary_df], ignore_index=True)
        if not combined_stock_sum.empty and "Ticker" in combined_stock_sum.columns:
            combined_stock_sum = combined_stock_sum.drop_duplicates(subset=["Ticker"], keep="last").sort_values("Ticker").reset_index(drop=True)

        # 4. DOSYAYA YAZ
        try:
            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                combined_detail.to_excel(writer, sheet_name="StockDetails", index=False)
                combined_summary.to_excel(writer, sheet_name="PortfolioSummary", index=False)
                combined_stock_sum.to_excel(writer, sheet_name="StockSummary", index=False)
        except PermissionError:
             raise PermissionError(f"Dosyaya yazılamadı: {file_path}\nDosya açık olabilir. Lütfen kapatıp tekrar deneyin.")