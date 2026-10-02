"""QML testleri için ortak ayarlar."""
import os

# Uygulamayla aynı Qt Quick Controls stili (Basic); özelleştirme uyarılarını önler.
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

import pytest


@pytest.fixture(autouse=True)
def _no_background_market_sync(monkeypatch):
    """MarketSyncController açılıştan 5 sn sonra gerçek DuckDB senkronu başlatır.

    Test süresi uzayınca bu zamanlayıcı başka testlerin DuckDB erişimiyle çakışıp native çökmeye
    yol açıyordu; testlerde açılış zamanlayıcısı devre dışı bırakılır.
    """
    from PySide6.QtCore import QTimer

    import src.ui_qml.controllers.market_sync_controller as module

    class _TimerWithoutSingleShot(QTimer):
        @staticmethod
        def singleShot(*args, **kwargs):  # noqa: N802 - Qt API adı
            return None

    monkeypatch.setattr(module, "QTimer", _TimerWithoutSingleShot)


@pytest.fixture(autouse=True)
def _isolated_last_update_settings(monkeypatch, tmp_path):
    """Son güncelleme/getiri kayıtları gerçek kullanıcı ayarlarına (kayıt defteri) yazılmasın."""
    from PySide6.QtCore import QSettings

    import src.ui_qml.last_update_store as module

    ini_path = str(tmp_path / "last_update.ini")
    monkeypatch.setattr(module, "QSettings", lambda *args, **kwargs: QSettings(ini_path, QSettings.IniFormat))


@pytest.fixture(autouse=True)
def _no_background_returns_worker(monkeypatch):
    """DashboardController açılışta getirileri arka plan iş parçacığında hesaplar. Test bittikten sonra çalışan
    iş parçacığı silinmiş QObject'e sinyal gönderip native çökmeye yol açmasın; ilgili testler işlemi doğrudan çağırır."""
    from src.ui_qml.controllers.dashboard_controller import DashboardController

    monkeypatch.setattr(DashboardController, "_reload_returns", lambda self: None)
