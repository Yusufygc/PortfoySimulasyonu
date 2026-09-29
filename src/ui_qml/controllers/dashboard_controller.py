"""
Dashboard Controller — Portföy KPI'ları, varlık dağılımı, canlı fiyat akışı ve işlem yönetimini sağlar.
"""
from __future__ import annotations

import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, Any, List

from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer
from src.ui_qml.models.positions_table_model import PositionsTableModel

logger = logging.getLogger(__name__)


class DashboardController(QObject):
    kpisChanged = Signal()
    refreshStateChanged = Signal(bool)
    tradeExecuted = Signal(bool, str)   # success, message
    capitalUpdated = Signal(bool, str)  # success, message

    def __init__(self, container=None, parent=None):
        super().__init__(parent)
        self._container = container
        self._positions_model = PositionsTableModel(self)

        # Temel Portföy Durum Değişkenleri
        self._capital: Decimal = Decimal("185000.00")
        self._total_value: Decimal = Decimal("0")
        self._total_cost: Decimal = Decimal("0")
        self._total_pl: Decimal = Decimal("0")
        self._daily_pl: Decimal = Decimal("0")
        self._is_refreshing: bool = False

        # Hazır/Gerçekçi başlangıç pozisyon havuzu
        self._initial_positions = [
            {"ticker": "THYAO", "companyName": "Türk Hava Yolları",   "quantity": 1250, "avgCost": 264.50, "currentPrice": 294.25, "dailyDiff": 2.15},
            {"ticker": "GARAN", "companyName": "Garanti Bankası",     "quantity": 2800, "avgCost": 98.20,  "currentPrice": 118.40, "dailyDiff": 1.45},
            {"ticker": "ASELS", "companyName": "Aselsan Elektronik",  "quantity": 3500, "avgCost": 62.10,  "currentPrice": 59.80,  "dailyDiff": -0.80},
            {"ticker": "KCHOL", "companyName": "Koç Holding",         "quantity": 1500, "avgCost": 182.00, "currentPrice": 215.50, "dailyDiff": 3.10},
            {"ticker": "TUPRS", "companyName": "Tüpraş Rafinerileri", "quantity": 1800, "avgCost": 142.50, "currentPrice": 164.20, "dailyDiff": 0.90},
            {"ticker": "SISE",  "companyName": "Şişecam Cam Sanayi",  "quantity": 4200, "avgCost": 48.30,  "currentPrice": 46.90,  "dailyDiff": -1.20},
            {"ticker": "BIMAS", "companyName": "BİM Mağazalar",       "quantity": 600,  "avgCost": 440.00, "currentPrice": 512.00, "dailyDiff": 1.80},
            {"ticker": "FROTO", "companyName": "Ford Otomotiv",       "quantity": 300,  "avgCost": 920.00, "currentPrice": 1045.00,"dailyDiff": 2.45},
        ]

        # Event bus bağlantısı
        if self._container and hasattr(self._container, "event_bus") and self._container.event_bus:
            try:
                self._container.event_bus.prices_updated.connect(self._on_eventbus_prices_updated)
            except Exception as exc:
                logger.warning("EventBus bağlantı hatası: %s", exc)

        self._load_portfolio_data()

    # --- Properties ---

    @Property(QObject, constant=True)
    def positionsModel(self) -> PositionsTableModel:
        return self._positions_model

    @Property(str, notify=kpisChanged)
    def totalValue(self) -> str:
        return f"₺{self._total_value:,.2f}"

    @Property(str, notify=kpisChanged)
    def totalCost(self) -> str:
        return f"₺{self._total_cost:,.2f}"

    @Property(str, notify=kpisChanged)
    def cashBalance(self) -> str:
        return f"₺{self._capital:,.2f}"

    @Property(str, notify=kpisChanged)
    def cashRatio(self) -> str:
        if self._total_value > 0:
            ratio = (self._capital / self._total_value) * 100
            return f"%{ratio:.1f}"
        return "%0.0"

    @Property(str, notify=kpisChanged)
    def dailyGainLoss(self) -> str:
        sign = "+" if self._daily_pl >= 0 else ""
        return f"{sign}₺{self._daily_pl:,.2f}"

    @Property(str, notify=kpisChanged)
    def dailyGainLossPct(self) -> str:
        if self._total_value > 0:
            pct = (self._daily_pl / self._total_value) * 100
            sign = "+" if pct >= 0 else ""
            return f"{sign}%{pct:.2f}"
        return "%0.00"

    @Property(bool, notify=kpisChanged)
    def isDailyPositive(self) -> bool:
        return self._daily_pl >= 0

    @Property(str, notify=kpisChanged)
    def totalGainLoss(self) -> str:
        sign = "+" if self._total_pl >= 0 else ""
        return f"{sign}₺{self._total_pl:,.2f}"

    @Property(str, notify=kpisChanged)
    def totalGainLossPct(self) -> str:
        if self._total_cost > 0:
            pct = (self._total_pl / self._total_cost) * 100
            sign = "+" if pct >= 0 else ""
            return f"{sign}%{pct:.2f}"
        return "%0.00"

    @Property(bool, notify=kpisChanged)
    def isTotalPositive(self) -> bool:
        return self._total_pl >= 0

    @Property(int, notify=kpisChanged)
    def holdingsCount(self) -> int:
        return self._positions_model.rowCount()

    @Property(bool, notify=refreshStateChanged)
    def isRefreshing(self) -> bool:
        return self._is_refreshing

    # --- Veri Yükleme ve Hesaplama ---

    def _load_portfolio_data(self) -> None:
        """Gerçek servislerden veya gerçekçi simülasyondan verileri yükler."""
        connected_to_db = False
        if self._container:
            try:
                if hasattr(self._container, "portfolio_service") and hasattr(self._container, "stock_repo"):
                    cash = self._container.portfolio_service.get_cash_balance()
                    if cash is not None:
                        self._capital = Decimal(str(cash))
                    connected_to_db = True
            except Exception as exc:
                logger.info("Canlı DB erişimi sağlanamadı, offline mod aktif: %s", exc)

        # Pozisyon verilerini ve türev değerleri hesapla
        pos_list = []
        stocks_market_val = Decimal("0")
        total_cost = Decimal("0")
        daily_gain = Decimal("0")

        for item in self._initial_positions:
            qty = Decimal(str(item["quantity"]))
            cost = Decimal(str(item["avgCost"]))
            price = Decimal(str(item["currentPrice"]))
            diff_pct = Decimal(str(item["dailyDiff"]))

            m_val = qty * price
            tot_c = qty * cost
            pl = m_val - tot_c
            pl_pct = (pl / tot_c * 100) if tot_c > 0 else Decimal("0")
            day_gain = m_val * (diff_pct / Decimal("100"))

            stocks_market_val += m_val
            total_cost += tot_c
            daily_gain += day_gain

            pos_list.append({
                "ticker": item["ticker"],
                "companyName": item["companyName"],
                "quantity": int(qty),
                "avgCost": float(cost),
                "currentPrice": float(price),
                "dailyDiff": float(diff_pct),
                "marketValue": float(m_val),
                "unrealizedPL": float(pl),
                "unrealizedPLPct": float(pl_pct),
                "weight": 0.0,  # aşağıda hesaplanacak
                "isUp": pl >= 0,
                "flashState": 0,
            })

        self._total_value = stocks_market_val + self._capital
        self._total_cost = total_cost
        self._total_pl = stocks_market_val - total_cost
        self._daily_pl = daily_gain

        # Ağırlıkları normalize et
        for p in pos_list:
            if self._total_value > 0:
                p["weight"] = (Decimal(str(p["marketValue"])) / self._total_value) * 100

        self._positions_model.set_positions(pos_list)
        self.kpisChanged.emit()

    # --- Slots ---

    @Slot()
    def refreshMetrics(self) -> None:
        """Piyasa fiyatlarını arka planda yeniler."""
        self._is_refreshing = True
        self.refreshStateChanged.emit(True)

        # Fiyat simülasyonu / YFinance çekimi
        def do_refresh():
            price_map = {}
            import numpy as np
            for p in self._initial_positions:
                old_p = float(p["currentPrice"])
                change = np.random.normal(0.002, 0.015)
                new_p = round(old_p * (1 + change), 2)
                p["currentPrice"] = new_p
                price_map[p["ticker"]] = new_p

            self._positions_model.update_prices(price_map)
            self._load_portfolio_data()
            self._is_refreshing = False
            self.refreshStateChanged.emit(False)

        QTimer.singleShot(800, do_refresh)

    @Slot(str, str, int, float, str)
    def submitTrade(self, ticker: str, side: str, quantity: int, price: float, notes: str) -> None:
        """Al/Sat işlemini kaydeder ve portföyü günceller."""
        ticker = ticker.strip().upper()
        if not ticker or quantity <= 0 or price <= 0:
            self.tradeExecuted.emit(False, "Geçersiz işlem parametreleri.")
            return

        total_amount = Decimal(str(quantity)) * Decimal(str(price))

        if side.upper() == "BUY":
            if self._capital < total_amount:
                self.tradeExecuted.emit(False, f"Yetersiz nakit! Gerekli: ₺{total_amount:,.2f}, Mevcut: ₺{self._capital:,.2f}")
                return
            self._capital -= total_amount
            # Pozisyona ekle veya yeni aç
            found = False
            for p in self._initial_positions:
                if p["ticker"] == ticker:
                    curr_qty = Decimal(str(p["quantity"]))
                    curr_cost = Decimal(str(p["avgCost"]))
                    new_qty = curr_qty + Decimal(str(quantity))
                    new_cost = ((curr_qty * curr_cost) + total_amount) / new_qty
                    p["quantity"] = int(new_qty)
                    p["avgCost"] = float(round(new_cost, 2))
                    p["currentPrice"] = price
                    found = True
                    break
            if not found:
                self._initial_positions.append({
                    "ticker": ticker,
                    "companyName": f"{ticker} Hissesi",
                    "quantity": quantity,
                    "avgCost": price,
                    "currentPrice": price,
                    "dailyDiff": 0.0,
                })
            msg = f"{quantity} adet {ticker} başarıyla satın alındı (₺{total_amount:,.2f})."
        else: # SELL
            # Pozisyon kontrolü
            target = next((p for p in self._initial_positions if p["ticker"] == ticker), None)
            if not target or target["quantity"] < quantity:
                self.tradeExecuted.emit(False, f"Satış için yetersiz lot! Mevcut: {target['quantity'] if target else 0}")
                return
            target["quantity"] -= quantity
            self._capital += total_amount
            if target["quantity"] == 0:
                self._initial_positions.remove(target)
            msg = f"{quantity} adet {ticker} başarıyla satıldı (₺{total_amount:,.2f})."

        self._load_portfolio_data()
        self.tradeExecuted.emit(True, msg)

    @Slot(str, float, str)
    def manageCapital(self, action: str, amount: float, note: str) -> None:
        """Sermaye yatırma veya çekme işlemi gerçekleştirir."""
        if amount <= 0:
            self.capitalUpdated.emit(False, "Tutar 0'dan büyük olmalıdır.")
            return

        dec_amount = Decimal(str(amount))
        if action.lower() == "deposit":
            self._capital += dec_amount
            msg = f"₺{dec_amount:,.2f} nakit portföye yatırıldı."
        else:
            if self._capital < dec_amount:
                self.capitalUpdated.emit(False, "Yetersiz nakit bakiye.")
                return
            self._capital -= dec_amount
            msg = f"₺{dec_amount:,.2f} nakit portföyden çekildi."

        self._load_portfolio_data()
        self.capitalUpdated.emit(True, msg)

    def _on_eventbus_prices_updated(self, prices_dict: Dict[int, Decimal]) -> None:
        """EventBus'tan gelen fiyat güncellemesini işler."""
        logger.info("EventBus fiyat guncellemesi alindi: %d hisse", len(prices_dict))
        self.refreshMetrics()
