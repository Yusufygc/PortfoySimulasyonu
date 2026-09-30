"""
Chart Controller — TradingView Lightweight Charts için gelişmiş OHLCV, çoklu zaman dilimi ve teknik indikatör veri köprüsü.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd

from PySide6.QtCore import QObject, Signal, Slot, Property

from src.application.services.analysis.technical.indicators import (
    sma,
    ema,
    rsi,
    macd,
    bollinger_bands,
)
from src.application.services.analysis.technical.golden_cross import detect_crosses, CrossType

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

        # Eğer portföyde hisseler varsa ilk hisseyi varsayılan grafik yap
        if self._container:
            try:
                port_service = getattr(self._container, "portfolio_service", None)
                if not port_service and hasattr(self._container, "services"):
                    port_service = getattr(self._container.services, "portfolio_service", None)

                s360 = getattr(self._container, "stock_360_service", None)
                if not s360 and hasattr(self._container, "services"):
                    s360 = getattr(self._container.services, "stock_360_service", None)

                if port_service:
                    port = port_service.get_current_portfolio()
                    if port and port.active_positions:
                        first_sid = next(iter(port.active_positions.keys()))
                        if s360 and hasattr(s360, "get_all_stocks"):
                            for s in s360.get_all_stocks():
                                if s.id == first_sid and s.ticker:
                                    self._current_ticker = s.ticker
                                    break
                        elif hasattr(self._container, "stock_repo"):
                            stock = self._container.stock_repo.get_stock_by_id(first_sid)
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

    @Property(list, constant=True)
    def timeframes(self) -> list[str]:
        return ["1D", "1W", "1M"]

    @Property(list, constant=True)
    def chartTypes(self) -> list[str]:
        return ["candle", "line", "area", "bar"]

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
        ticker = ticker.strip().upper()
        if not ticker:
            return
        self._current_ticker = ticker
        self.tickerChanged.emit(ticker)
        self._fetch_and_emit_chart_data(ticker)

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

    @Slot(str, result=bool)
    def isIndicatorActive(self, indicator: str) -> bool:
        return indicator.strip().lower() in self._active_indicators

    # --- Data Fetching & Processing ---

    def _fetch_and_emit_chart_data(self, ticker: str) -> None:
        """
        Gerçek veritabanından veri çeker, zaman dilimine (1D, 1W, 1M) göre resample eder,
        tüm teknik indikatörleri (SMA, EMA, BB, RSI, MACD) hesaplar ve zengin JSON döner.
        """
        raw_candles: list[dict[str, Any]] = []
        raw_volumes: list[dict[str, Any]] = []
        company_name = ticker

        # 1. Veritabanından Fiyat Çek (Önce Application servisi üzerinden)
        data_found = False
        if self._container:
            try:
                s360 = getattr(self._container, "stock_360_service", None)
                if not s360 and hasattr(self._container, "services"):
                    s360 = getattr(self._container.services, "stock_360_service", None)

                stock = None
                for candidate in [ticker, f"{ticker}.IS", ticker.replace(".IS", "")]:
                    if s360 and hasattr(s360, "get_stock_by_ticker"):
                        stock = s360.get_stock_by_ticker(candidate)
                    elif hasattr(self._container, "stock_repo"):
                        stock = self._container.stock_repo.get_stock_by_ticker(candidate)
                    if stock:
                        break

                if stock:
                    company_name = getattr(stock, "name", None) or stock.ticker
                    start_date = datetime.now().date() - timedelta(days=365 * 3)  # 3 yıllık veri
                    end_date = datetime.now().date()
                    prices = []
                    if s360 and hasattr(s360, "get_price_series"):
                        prices = s360.get_price_series(stock.id, start_date, end_date)
                    elif hasattr(self._container, "price_repo"):
                        prices = self._container.price_repo.get_price_series(stock.id, start_date, end_date)

                    if prices:
                        sorted_prices = sorted(prices, key=lambda x: x.price_date)
                        prev_close = None
                        for p in sorted_prices:
                            dt_str = p.price_date.strftime("%Y-%m-%d")
                            c = float(p.close_price)

                            if p.open_price is not None and p.high_price is not None and p.low_price is not None:
                                o = float(p.open_price)
                                h = float(p.high_price)
                                l = float(p.low_price)
                            else:
                                o = prev_close if prev_close is not None else c
                                spread = max(abs(c - o), c * 0.008)
                                h = max(o, c) + (spread * 0.35)
                                l = max(0.01, min(o, c) - (spread * 0.35))

                            prev_close = c
                            v = float(p.volume if p.volume is not None and p.volume > 0 else 250000)

                            raw_candles.append({
                                "time": dt_str,
                                "open": round(o, 2),
                                "high": round(h, 2),
                                "low": round(l, 2),
                                "close": round(c, 2),
                            })
                            raw_volumes.append({
                                "time": dt_str,
                                "value": v,
                                "color": "rgba(8, 153, 129, 0.4)" if c >= o else "rgba(242, 54, 69, 0.4)",
                            })

                        data_found = True
                        logger.info("SQLite'tan %s icin %d adet 1D mum verisi yuklendi.", ticker, len(raw_candles))
            except Exception as exc:
                logger.warning("Fiyat verisi cekilirken hata: %s", exc)

        # 2. Fallback Mock Veri (Veritabanında hisse yoksa)
        if not data_found or not raw_candles:
            base_price = 285.0 if "THY" in ticker else (110.0 if "GARAN" in ticker else 150.0)
            today = datetime.now().date()
            np.random.seed(abs(hash(ticker)) % (2**32))

            current_price = base_price
            for i in range(260, -1, -1):
                d = today - timedelta(days=i)
                if d.weekday() >= 5:
                    continue

                change_pct = np.random.normal(0.001, 0.02)
                o = current_price
                c = o * (1 + change_pct)
                h = max(o, c) * (1 + abs(np.random.normal(0, 0.008)))
                l = min(o, c) * (1 - abs(np.random.normal(0, 0.008)))
                v = int(np.random.uniform(500000, 3500000))

                dt_str = d.strftime("%Y-%m-%d")
                raw_candles.append({
                    "time": dt_str,
                    "open": round(o, 2),
                    "high": round(h, 2),
                    "low": round(l, 2),
                    "close": round(c, 2),
                })
                raw_volumes.append({
                    "time": dt_str,
                    "value": v,
                    "color": "rgba(8, 153, 129, 0.4)" if c >= o else "rgba(242, 54, 69, 0.4)",
                })
                current_price = c

        self._company_name = company_name

        # 3. Zaman Dilimine Göre Yeniden Örnekleme (Resampling)
        resampled_candles, resampled_volumes = self._resample_timeframe(
            raw_candles, raw_volumes, self._current_timeframe
        )

        # Son Fiyat Bilgisi Güncelleme
        if resampled_candles:
            last_c = resampled_candles[-1]
            last_close = last_c["close"]
            prev_close = resampled_candles[-2]["close"] if len(resampled_candles) > 1 else last_c["open"]
            diff = last_close - prev_close
            diff_pct = (diff / prev_close) * 100 if prev_close > 0 else 0.0

            self._last_price_str = f"₺{last_close:,.2f}"
            self._is_positive = diff >= 0
            sign = "+" if diff >= 0 else ""
            self._price_change_str = f"{sign}{diff_pct:.2f}%"

        # 4. Teknik İndikatörleri Hesapla (NumPy / Pandas Vektörize)
        indicators_data = self._calculate_indicators(resampled_candles)

        # 5. JSON Paketi Oluştur ve Gönder
        payload = {
            "ticker": ticker,
            "companyName": self._company_name,
            "timeframe": self._current_timeframe,
            "chartType": self._current_chart_type,
            "candles": resampled_candles,
            "volumes": resampled_volumes,
            **indicators_data,
        }

        json_str = json.dumps(payload)
        self.chartDataLoaded.emit(ticker, json_str)

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
        """Tüm teknik indikatör serilerini ve sinyal işaretçilerini hesaplar."""
        empty_result = {
            "sma20": [],
            "sma50": [],
            "sma200": [],
            "ema20": [],
            "bb": {"upper": [], "middle": [], "lower": []},
            "rsi": [],
            "macd": {"macd": [], "signal": [], "hist": []},
            "markers": [],
        }
        if not candles:
            return empty_result

        times = [c["time"] for c in candles]
        closes = pd.Series([c["close"] for c in candles], index=times)
        highs = pd.Series([c["high"] for c in candles], index=times)
        lows = pd.Series([c["low"] for c in candles], index=times)

        def _to_line_data(series: pd.Series) -> list[dict[str, Any]]:
            clean = series.dropna()
            return [{"time": str(t), "value": round(float(v), 2)} for t, v in clean.items()]

        # 1. Hareketli Ortalamalar
        s20 = sma(closes, 20)
        s50 = sma(closes, 50)
        s200 = sma(closes, 200)
        e20 = ema(closes, 20)

        # 2. Bollinger Bantları
        bb_upper, bb_mid, bb_lower = bollinger_bands(closes, 20, 2.0)

        # 3. RSI
        rsi14 = rsi(closes, 14)

        # 4. MACD
        m_line, s_line, h_line = macd(closes, 12, 26, 9)
        macd_clean = m_line.dropna()
        sig_clean = s_line.dropna()
        hist_clean = h_line.dropna()

        macd_hist_data = [
            {
                "time": str(t),
                "value": round(float(v), 2),
                "color": "rgba(8, 153, 129, 0.7)" if v >= 0 else "rgba(242, 54, 69, 0.7)",
            }
            for t, v in hist_clean.items()
        ]

        # 5. Golden Cross / Death Cross Tespiti (Application Servisine Delege Edilir - DRY)
        markers = []
        try:
            cross_events = detect_crosses(closes, short=50, long=200)
            for ev in cross_events:
                if ev.cross_type == CrossType.GOLDEN:
                    markers.append({
                        "time": str(ev.cross_date),
                        "position": "belowBar",
                        "color": "#089981",
                        "shape": "arrowUp",
                        "text": "Golden Cross",
                    })
                elif ev.cross_type == CrossType.DEATH:
                    markers.append({
                        "time": str(ev.cross_date),
                        "position": "aboveBar",
                        "color": "#f23645",
                        "shape": "arrowDown",
                        "text": "Death Cross",
                    })

            # Kısa vadeli seriler için SMA fallback'i
            if not markers and len(s50.dropna()) > 0 and len(s200.dropna()) > 0:
                diff = s50 - s200
                diff_clean = diff.dropna()
                if len(diff_clean) > 1:
                    prev_val = diff_clean.iloc[0]
                    for t, curr_val in diff_clean.iloc[1:].items():
                        if prev_val < 0 and curr_val >= 0:
                            markers.append({
                                "time": str(t),
                                "position": "belowBar",
                                "color": "#089981",
                                "shape": "arrowUp",
                                "text": "Golden Cross",
                            })
                        elif prev_val > 0 and curr_val <= 0:
                            markers.append({
                                "time": str(t),
                                "position": "aboveBar",
                                "color": "#f23645",
                                "shape": "arrowDown",
                                "text": "Death Cross",
                            })
                        prev_val = curr_val
        except Exception as exc:
            logger.debug("Golden/Death cross tespiti sirasinda istisna: %s", exc)

        return {
            "sma20": _to_line_data(s20),
            "sma50": _to_line_data(s50),
            "sma200": _to_line_data(s200),
            "ema20": _to_line_data(e20),
            "bb": {
                "upper": _to_line_data(bb_upper),
                "middle": _to_line_data(bb_mid),
                "lower": _to_line_data(bb_lower),
            },
            "rsi": _to_line_data(rsi14),
            "macd": {
                "macd": _to_line_data(macd_clean),
                "signal": _to_line_data(sig_clean),
                "hist": macd_hist_data,
            },
            "markers": markers,
        }
