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
