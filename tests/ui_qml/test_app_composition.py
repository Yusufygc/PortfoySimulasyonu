"""Bileşim kökü (`src/ui_qml/app.py`): denetleyiciler kurulur, QML bağlamına kaydedilir ve birbirine bağlanır.

Gerçek container (oturuma özel veritabanı kopyası) kullanılır; Main.qml yüklenmez, olay döngüsü başlatılmaz,
zamanlayıcılar (`autostart=False`) çalışmaz.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from PySide6.QtCore import SIGNAL
from PySide6.QtQml import QQmlApplicationEngine

from src.application.container import AppContainer
from src.ui_qml import app as app_module

QML_DIR = Path(app_module.__file__).resolve().parent / "qml"


@pytest.fixture
def built(qapp):  # işlev kapsamı: ui conftest arka plan senkron/getiri yamaları kurulumdan önce uygulanır
    engine = QQmlApplicationEngine()
    controllers = app_module.build_ui(engine, AppContainer(), autostart=False)
    yield engine, controllers
    engine.deleteLater()


def _qml_controller_names() -> set:
    names = set()
    for path in QML_DIR.rglob("*.qml"):
        text = path.read_text(encoding="utf-8")
        names |= set(re.findall(r"\b([a-z][A-Za-z0-9]*Controller)\s*\.", text))  # xController.özellik
        names |= set(re.findall(r"typeof\s+([a-z][A-Za-z0-9]*Controller)\b", text))
    return names


def test_every_controller_used_in_qml_is_registered(built):
    engine, controllers = built
    context = engine.rootContext()
    missing = sorted(name for name in _qml_controller_names() if context.contextProperty(name) is None)
    assert missing == [], f"QML'de kullanılıp bağlama kaydedilmeyen denetleyiciler: {missing}"
    assert all(context.contextProperty(name) is controller for name, controller in controllers.items())


def test_timers_do_not_autostart_in_tests(built):
    _, controllers = built
    assert not controllers["assetsController"]._timer.isActive()
    assert not controllers["newsController"]._timer.isActive()


def _receivers(obj, signature: str) -> int:
    return obj.receivers(SIGNAL(signature))


@pytest.mark.parametrize(
    "source, signature, minimum",
    [
        ("priceRefreshController", "pricesChanged()", 4),          # Genel Bakış, Portföyüm, izleme, model portföy
        ("assetsController", "dataChanged()", 3),                  # Portföyüm, haber, grafik hızlı seçici
        ("systemController", "systemReset()", 5),                  # fiyat koordinatörü, model, Portföyüm, haber, izleme
        ("newsSettingsController", "sourcesChanged()", 1),
        ("newsSettingsController", "refreshMinutesChanged(int)", 1),
        ("riskProfileController", "profileSaved()", 1),
        ("marketSyncController", "syncFinished()", 1),             # açılış işleri ilk senkrondan sonra
        ("cashPoolController", "balancesChanged()", 2),            # Portföyüm ve Ana Sayfa nakdi yeniden okur
        ("dashboardController", "tradeExecuted(bool,QString)", 1), # BIST işlemi nakit havuzunu yeniler
    ],
)
def test_cross_controller_signals_are_wired(built, source, signature, minimum):
    _, controllers = built
    assert _receivers(controllers[source], signature) >= minimum


def test_assets_change_refreshes_my_portfolio(built, monkeypatch):
    """Bağlantı davranışı: varlık defteri değişince Portföyüm özeti yeniden okunur."""
    _, controllers = built
    controllers["newsController"]._container = None  # haber yenilemesi ağa çıkmasın (servis yok -> işlem yapmaz)
    service = controllers["myPortfolioController"]._service
    calls = []
    original = service.get_summary
    monkeypatch.setattr(service, "get_summary", lambda *a, **k: calls.append(1) or original(*a, **k))

    controllers["assetsController"].dataChanged.emit()

    assert calls, "assetsController.dataChanged Portföyüm'ü yeniden okutmadı"


def test_window_is_fitted_and_centered_on_small_screen():
    from types import SimpleNamespace

    class Window:
        def __init__(self):
            self.props = {"width": 1600, "height": 1000}

        def property(self, name):
            return self.props.get(name)

        def setProperty(self, name, value):  # noqa: N802 - Qt API adı
            self.props[name] = value

    window = Window()
    geometry = SimpleNamespace(x=lambda: 0, y=lambda: 0, width=lambda: 1366, height=lambda: 728)
    app = SimpleNamespace(primaryScreen=lambda: SimpleNamespace(availableGeometry=lambda: geometry))
    engine = SimpleNamespace(rootObjects=lambda: [window])

    app_module._fit_window_to_screen(app, engine)

    assert window.props == {"width": 1326, "height": 668, "x": 20, "y": 30}
    app_module._fit_window_to_screen(SimpleNamespace(primaryScreen=lambda: None), engine)  # ekran yoksa dokunmaz
