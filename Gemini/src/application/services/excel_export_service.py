# src/application/services/excel_export_service.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Iterable, Union

import pandas as pd

from src.domain.models.portfolio import Portfolio
from src.domain.models.position import Position
from src.domain.models.trade import Trade
from src.domain.models.stock import Stock
from src.domain.repositories.portfolio_repository import IPortfolioRepository
from src.domain.repositories.price_repository import IPriceRepository
from src.domain.repositories.stock_repository import IStockRepository


class ExportMode(str, Enum):
    """Excel çıktı davranışı."""
    OVERWRITE = "overwrite"  # Dosyayı komple baştan yaz
    APPEND = "append"        # Var olan dosyaya yeni satırları ekle / güncelle


@dataclass
class DailyPosition:
    date: date
    ticker: str
    stock_id: int
    quantity: int
    avg_cost: Decimal

    # Fiyat / değer
    close_price: Optional[Decimal]           # o günün kapanış fiyatı
    position_value: Optional[Decimal]        # qty * close_price

    # Performans metrikleri
    daily_price_change_pct: Optional[Decimal]  # d-1 kapanışına göre fiyat değişimi
    unrealized_pnl_tl: Optional[Decimal]       # (close - avg_cost) * qty
    unrealized_pnl_pct: Optional[Decimal]      # unrealized_pnl_tl / (avg_cost * qty)
    weight_pct: Optional[Decimal]              # pozisyon_değeri / portföy_değeri



@dataclass
class DailyPortfolioSnapshot:
    """Belirli bir tarihte portföyün toplam durumu."""
    date: date
    total_value: Optional[Decimal]
    daily_return_pct: Optional[Decimal]
    cumulative_return_pct: Optional[Decimal]
    daily_pnl: Optional[Decimal]
    cumulative_pnl: Optional[Decimal]
    status: str  # Normal / Hafta Sonu / Tatil / Veri Yok vb.


