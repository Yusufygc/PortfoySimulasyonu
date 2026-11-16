"""FeeSettingsController ve SettingsFeesTab.qml: kaydetme, doğrulama, varsayılan 0 ve uyarısız yükleme."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QCoreApplication, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

from src.application.services.settings.fee_settings_service import FeeSettingsService
from src.domain.ports.repositories.i_app_settings_repo import IAppSettingsRepository
from src.ui_qml.controllers.fee_settings_controller import FeeSettingsController, rate_text

QML_DIR = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "qml"


class MemorySettings(IAppSettingsRepository):
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value):
        self.values[key] = value


@pytest.fixture(scope="module")
def qapp():
    return QGuiApplication.instance() or QGuiApplication([])


def _controller(qapp, service=None):
    service = service or FeeSettingsService(MemorySettings())
    return FeeSettingsController(container=SimpleNamespace(fee_settings_service=service)), service


def test_rate_text_uses_turkish_decimal_comma():
    assert [rate_text(Decimal(v)) for v in ("0", "0.200", "5.00", "0.0125")] == ["0", "0,2", "5", "0,0125"]


def test_defaults_are_zero(qapp):
    controller, _ = _controller(qapp)
    assert (controller.bistCommission, controller.assetCommission, controller.bsmv) == ("0", "0", "0")


def test_save_accepts_turkish_numbers_and_persists(qapp):
    controller, service = _controller(qapp)
    results = []
    controller.notify.connect(lambda ok, text: results.append((ok, text)))

    controller.save("0,2", "0.1", "5")

    rates = service.get_rates()
    assert (rates.bist_commission_pct, rates.asset_commission_pct, rates.bsmv_pct) == (Decimal("0.2"), Decimal("0.1"), Decimal("5"))
    assert results == [(True, "Ücret oranları kaydedildi.")]
    assert (controller.bistCommission, controller.bsmv) == ("0,2", "5")


def test_save_rejects_invalid_and_out_of_range_values_without_changing_rates(qapp):
    controller, service = _controller(qapp)
    results = []
    controller.notify.connect(lambda ok, text: results.append(ok))

    controller.save("abc", "0", "0")
    controller.save("11", "0", "0")      # komisyon üst sınırı %10
    controller.save("0", "0", "101")     # BSMV üst sınırı %100

    assert results == [False, False, False]
    assert service.get_rates().bist_commission_pct == Decimal("0")


def test_empty_fields_mean_zero_and_missing_service_is_reported(qapp):
    controller, service = _controller(qapp)
    controller.save("", "", "")
    assert service.get_rates().bsmv_pct == Decimal("0")

    missing = FeeSettingsController(container=None)
    results = []
    missing.notify.connect(lambda ok, text: results.append(ok))
    missing.save("0", "0", "0")
    assert results == [False]


def test_fees_tab_loads_without_warnings(qapp):
    controller, _ = _controller(qapp)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("feeSettingsController", controller)
    engine.addImportPath(str(QML_DIR))
    warnings: list[str] = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))

    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / "components" / "SettingsFeesTab.qml")))
    assert component.isReady(), "; ".join(e.toString() for e in component.errors())
    item = component.create()
    assert item is not None
    for _ in range(5):
        QCoreApplication.processEvents()

    assert warnings == []
    item._engine, item._component = engine, component


def test_set_mode_and_save_fixed_fee_persists_and_reloads(qapp):
    controller, service = _controller(qapp)
    assert (controller.bistMode, controller.assetMode, controller.bsmvMode) == ("PCT", "PCT", "PCT")

    controller.setMode("bist", "FIXED")
    controller.setMode("asset", "fixed")
    controller.setMode("bsmv", "PCT")
    controller.setMode("unknown", "FIXED")
    controller.setMode("bist", "BOGUS")

    assert (controller.bistMode, controller.assetMode, controller.bsmvMode) == ("FIXED", "FIXED", "PCT")

    results = []
    controller.notify.connect(lambda ok, text: results.append((ok, text)))
    controller.save("25", "1,5", "5")

    assert results == [(True, "Ücret oranları kaydedildi.")]
    saved = service.get_rates()
    assert (saved.bist_mode, saved.asset_mode, saved.bsmv_mode) == ("FIXED", "FIXED", "PCT")
    assert service.bist_fee(Decimal("1000")) == Decimal("26.2500")
    assert service.asset_fee(Decimal("1000")) == Decimal("1.5750")

    reloaded = FeeSettingsController(container=SimpleNamespace(fee_settings_service=service))
    assert (reloaded.bistMode, reloaded.assetMode, reloaded.bsmvMode) == ("FIXED", "FIXED", "PCT")
    assert (reloaded.bistCommission, reloaded.assetCommission, reloaded.bsmv) == ("25", "1,5", "5")


def test_fixed_mode_validation_rejects_above_max_fixed_fee(qapp):
    controller, service = _controller(qapp)
    results = []
    controller.notify.connect(lambda ok, text: results.append(ok))
    controller.setMode("bist", "FIXED")

    controller.save("100001", "0", "0")
    assert results == [False]
    assert service.get_rates().bist_commission_pct == Decimal("0")


def test_fees_tab_mode_buttons_toggle_mode_in_qml(qapp):
    controller, _ = _controller(qapp)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("feeSettingsController", controller)
    engine.addImportPath(str(QML_DIR))
    warnings: list[str] = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))

    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / "components" / "SettingsFeesTab.qml")))
    assert component.isReady(), "; ".join(e.toString() for e in component.errors())
    item = component.create()
    assert item is not None
    for _ in range(5):
        QCoreApplication.processEvents()

    controller.setMode("bist", "FIXED")
    for _ in range(5):
        QCoreApplication.processEvents()
    assert controller.bistMode == "FIXED"
    assert warnings == []
    item._engine, item._component = engine, component
