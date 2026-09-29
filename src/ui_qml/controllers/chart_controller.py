"""
Chart Controller — TradingView Lightweight Charts için OHLCV veri köprüsü.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
import numpy as np

from PySide6.QtCore import QObject, Signal, Slot, Property

logger = logging.getLogger(__name__)


class ChartController(QObject):
    chartDataLoaded = Signal(str, str)  # ticker, json_payload
    tickerChanged = Signal(str)

    def __init__(self, container=None, parent=None):
        super().__init__(parent)
        self._container = container
        self._current_ticker: str = "THYAO"

    @Property(str, notify=tickerChanged)
    def currentTicker(self) -> str:
        return self._current_ticker

    @Slot(str)
    def loadTicker(self, ticker: str) -> None:
        ticker = ticker.strip().upper()
        if not ticker:
            return
        self._current_ticker = ticker
        self.tickerChanged.emit(ticker)
        self._fetch_and_emit_chart_data(ticker)

    def _fetch_and_emit_chart_data(self, ticker: str) -> None:
        """
        Gerçek veritabanı veya YFinanceClient üzerinden,
        yoksa demo/gerçekçi OHLCV üreterek TradingView formatında JSON döner.
        """
        candles = []
        volumes = []

        # Eğer container ve repository varsa gerçek veriyi çekmeyi dene
        data_found = False
        if self._container and hasattr(self._container, "daily_price_repo"):
            try:
                repo = self._container.daily_price_repo
                # stock_id veya ticker sorgusu
                prices = repo.get_prices_by_ticker(ticker) if hasattr(repo, "get_prices_by_ticker") else []
                if prices:
                    for p in prices:
                        dt_str = p.date.strftime("%Y-%m-%d")
                        candles.append({
                            "time": dt_str,
                            "open": float(p.open or p.close),
                            "high": float(p.high or p.close),
                            "low": float(p.low or p.close),
                            "close": float(p.close),
                        })
                        volumes.append({
                            "time": dt_str,
                            "value": float(p.volume or 100000),
                            "color": "rgba(8, 153, 129, 0.4)" if (p.close >= (p.open or p.close)) else "rgba(242, 54, 69, 0.4)",
                        })
                    data_found = True
            except Exception as exc:
                logger.warning("Fiyat verisi cekilirken hata: %s", exc)

        # Fallback: Gerçekçi 90 günlük BIST simülasyon serisi
        if not data_found or not candles:
            base_price = 285.0 if "THY" in ticker else (110.0 if "GARAN" in ticker else 150.0)
            today = datetime.now().date()
            np.random.seed(abs(hash(ticker)) % (2**32))

            current_price = base_price
            for i in range(120, -1, -1):
                d = today - timedelta(days=i)
                if d.weekday() >= 5:  # Hafta sonu atla
                    continue
                
                change_pct = np.random.normal(0.001, 0.02)
                o = current_price
                c = o * (1 + change_pct)
                h = max(o, c) * (1 + abs(np.random.normal(0, 0.008)))
                l = min(o, c) * (1 - abs(np.random.normal(0, 0.008)))
                v = int(np.random.uniform(500000, 3500000))
                
                dt_str = d.strftime("%Y-%m-%d")
                candles.append({
                    "time": dt_str,
                    "open": round(o, 2),
                    "high": round(h, 2),
                    "low": round(l, 2),
                    "close": round(c, 2),
                })
                volumes.append({
                    "time": dt_str,
                    "value": v,
                    "color": "rgba(8, 153, 129, 0.4)" if c >= o else "rgba(242, 54, 69, 0.4)",
                })
                current_price = c

        payload = json.dumps({"candles": candles, "volumes": volumes})
        self.chartDataLoaded.emit(ticker, payload)
