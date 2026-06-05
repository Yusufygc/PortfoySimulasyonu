from __future__ import annotations

import logging
from datetime import date, datetime

from PyQt5.QtCore import QSettings, QThreadPool, QTimer

from src.ui.shared.price_event_publisher import publish_prices_updated
from src.ui.widgets.shared import Toast
from src.ui.worker import Worker

logger = logging.getLogger(__name__)

LIVE_PRICE_REFRESH_ENABLED_KEY = "settings/live_price_refresh_enabled"
LIVE_PRICE_REFRESH_INTERVAL_KEY = "settings/live_price_refresh_interval_minutes"
LAST_LIVE_PRICE_REFRESH_KEY = "settings/last_live_price_refresh_at"
DEFAULT_LIVE_PRICE_REFRESH_ENABLED = True
DEFAULT_LIVE_PRICE_REFRESH_INTERVAL_MINUTES = 15
LIVE_PRICE_REFRESH_INTERVAL_OPTIONS = (5, 15, 30, 60)


class LivePriceRefreshController:
    def __init__(
        self,
        parent,
        container,
        settings: QSettings,
        threadpool: QThreadPool,
    ) -> None:
        self._parent = parent
        self._container = container
        self._settings = settings
        self._threadpool = threadpool
        self._timer = QTimer(parent)
        self._timer.timeout.connect(self.run_once)
        self._running = False
        self._consecutive_errors = 0

    def start(self) -> None:
        self.reload_settings()
        QTimer.singleShot(0, self.run_once)

    def reload_settings(self) -> None:
        self._timer.stop()
        if not self.enabled():
            return
        self._timer.start(self.interval_minutes() * 60_000)

    def enabled(self) -> bool:
        return _settings_bool(
            self._settings.value(
                LIVE_PRICE_REFRESH_ENABLED_KEY,
                DEFAULT_LIVE_PRICE_REFRESH_ENABLED,
            ),
            DEFAULT_LIVE_PRICE_REFRESH_ENABLED,
        )

    def interval_minutes(self) -> int:
        return 15

    def run_once(self) -> None:
        if self._running or not self.enabled() or not self._is_bist_trading_day():
            return
        service = getattr(self._container, "live_price_refresh_service", None)
        if service is None:
            return
        self._running = True
        worker = Worker(service.refresh_active_prices)
        worker.signals.result.connect(self._on_success)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(self._on_finished)
        self._threadpool.start(worker)

    def _is_bist_trading_day(self) -> bool:
        session_service = getattr(self._container, "bist_market_session_service", None)
        if session_service is None:
            return True
        try:
            return bool(session_service.status_for(date.today()).is_open)
        except Exception as exc:
            logger.warning("BIST trading day check failed: %s", exc)
            return True

    def _on_success(self, result) -> None:
        self._consecutive_errors = 0
        publish_prices_updated(getattr(self._container, "event_bus", None), getattr(result, "prices", None))
        self._settings.setValue(
            LAST_LIVE_PRICE_REFRESH_KEY,
            _iso_timestamp(getattr(result, "finished_at", None)),
        )
        self._settings.sync()
        errors = getattr(result, "errors", None) or []
        if errors:
            logger.info("Live price refresh completed with %d item errors.", len(errors))

    def _on_error(self, err_tuple) -> None:
        self._consecutive_errors += 1
        logger.warning("Live price refresh failed: %s", err_tuple[1])
        if self._consecutive_errors >= 3:
            Toast.warning(self._parent, f"Otomatik fiyat yenileme calistirilamadi: {err_tuple[1]}")
            self._consecutive_errors = 0

    def _on_finished(self) -> None:
        self._running = False


def _settings_bool(value, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "hayir", "hayır", "no", "off"}
    return bool(value)


def _iso_timestamp(value) -> str:
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    return datetime.now().isoformat(timespec="seconds")
