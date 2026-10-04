"""
Chart Controller — TradingView Lightweight Charts için gelişmiş OHLCV, çoklu zaman dilimi ve teknik indikatör veri köprüsü.
"""
from __future__ import annotations

import json
import logging
from typing import List, Dict, Any, Optional
import pandas as pd

from PySide6.QtCore import QObject, Signal, Slot, Property

from src.ui_qml.controllers.chart_indicators import calculate_indicators
from src.ui_qml.controllers.chart_candle_sources import (
    demo_candles,
    last_price_summary,
    load_market_history_candles,
    load_price_series_candles,
)

logger = logging.getLogger(__name__)


class ChartController(QObject):
    chartDataLoaded = Signal(str, str)  # ticker, json_payload
    tickerChanged = Signal(str)
    timeframeChanged = Signal(str)
    chartTypeChanged = Signal(str)
    indicatorsChanged = Signal()

    def __init__(self, container=None, parent=None):
        super().__init__(parent)
        self._container = container
        self._current_ticker: str = "THYAO"
        self._current_timeframe: str = "1D"
        self._current_chart_type: str = "candle"
        self._active_indicators: set[str] = set()
        self._company_name: str = ""
        self._last_price_str: str = "₺0.00"
        self._price_change_str: str = "+0.00%"
        self._is_positive: bool = True
        self._average_cost: float | None = None  # Hisse Detay'dan açılan grafikte ortalama maliyet çizgisi
        self._average_cost_ticker: str = ""

        # Eğer portföyde hisseler varsa ilk hisseyi varsayılan grafik yap
        if self._container:
            try:
                port_service = getattr(self._container, "portfolio_service", None)
                if not port_service and hasattr(self._container, "services"):
                    port_service = getattr(self._container.services, "portfolio_service", None)

                lookup = getattr(self._container, "stock_lookup_service", None)
                if port_service and lookup:
                    port = port_service.get_current_portfolio()
                    if port and port.active_positions:
                        first_sid = next(iter(port.active_positions.keys()))
                        stock = lookup.get_stock(first_sid)
                        if stock and stock.ticker:
                            self._current_ticker = stock.ticker
            except Exception as exc:
                logger.debug("Varsayılan grafik hissesi belirlenemedi: %s", exc)

    # --- Properties ---

    @Property(str, notify=tickerChanged)
    def currentTicker(self) -> str:
        return self._current_ticker

    @Property(str, notify=timeframeChanged)
    def currentTimeframe(self) -> str:
        return self._current_timeframe

    @Property(str, notify=chartTypeChanged)
    def currentChartType(self) -> str:
        return self._current_chart_type

    @Property(str, notify=tickerChanged)
    def companyName(self) -> str:
        return self._company_name

    @Property(str, notify=tickerChanged)
    def lastPrice(self) -> str:
        return self._last_price_str

    @Property(str, notify=tickerChanged)
    def priceChange(self) -> str:
        return self._price_change_str

    @Property(bool, notify=tickerChanged)
    def isPositive(self) -> bool:
        return self._is_positive

    @Property(list, notify=indicatorsChanged)
    def activeIndicators(self) -> list[str]:
        return sorted(list(self._active_indicators))

    # --- Slots ---

    @Slot(str)
    def loadTicker(self, ticker: str) -> None:
        self._average_cost, self._average_cost_ticker = None, ""  # sıradan yüklemede maliyet çizgisi gösterilmez
        self._load_ticker(ticker)

    def _load_ticker(self, ticker: str) -> None:
        ticker = ticker.strip().upper()
        if not ticker:
            return
        self._current_ticker = ticker
        self.tickerChanged.emit(ticker)
        self._fetch_and_emit_chart_data(ticker)

    @Slot(str, float)
    def loadTickerWithCost(self, ticker: str, average_cost: float) -> None:
        """Grafiği ortalama maliyet çizgisiyle yükler (Hisse Detay > Grafik). Maliyet <= 0 ise çizgi çizilmez."""
        clean = ticker.replace(".IS", "").strip().upper()
        self._average_cost = float(average_cost) if average_cost and average_cost > 0 else None
        self._average_cost_ticker = clean if self._average_cost else ""
        self._load_ticker(ticker)

    @Slot(str)
    def loadStock(self, ticker: str) -> None:
        """loadTicker için uyumluluk takma adı (alias)."""
        self.loadTicker(ticker)

    @Slot(str)
    def setTimeframe(self, tf: str) -> None:
        tf = tf.strip().upper()
        if tf not in ["1D", "1W", "1M"] or tf == self._current_timeframe:
            return
        self._current_timeframe = tf
        self.timeframeChanged.emit(tf)
        self._fetch_and_emit_chart_data(self._current_ticker)

    @Slot(str)
    def setChartType(self, chart_type: str) -> None:
        chart_type = chart_type.strip().lower()
        if chart_type not in ["candle", "line", "area", "bar"] or chart_type == self._current_chart_type:
            return
        self._current_chart_type = chart_type
        self.chartTypeChanged.emit(chart_type)

    @Slot(str)
    @Slot(str, bool)
    def toggleIndicator(self, indicator: str, enabled: Optional[bool] = None) -> None:
        ind = indicator.strip().lower()
        if enabled is None:
            if ind in self._active_indicators:
                self._active_indicators.discard(ind)
            else:
                self._active_indicators.add(ind)
        elif enabled:
            self._active_indicators.add(ind)
        else:
            self._active_indicators.discard(ind)
        self.indicatorsChanged.emit()

    # --- Data Fetching & Processing ---

    def _load_candles(self, ticker: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
        """Mum kaynağı sırası: DuckDB piyasa geçmişi, SQLite fiyatları; demo yalnızca konteynersiz modda."""
        lookup = getattr(self._container, "stock_lookup_service", None) if self._container else None
        if lookup is not None:
            loaded = load_market_history_candles(lookup, ticker)
            if loaded:
                return loaded
        if self._container:
            return load_price_series_candles(lookup, ticker)
        return demo_candles(ticker)

    def _update_last_price(self, candles: list[dict[str, Any]]) -> None:
        summary = last_price_summary(candles)
        if summary is not None:
            self._last_price_str, self._is_positive, self._price_change_str = summary

    def _build_payload(
        self,
        ticker: str,
        candles: list[dict[str, Any]],
        volumes: list[dict[str, Any]],
        indicators: dict[str, Any],
    ) -> dict[str, Any]:
        clean_ticker = ticker.replace(".IS", "").strip().upper()
        return {
            "ticker": clean_ticker,
            "companyName": (self._company_name or "").replace(".IS", "").strip(),
            "timeframe": self._current_timeframe,
            "chartType": self._current_chart_type,
            "candles": candles,
            "volumes": volumes,
            # Ortalama maliyet çizgisi yalnızca maliyetin ait olduğu hissede gösterilir
            "avgCost": self._average_cost if clean_ticker == self._average_cost_ticker else None,
            **indicators,
        }

    def _fetch_and_emit_chart_data(self, ticker: str) -> None:
        """
        Mumları kaynaklardan yükler, zaman dilimine (1D, 1W, 1M) göre resample eder,
        tüm teknik indikatörleri (SMA, EMA, BB, RSI, MACD) hesaplar ve zengin JSON yayar.
        """
        raw_candles, raw_volumes, self._company_name = self._load_candles(ticker)
        candles, volumes = self._resample_timeframe(raw_candles, raw_volumes, self._current_timeframe)
        self._update_last_price(candles)
        payload = self._build_payload(ticker, candles, volumes, self._calculate_indicators(candles))
        self.chartDataLoaded.emit(ticker, json.dumps(payload))

    def _resample_timeframe(
        self,
        candles: list[dict[str, Any]],
        volumes: list[dict[str, Any]],
        timeframe: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Günlük mumları 1W (Haftalık) veya 1M (Aylık) mumlara konsolide eder."""
        if timeframe == "1D" or not candles:
            return candles, volumes

        df = pd.DataFrame(candles)
        df["volume"] = [v["value"] for v in volumes]
        df["dt"] = pd.to_datetime(df["time"])
        df.set_index("dt", inplace=True)

        if timeframe == "1W":
            # Haftalık gruplama: W-FRI (Cuma kapanışlı)
            rule = "W"
        elif timeframe == "1M":
            # Aylık gruplama: ME (Ay sonu)
            rule = "ME"
        else:
            return candles, volumes

        try:
            agg_dict = {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
                "time": "last",
            }
            resampled = df.resample(rule).agg(agg_dict).dropna()

            out_candles = []
            out_volumes = []
            for _, row in resampled.iterrows():
                t = str(row["time"])
                o = float(row["open"])
                h = float(row["high"])
                l = float(row["low"])
                c = float(row["close"])
                v = float(row["volume"])

                out_candles.append({
                    "time": t,
                    "open": round(o, 2),
                    "high": round(h, 2),
                    "low": round(l, 2),
                    "close": round(c, 2),
                })
                out_volumes.append({
                    "time": t,
                    "value": v,
                    "color": "rgba(8, 153, 129, 0.4)" if c >= o else "rgba(242, 54, 69, 0.4)",
                })

            return out_candles, out_volumes
        except Exception as exc:
            logger.warning("Resampling hatasi: %s, fallback 1D", exc)
            return candles, volumes

    def _calculate_indicators(self, candles: list[dict[str, Any]]) -> dict[str, Any]:
        """Tüm teknik indikatör serilerini ve sinyal işaretçilerini hesaplar (`chart_indicators`)."""
        return calculate_indicators(candles)
