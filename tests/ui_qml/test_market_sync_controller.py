import threading
from unittest.mock import MagicMock, patch
import pytest
from PySide6.QtCore import QCoreApplication

from src.application.services.market_data.market_data_sync_service import (
    MarketSyncResult,
    MarketSyncStatus,
)
from src.ui_qml.controllers.market_sync_controller import MarketSyncController


@pytest.fixture
def sync_gate():
    """Sahte senkronu, test `isSyncing` durumunu doğrulayana kadar bekletir (sabit uyku yerine olay)."""
    gate = threading.Event()
    yield gate
    gate.set()  # test erken biterse iş parçacığı takılı kalmasın


@pytest.fixture
def mock_sync_service(sync_gate):
    svc = MagicMock()
    svc.get_sync_status.return_value = MarketSyncStatus(
        max_db_date=None,
        last_completed_trading_day=None,
        is_up_to_date=True,
        missing_trading_days=[],
        message="Veriler güncel",
    )
    def mock_sync():
        sync_gate.wait(timeout=10)
        return MarketSyncResult(
            is_up_to_date=True,
            updated_stocks=10,
            added_bars=20,
            elapsed_seconds=1.2,
            message="10 hisse güncellendi",
        )
    svc.sync_daily_delta.side_effect = mock_sync
    return svc


def test_market_sync_controller_initialization(qapp, mock_sync_service):
    ctrl = MarketSyncController(sync_service=mock_sync_service)
    assert not ctrl.isSyncing
    assert ctrl.isUpToDate is True
    assert "hazır" in ctrl.statusText.lower()


def test_market_sync_controller_trigger_sync(qapp, mock_sync_service, sync_gate, wait_until):
    ctrl = MarketSyncController(sync_service=mock_sync_service)
    notifications = []
    ctrl.syncNotification.connect(lambda s, m: notifications.append((s, m)))

    ctrl.triggerSyncNow()
    assert ctrl.isSyncing is True  # senkron kapıda bekliyor: durum deterministik

    sync_gate.set()
    assert wait_until(lambda: not ctrl.isSyncing), "Senkron tamamlanmadı"

    assert not ctrl.isSyncing
    assert ctrl.isUpToDate is True
    assert len(notifications) == 1
    assert notifications[0][0] is True
    assert "10 hisse" in notifications[0][1]


def test_watcher_syncs_once_when_today_close_data_is_ready(qapp, mock_sync_service, sync_gate, monkeypatch):
    """Nöbetçi saat sabiti değil, servisin kapanış verisi hazır günü (Istanbul saati, tatil takvimi) ile karar verir."""
    from datetime import date
    from src.ui_qml.controllers import market_sync_controller as module

    today = date(2026, 10, 5)
    monkeypatch.setattr(module, "market_today", lambda: today)
    ctrl = MarketSyncController(sync_service=mock_sync_service)
    ctrl.triggerSyncNow = MagicMock()

    mock_sync_service.get_last_completed_trading_day.return_value = date(2026, 10, 2)  # kapanış verisi henüz yok
    ctrl._on_watcher_tick()
    assert ctrl.triggerSyncNow.call_count == 0

    mock_sync_service.get_last_completed_trading_day.return_value = today
    ctrl._on_watcher_tick()
    ctrl._on_watcher_tick()
    assert ctrl.triggerSyncNow.call_count == 1
