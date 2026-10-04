"""Açılış işleri ilk kapanış senkronu bittikten sonra bir kez başlar (aynı kapanışlar iki yoldan indirilmez)."""
from __future__ import annotations

from unittest.mock import MagicMock

from PySide6.QtCore import QObject, QSettings, Signal

from src.application.services.market_data.market_data_sync_service import MarketSyncResult
from src.ui_qml.controllers.market_sync_controller import MarketSyncController
from src.ui_qml.controllers.startup_jobs_controller import StartupJobsController


class _Sync(QObject):
    finished = Signal()


def test_startup_jobs_wait_for_first_sync_and_run_once(qapp, tmp_path):
    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    ctrl = StartupJobsController(container=None, settings=settings, autostart=False)
    runs = []
    ctrl.runAll = lambda: runs.append(1)
    sync = _Sync()

    ctrl.start_after(sync.finished)
    assert runs == []  # senkron bitmeden başlamaz

    sync.finished.emit()
    sync.finished.emit()  # sonraki senkronlar açılış işlerini yeniden başlatmaz
    assert runs == [1]


def test_market_sync_emits_finished_on_success_and_failure(qapp):
    ctrl = MarketSyncController(sync_service=MagicMock())
    finished = []
    ctrl.syncFinished.connect(lambda: finished.append(1))

    ctrl._on_sync_finished(MarketSyncResult(is_up_to_date=True, updated_stocks=0, added_bars=0, elapsed_seconds=0.1, message="güncel"))
    ctrl._on_sync_failed("ağ yok")

    assert finished == [1, 1]
