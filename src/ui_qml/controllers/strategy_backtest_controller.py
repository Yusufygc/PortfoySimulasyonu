"""
StrategyBacktestController — Planlama > Strateji Testi sekmesi (QML).

Periyodik yeniden dengeleme (eşit ağırlık veya Markowitz maksimum Sharpe) ve stop-loss / take-profit stratejilerini
geçmiş fiyatlarla çalıştırır, sonucu "al ve tut" taban çizgisiyle karşılaştırır. Hesap `StrategyBacktestService`'tedir;
bu sınıf yalnızca form girdisini doğrular, işi arka planda çalıştırır ve sonucu biçimler.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.controllers.date_input import parse_date_text
from src.application.services.simulation.strategy_backtest import BacktestSetup, StrategyBacktestResult
from src.ui_qml.controllers.number_input import parse_decimal_text
from src.ui_qml.controllers.lw_chart_html import line_chart_html
from src.ui_qml.presenters.formatting import tr_money, tr_pct
from src.ui_qml.messages import msg

logger = logging.getLogger(__name__)

_ACTION_LABELS = {
    "REBALANCE": "Dengeleme",
    "STOP_LOSS": "Stop-loss",
    "TAKE_PROFIT": "Take-profit",
    "FALLBACK": msg("backtest.uyari"),
}
_STRATEGY_COLOR = "#2962ff"
_BASELINE_COLOR = "#9db2ce"
_MAX_LISTED_EVENTS = 200


def _fmt_pct(value: Optional[float]) -> str:
    return "-" if value is None else tr_pct(value, with_sign=True)


def parse_number(text: str) -> Optional[float]:
    """'1.234,5', '1234.5' veya '50.000' -> float; boş veya geçersiz metin için None."""
    value = parse_decimal_text(text)
    return None if value is None else float(value)


class StrategyBacktestController(QObject):
    """QML context property: strategyBacktestController"""

    runningChanged = Signal()
    resultChanged = Signal()
    # (success, message) — form hataları ve tamamlanma bildirimi
    notification = Signal(bool, str, arguments=["success", "message"])

    _finished = Signal(object, str)  # worker thread -> ana thread (sonuç, hata)

    def __init__(self, container=None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service = getattr(container, "strategy_backtest_service", None) if container else None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._is_running = False
        self._clear_result()
        self._finished.connect(self._on_finished)

    # ------------------------------------------------------------------ properties

    @Property(bool, notify=runningChanged)
    def isRunning(self) -> bool:
        return self._is_running

    @Property(bool, notify=resultChanged)
    def hasResult(self) -> bool:
        return self._has_result

    @Property(str, notify=resultChanged)
    def strategyReturnText(self) -> str:
        return self._strategy_return

    @Property(str, notify=resultChanged)
    def baselineReturnText(self) -> str:
        return self._baseline_return

    @Property(str, notify=resultChanged)
    def differenceText(self) -> str:
        return self._difference

    @Property(bool, notify=resultChanged)
    def differencePositive(self) -> bool:
        return self._difference_positive

    @Property(str, notify=resultChanged)
    def strategyValueText(self) -> str:
        return self._strategy_value

    @Property(str, notify=resultChanged)
    def baselineValueText(self) -> str:
        return self._baseline_value

    @Property(str, notify=resultChanged)
    def drawdownText(self) -> str:
        return self._drawdown

    @Property(str, notify=resultChanged)
    def baselineDrawdownText(self) -> str:
        return self._baseline_drawdown

    @Property(str, notify=resultChanged)
    def summaryText(self) -> str:
        return self._summary

    @Property("QVariantList", notify=resultChanged)
    def events(self) -> List[Dict[str, Any]]:
        return self._events

    @Property(str, notify=resultChanged)
    def chartHtml(self) -> str:
        return self._chart_html

    # ------------------------------------------------------------------ slots

    @Slot(str, str, str, str, int, str, str)
    def runRebalancing(
        self, tickers: str, capital: str, start: str, end: str, months: int, weighting: str, commission_pct: str,
    ) -> None:
        args = self._common_args(tickers, capital, start, end, commission_pct)
        if args is None:
            return
        setup = self._setup(*args)
        self._submit("rebalance", lambda: self._service.run_rebalancing(setup, months, weighting))

    @Slot(str, str, str, str, str, str, str)
    def runStopTake(
        self, tickers: str, capital: str, start: str, end: str, stop_pct: str, take_pct: str, commission_pct: str,
    ) -> None:
        args = self._common_args(tickers, capital, start, end, commission_pct)
        if args is None:
            return
        stop, take = parse_number(stop_pct), parse_number(take_pct)
        if stop is None and take is None:
            self.notification.emit(False, msg("backtest.stop_loss_veya_take_profit_esiklerinden"))
            return
        setup = self._setup(*args)
        self._submit("stop_take", lambda: self._service.run_stop_take(setup, stop, take))

    # ------------------------------------------------------------------ internal

    @staticmethod
    def _setup(names, amount, start_date, end_date, commission) -> BacktestSetup:
        return BacktestSetup(
            tickers=names, initial_capital=amount, start_date=start_date, end_date=end_date, commission_rate=commission
        )

    def _common_args(self, tickers: str, capital: str, start: str, end: str, commission_pct: str):
        if self._service is None:
            self.notification.emit(False, msg("backtest.strateji_backtest_servisi_kullanilamiyor"))
            return None
        if self._is_running:
            return None
        names = [t for t in tickers.replace(",", " ").split() if t.strip()]
        amount_value = parse_number(capital)
        if amount_value is None or amount_value <= 0:
            self.notification.emit(False, msg("backtest.baslangic_sermayesi_0_dan_buyuk_gecerli"))
            return None
        start_date, end_date = parse_date_text(start), parse_date_text(end)
        if start_date is None or end_date is None:
            self.notification.emit(False, msg("backtest.tarih_gecersiz_bicim_yyyy_aa_gg"))
            return None
        commission_value = parse_number(commission_pct)
        commission = 0.0 if commission_value is None else commission_value / 100.0
        amount = Decimal(str(amount_value))
        return names, amount, start_date, end_date, commission

    def _submit(self, kind: str, job) -> None:
        self._is_running = True
        self.runningChanged.emit()

        def work() -> None:
            try:
                self._finished.emit(job(), "")
            except ValueError as exc:
                self._finished.emit(None, str(exc))
            except Exception as exc:
                logger.exception("Strateji backtest hatası (%s): %s", kind, exc)
                self._finished.emit(None, msg("backtest.simulasyon_calistirilamadi"))

        self._executor.submit(work)

    def _on_finished(self, result: Optional[StrategyBacktestResult], error: str) -> None:
        self._is_running = False
        self.runningChanged.emit()
        if error:
            self.notification.emit(False, error)
            return
        if result is None or not result.strategy_series:
            self._clear_result()
            self.resultChanged.emit()
            self.notification.emit(False, msg("backtest.secilen_tarih_araliginda_tum_hisselerin_fiya"))
            return
        self._apply(result)
        self.resultChanged.emit()
        self.notification.emit(True, msg("backtest.strateji_testi_tamamlandi"))

    def _clear_result(self) -> None:
        self._has_result = False
        self._strategy_return = self._baseline_return = self._difference = "-"
        self._difference_positive = True
        self._strategy_value = self._baseline_value = "-"
        self._drawdown = self._baseline_drawdown = "-"
        self._summary = ""
        self._events: List[Dict[str, Any]] = []
        self._chart_html = ""

    def _apply(self, result: StrategyBacktestResult) -> None:
        self._has_result = True
        self._strategy_return = _fmt_pct(result.total_return_pct)
        self._baseline_return = _fmt_pct(result.baseline_return_pct)
        diff = None
        if result.total_return_pct is not None and result.baseline_return_pct is not None:
            diff = result.total_return_pct - result.baseline_return_pct
        self._difference = _fmt_pct(diff)
        self._difference_positive = diff is None or diff >= 0
        self._strategy_value = tr_money(result.final_value)
        self._baseline_value = tr_money(result.baseline_final_value)
        self._drawdown = _fmt_pct(result.max_drawdown_pct)
        self._baseline_drawdown = _fmt_pct(result.baseline_max_drawdown_pct)

        parts = [f"{result.start_date.strftime('%d.%m.%Y')} - {result.end_date.strftime('%d.%m.%Y')}"]
        if result.rebalance_count:
            parts.append(f"{result.rebalance_count} dengeleme")
        if result.exit_count:
            parts.append(msg("backtest.pozisyon_cikisi", exit_count=result.exit_count))
        if result.skipped_tickers:
            parts.append(msg("backtest.fiyati_olmayan") + ", ".join(result.skipped_tickers))
        self._summary = " | ".join(parts)

        self._events = [
            {
                "dateText": event.event_date.strftime("%d.%m.%Y"),
                "ticker": event.ticker,
                "actionText": _ACTION_LABELS.get(event.action, event.action),
                "action": event.action,
                "detail": event.detail,
            }
            for event in result.events[:_MAX_LISTED_EVENTS]
        ]
        self._chart_html = line_chart_html([
            ("Strateji", _STRATEGY_COLOR, [(d.isoformat(), float(v)) for d, v in sorted(result.strategy_series.items())]),
            ("Al ve tut", _BASELINE_COLOR, [(d.isoformat(), float(v)) for d, v in sorted(result.baseline_series.items())]),
        ])