class ExcelExportService:
    """
    Portföy tarihçesini Excel'e aktaran servis.

    - Sheet1: PortfolioSummary (gün bazlı tek satır)
    - Sheet2: PositionsDetail (gün x hisse bazlı çok satır)
    """

    def __init__(
            self,
            portfolio_repo: IPortfolioRepository,
            price_repo: IPriceRepository,
            stock_repo: IStockRepository,
        ) -> None:
            self.portfolio_repo = portfolio_repo
            self.price_repo = price_repo
            self.stock_repo = stock_repo

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def export_history(
        self,
        start_date: date,
        end_date: date,
        file_path: Union[str, Path],
        mode: ExportMode = ExportMode.OVERWRITE,
    ) -> None:
        """
        Belirli bir tarih aralığındaki portföy tarihçesini Excel'e yazar.

        :param start_date: Dahil başlangıç günü
        :param end_date: Dahil bitiş günü
        :param file_path: Oluşturulacak / güncellenecek Excel dosyasının yolu
        :param mode: OVERWRITE = dosyayı baştan yaz, APPEND = var olana ekle
        """
        file_path = Path(file_path)

        # 1) DB'den gerekli veriyi çek ve günlük snapshot'ları oluştur
        daily_positions, daily_snapshots = self._build_daily_history(
            start_date=start_date,
            end_date=end_date,
        )

        # 2) pandas DataFrame'lerine dönüştür
        summary_df = self._build_summary_df(daily_snapshots)
        detail_df = self._build_detail_df(daily_positions)

        # 3) Excel'e yaz / ekle
        if mode == ExportMode.OVERWRITE or not file_path.exists():
            self._write_fresh_excel(file_path, summary_df, detail_df)
        else:
            self._append_to_existing_excel(file_path, summary_df, detail_df)

    # ------------------------------------------------------------------
    # INTERNAL: tarihçeyi hesaplama
    # ------------------------------------------------------------------

    def _build_daily_history(
        self,
        start_date: date,
        end_date: date,
    ) -> tuple[List[DailyPosition], List[DailyPortfolioSnapshot]]:
        """
        DB'deki trades + daily_prices'tan günlük pozisyonları ve portföy
        snapshot'larını üretir.

        Mantık:
        - Tüm işlemleri al, tarih/saat'e göre sırala.
        - start_date..end_date aralığında gün gün ilerle.
        - O güne kadar olan işlemleri pozisyon durumuna uygula.
        - price_repo.get_prices_for_date(gün) ile kapanış fiyatlarını çek.
        - Eğer fiyat varsa: portföy değerini hesapla, günlük & toplam getiri çıkar.
        - Eğer fiyat yoksa ama daha önce değer varsa: son değeri taşı,
          status alanına "Piyasa Kapalı (...)" yaz.
        """

        # --- 0) Hazırlık: tarih aralığı guard ---
        if end_date < start_date:
            start_date, end_date = end_date, start_date

        # --- 1) Tüm işlemleri al ve filtrele / sırala ---
        all_trades: List[Trade] = self.portfolio_repo.get_all_trades()
        # Sadece end_date'e kadar olan işlemler önemli
        relevant_trades = [t for t in all_trades if t.trade_date <= end_date]

        if not relevant_trades:
            # Hiç işlem yoksa boş dön
            return [], []

        # Tarih + zaman'a göre sırala
        from datetime import time as dt_time

        def _trade_sort_key(t: Trade):
            trade_time = getattr(t, "trade_time", None) or dt_time.min
            return (t.trade_date, trade_time)

        relevant_trades.sort(key=_trade_sort_key)

        # --- 2) Ticker map (stock_id -> ticker) ---
        # get_all_stocks() kullanarak id -> ticker sözlüğü üretelim
        stocks = self.stock_repo.get_all_stocks()
        ticker_map: Dict[int, str] = {s.id: s.ticker for s in stocks}

        # --- 3) Gün gün ilerlerken kullanılacak state'ler ---
        # Pozisyon durumu: stock_id -> {"qty": int, "total_cost": Decimal}
        positions_state: Dict[int, Dict[str, Decimal]] = {}
        trade_idx = 0
        n_trades = len(relevant_trades)

        daily_positions: List[DailyPosition] = []
        daily_snapshots: List[DailyPortfolioSnapshot] = []

        last_close_by_stock: Dict[int, Decimal] = {}
        last_portfolio_value: Optional[Decimal] = None
        base_portfolio_value: Optional[Decimal] = None  # ilk geçerli değer

        # --- 4) Tarih aralığında gün gün ilerle ---
        cur = start_date
        while cur <= end_date:
            # 4.1) Bu güne kadar olan işlemleri uygula
            while trade_idx < n_trades and relevant_trades[trade_idx].trade_date <= cur:
                t = relevant_trades[trade_idx]
                stock_id = t.stock_id
                qty = int(t.quantity)
                price = Decimal(str(t.price))

                if stock_id not in positions_state:
                    positions_state[stock_id] = {
                        "qty": Decimal("0"),
                        "total_cost": Decimal("0"),
                    }

                state = positions_state[stock_id]
                cur_qty = state["qty"]
                cur_cost = state["total_cost"]
                avg_cost = (cur_cost / cur_qty) if cur_qty != 0 else Decimal("0")

                if t.side == "BUY":
                    # Alış: adet ekle, maliyeti artır
                    state["qty"] = cur_qty + Decimal(qty)
                    state["total_cost"] = cur_cost + (Decimal(qty) * price)
                elif t.side == "SELL":
                    # Satış: adet azalt, maliyetten avg_cost * qty düş
                    sell_qty = Decimal(qty)
                    if sell_qty > cur_qty:
                        # Domain tarafında zaten engellenmiş olması lazım ama yine de guard
                        sell_qty = cur_qty

                    state["qty"] = cur_qty - sell_qty
                    state["total_cost"] = cur_cost - (avg_cost * sell_qty)

                    # Eğer pozisyon sıfırlandıysa total_cost'u 0'la
                    if state["qty"] == 0:
                        state["total_cost"] = Decimal("0")
                else:
                    # Bilinmeyen side
                    pass

                trade_idx += 1

            # 4.2) Bugünün fiyatlarını çek
            prices_for_day: Dict[int, Decimal] = self.price_repo.get_prices_for_date(cur)

            is_weekend = cur.weekday() >= 5  # 5=Cumartesi, 6=Pazar
            has_prices = bool(prices_for_day)

            # 4.3) Pozisyonlar ve portföy değeri
            day_positions: List[DailyPosition] = []
            portfolio_value: Optional[Decimal] = None

            if has_prices:
                # Normal işlem günü: önce pozisyon değerlerini hesapla
                temp_positions: List[Dict] = []
                total_value = Decimal("0")

                for stock_id, state in positions_state.items():
                    qty = int(state["qty"])
                    if qty <= 0:
                        continue

                    avg_cost = (state["total_cost"] / state["qty"]) if state["qty"] != 0 else Decimal("0")
                    close_price = prices_for_day.get(stock_id)

                    if close_price is None:
                        position_value = None
                        daily_price_change_pct = None
                        unrealized_pnl_tl = None
                        unrealized_pnl_pct = None
                    else:
                        # Pozisyon değeri
                        position_value = Decimal(qty) * close_price
                        total_value += position_value

                        # Günlük fiyat değişimi (%)
                        last_close = last_close_by_stock.get(stock_id)
                        if last_close is not None and last_close != 0:
                            daily_price_change_pct = (close_price / last_close) - Decimal("1")
                        else:
                            daily_price_change_pct = None

                        # Gerçekleşmemiş K/Z (TL ve %)
                        cost_basis = avg_cost * Decimal(qty)
                        unrealized_pnl_tl = (close_price - avg_cost) * Decimal(qty)
                        if cost_basis != 0:
                            unrealized_pnl_pct = unrealized_pnl_tl / cost_basis
                        else:
                            unrealized_pnl_pct = None

                    ticker = ticker_map.get(stock_id, f"ID_{stock_id}")

                    temp_positions.append(
                        {
                            "stock_id": stock_id,
                            "ticker": ticker,
                            "qty": qty,
                            "avg_cost": avg_cost,
                            "close_price": close_price,
                            "position_value": position_value,
                            "daily_price_change_pct": daily_price_change_pct,
                            "unrealized_pnl_tl": unrealized_pnl_tl,
                            "unrealized_pnl_pct": unrealized_pnl_pct,
                        }
                    )

                # Şimdi ağırlıkları (weight_pct) hesaplayarak DailyPosition objeleri üretelim
                day_positions: List[DailyPosition] = []
                for tmp in temp_positions:
                    position_value = tmp["position_value"]
                    if position_value is not None and total_value != 0:
                        weight_pct = position_value / total_value
                    else:
                        weight_pct = None

                    day_positions.append(
                        DailyPosition(
                            date=cur,
                            ticker=tmp["ticker"],
                            stock_id=tmp["stock_id"],
                            quantity=tmp["qty"],
                            avg_cost=tmp["avg_cost"],
                            close_price=tmp["close_price"],
                            position_value=position_value,
                            daily_price_change_pct=tmp["daily_price_change_pct"],
                            unrealized_pnl_tl=tmp["unrealized_pnl_tl"],
                            unrealized_pnl_pct=tmp["unrealized_pnl_pct"],
                            weight_pct=weight_pct,
                        )
                    )

                portfolio_value = total_value
                last_close_by_stock = prices_for_day.copy()


            else:
                # Fiyat yok: hafta sonu veya tatil / veri yok
                if last_portfolio_value is not None:
                    # Son işlem gününün değerini taşı (carry forward)
                    portfolio_value = last_portfolio_value
                else:
                    portfolio_value = None  # henüz hiç değer oluşmamış

            # 4.4) Günlük & toplam getiri hesapları
            if portfolio_value is not None:
                if base_portfolio_value is None:
                    base_portfolio_value = portfolio_value

                if last_portfolio_value is not None and last_portfolio_value != 0:
                    daily_pnl = portfolio_value - last_portfolio_value
                    daily_return_pct = daily_pnl / last_portfolio_value
                else:
                    daily_pnl = None
                    daily_return_pct = None

                if base_portfolio_value is not None and base_portfolio_value != 0:
                    cumulative_pnl = portfolio_value - base_portfolio_value
                    cumulative_return_pct = cumulative_pnl / base_portfolio_value
                else:
                    cumulative_pnl = None
                    cumulative_return_pct = None
            else:
                daily_pnl = None
                daily_return_pct = None
                cumulative_pnl = None
                cumulative_return_pct = None

            # 4.5) Status metni
            if has_prices:
                status = "Normal"
            else:
                if portfolio_value is None:
                    # hiç değer yok ve fiyat yok
                    status = "Veri Yok / İşlem Yok"
                else:
                    status = "Piyasa Kapalı (Hafta Sonu)" if is_weekend else "Piyasa Kapalı (Tatil / Veri Yok)"

            # 4.6) Snapshot listelerine ekle
            # Detail: sadece fiyat olan günler için pozisyon satırı ekliyoruz
            if day_positions:
                daily_positions.extend(day_positions)

            daily_snapshots.append(
                DailyPortfolioSnapshot(
                    date=cur,
                    total_value=portfolio_value,
                    daily_return_pct=daily_return_pct,
                    cumulative_return_pct=cumulative_return_pct,
                    daily_pnl=daily_pnl,
                    cumulative_pnl=cumulative_pnl,
                    status=status,
                )
            )

            # Son portföy değerini güncelle
            if portfolio_value is not None:
                last_portfolio_value = portfolio_value

            # bir sonraki gün
            cur = cur + timedelta(days=1)

        return daily_positions, daily_snapshots


    # ------------------------------------------------------------------
    # INTERNAL: DataFrame üretimi
    # ------------------------------------------------------------------

    def _build_summary_df(
        self,
        snapshots: Iterable[DailyPortfolioSnapshot],
    ) -> pd.DataFrame:
        """
        PortfolioSummary sheet'i için DataFrame üretir.
        """
        records = []
        for s in snapshots:
            records.append(
                {
                    "Tarih": s.date,
                    "Portföy Değeri": float(s.total_value) if s.total_value is not None else None,
                    "Günlük Getiri %": float(s.daily_return_pct) if s.daily_return_pct is not None else None,
                    "Toplam Getiri %": float(s.cumulative_return_pct) if s.cumulative_return_pct is not None else None,
                    "Günlük K/Z": float(s.daily_pnl) if s.daily_pnl is not None else None,
                    "Toplam K/Z": float(s.cumulative_pnl) if s.cumulative_pnl is not None else None,
                    "Durum": s.status,
                }
            )

        df = pd.DataFrame.from_records(records)
        # Tarihi excel'de düzgün görünsün diye sort + reset index
        if not df.empty:
            df = df.sort_values("Tarih").reset_index(drop=True)
        return df

    def _build_detail_df(
        self,
        positions: Iterable[DailyPosition],
    ) -> pd.DataFrame:
        records = []
        for p in positions:
            records.append(
                {
                    "Tarih": p.date,
                    "Ticker": p.ticker,
                    "Stock ID": p.stock_id,
                    "Lot": p.quantity,
                    "Ortalama Maliyet": float(p.avg_cost),
                    "Kapanış Fiyatı": float(p.close_price) if p.close_price is not None else None,
                    "Pozisyon Değeri": float(p.position_value) if p.position_value is not None else None,
                    "Günlük Fiyat Değişim %": float(p.daily_price_change_pct) if p.daily_price_change_pct is not None else None,
                    "Gerç. Olmayan K/Z (TL)": float(p.unrealized_pnl_tl) if p.unrealized_pnl_tl is not None else None,
                    "Gerç. Olmayan K/Z %": float(p.unrealized_pnl_pct) if p.unrealized_pnl_pct is not None else None,
                    "Portföy Ağırlığı %": float(p.weight_pct) if p.weight_pct is not None else None,
                }
            )

        df = pd.DataFrame.from_records(records)
        if not df.empty:
            df = df.sort_values(["Tarih", "Ticker"]).reset_index(drop=True)
        return df

    # ------------------------------------------------------------------
    # INTERNAL: Excel yazma / ekleme
    # ------------------------------------------------------------------

    def _write_fresh_excel(
        self,
        file_path: Path,
        summary_df: pd.DataFrame,
        detail_df: pd.DataFrame,
    ) -> None:
        """
        Dosyayı komple baştan yazar (varsa üstüne yazar).
        """
        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            summary_df.to_excel(writer, sheet_name="PortfolioSummary", index=False)
            detail_df.to_excel(writer, sheet_name="PositionsDetail", index=False)

    def _append_to_existing_excel(
        self,
        file_path: Path,
        summary_df: pd.DataFrame,
        detail_df: pd.DataFrame,
    ) -> None:
        """
        Var olan Excel dosyasına yeni satırları ekler.

        - Tarih / (Tarih+Ticker) bazında duplicate satırlar varsa
          en son geleni korumak için basit bir birleştirme yapılır.
        """
        # Mevcut dosyayı oku
        try:
            existing_summary = pd.read_excel(file_path, sheet_name="PortfolioSummary")
            existing_detail = pd.read_excel(file_path, sheet_name="PositionsDetail")
        except Exception:
            # Dosya bozuksa veya sheet yoksa, fresh yaz
            self._write_fresh_excel(file_path, summary_df, detail_df)
            return

        # Summary: Tarih bazlı birleştirme
        combined_summary = pd.concat([existing_summary, summary_df], ignore_index=True)
        if not combined_summary.empty:
            combined_summary = (
                combined_summary
                .drop_duplicates(subset=["Tarih"], keep="last")
                .sort_values("Tarih")
                .reset_index(drop=True)
            )

        # Detail: Tarih + Ticker bazlı birleştirme
        combined_detail = pd.concat([existing_detail, detail_df], ignore_index=True)
        if not combined_detail.empty:
            combined_detail = (
                combined_detail
                .drop_duplicates(subset=["Tarih", "Ticker"], keep="last")
                .sort_values(["Tarih", "Ticker"])
                .reset_index(drop=True)
            )

        # Yeniden yaz (ama kullanıcı açısından "append" gibi çalışıyor)
        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            combined_summary.to_excel(writer, sheet_name="PortfolioSummary", index=False)
            combined_detail.to_excel(writer, sheet_name="PositionsDetail", index=False)
