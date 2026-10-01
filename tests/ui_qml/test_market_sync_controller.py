from unittest.mock import MagicMock, patch
import pytest
from PySide6.QtCore import QCoreApplication

from src.application.services.market_data.market_data_sync_service import (
    MarketSyncResult,
    MarketSyncStatus,
)
from src.ui_qml.controllers.market_sync_controller import MarketSyncController


@pytest.fixture
def mock_sync_service():
    svc = MagicMock()
    svc.get_sync_status.return_value = MarketSyncStatus(
        max_db_date=None,
        last_completed_trading_day=None,
        is_up_to_date=True,
        missing_trading_days=[],
        message="Veriler güncel",
    )
    def mock_sync():
        import time
        time.sleep(0.05)
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


def test_market_sync_controller_trigger_sync(qapp, mock_sync_service):
    ctrl = MarketSyncController(sync_service=mock_sync_service)
    notifications = []
    ctrl.syncNotification.connect(lambda s, m: notifications.append((s, m)))

    ctrl.triggerSyncNow()
    assert ctrl.isSyncing is True

    # Thread tamamlanmasını bekle
    import time
    for _ in range(50):
        qapp.processEvents()
        if not ctrl.isSyncing:
            break
        time.sleep(0.02)

    assert not ctrl.isSyncing
    assert ctrl.isUpToDate is True
    assert len(notifications) == 1
    assert notifications[0][0] is True
    assert "10 hisse" in notifications[0][1]
