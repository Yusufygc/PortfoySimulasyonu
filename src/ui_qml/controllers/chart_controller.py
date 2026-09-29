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
        if self._container and hasattr(self._container, "stock_repo") and hasattr(self._container, "price_repo"):
            try:
                stock = None
                # Ticker alternatiflerini dene (örn. GARAN veya GARAN.IS)
                for candidate in [ticker, f"{ticker}.IS", ticker.replace(".IS", "")]:
                    stock = self._container.stock_repo.get_stock_by_ticker(candidate)
                    if stock:
                        break

                if stock:
                    start_date = datetime.now().date() - timedelta(days=365)
                    end_date = datetime.now().date()
                    prices = self._container.price_repo.get_price_series(stock.id, start_date, end_date)
                    if prices:
                        for p in prices:
                            dt_str = p.price_date.strftime("%Y-%m-%d")
                            o = float(p.open_price if p.open_price is not None else p.close_price)
                            h = float(p.high_price if p.high_price is not None else p.close_price)
                            l = float(p.low_price if p.low_price is not None else p.close_price)
                            c = float(p.close_price)
                            v = float(p.volume if p.volume is not None else 100000)
                            candles.append({
                                "time": dt_str,
                                "open": o,
                                "high": h,
                                "low": l,
                                "close": c,
                            })
                            volumes.append({
                                "time": dt_str,
                                "value": v,
                                "color": "rgba(8, 153, 129, 0.4)" if c >= o else "rgba(242, 54, 69, 0.4)",
                            })
                        # TradingView kesinlikle artan tarih sıralaması ister
                        candles.sort(key=lambda x: x["time"])
                        volumes.sort(key=lambda x: x["time"])
                        data_found = True
                        logger.info("SQLite'tan %s icin %d adet mum verisi yuklendi.", ticker, len(candles))
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
