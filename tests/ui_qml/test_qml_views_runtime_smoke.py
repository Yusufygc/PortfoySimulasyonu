"""Büyük QML görünümleri için çalışma zamanı duman testi.

Her görünüm uygulamadakiyle aynı bağlam özellikleriyle (denetleyiciler) oluşturulur, tüm sekme/mod değerleri sırayla
etkinleştirilir ve QML motorunun hiçbir uyarı (tanımsız kimlik, bağlama hatası, TypeError) üretmediği doğrulanır.
Bölme/yeniden düzenleme sırasında koparılan bağlamaları (`root.*`, üst kimlik başvuruları) yakalamak içindir.
"""
from __future__ import annotations

from pathlib import Path
import re

import pytest
from PySide6.QtCore import QCoreApplication, QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtWebEngineQuick import QtWebEngineQuick
from PySide6.QtWidgets import QApplication

from tests.ui_qml.qobject_utils import children_of_class
from src.application.container import AppContainer
from src.ui_qml.app import create_controllers

QML_DIR = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "qml"

# (qml dosyası, değiştirilen özellik, değerler, denetleyici üzerinden sürücü (ad, yuva, değerler) ya da None)
TARGETS = {
    "DashboardView": ("views/DashboardView.qml", None, [None], None),
    "MyPortfolioView": ("views/MyPortfolioView.qml", None, [None], None),
    "SettingsView": ("views/SettingsView.qml", "activeTabIndex", range(9), None),
    "AiAdvisorView": ("views/AiAdvisorView.qml", "mode", range(2), None),
    "OptimizationView": ("views/OptimizationView.qml", None, [None], None),
    # Hisse 360 görünüm modları (0 Genel Bakış, 1 Finansal, 2 KAP) bir denetleyici yuvasıyla değişir
    "Stock360View": ("views/Stock360View.qml", None, [None], ("stock360Controller", "setViewMode", (0, 1, 2, 0))),
    # Alt sekme durumu StockDetailTabsPanel bileşeninde: çocuk bileşenin özelliği değiştirilir
    "StockDetailModal": ("components/StockDetailModal.qml", None, [None], ("child", "StockDetailTabsPanel", "activeTab", (0, 1, 0))),
}


@pytest.fixture(scope="session")
def qapp():
    QtWebEngineQuick.initialize()
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def qml_env(qapp):
    container = AppContainer()
    engine = QQmlApplicationEngine()
    controllers = create_controllers(container, engine, autostart=False)  # uygulamadaki tek liste
    context = engine.rootContext()
    for name, controller in controllers.items():
        context.setContextProperty(name, controller)
    engine.addImportPath(str(QML_DIR))
    warnings: list[str] = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    yield engine, warnings, controllers
    engine.deleteLater()


def _pump(times: int = 6) -> None:
    for _ in range(times):
        QCoreApplication.processEvents()


@pytest.mark.parametrize("name", sorted(TARGETS))
def test_view_loads_every_tab_without_qml_warnings(qml_env, name):
    engine, warnings, controllers = qml_env
    relative_path, property_name, values, driver = TARGETS[name]
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / relative_path)))
    assert component.isReady(), "; ".join(e.toString() for e in component.errors())

    item = component.create()
    assert item is not None, f"{name} oluşturulamadı"
    item.setProperty("width", 1280)
    item.setProperty("height", 820)
    _pump()
    for value in values:
        if property_name is not None:
            item.setProperty(property_name, value)
        _pump()

    if driver is not None and driver[0] == "child":
        _, class_name, property_name, driver_values = driver
        children = children_of_class(item, class_name)
        assert children, f"{class_name} bulunamadı"
        for value in driver_values:
            assert children[0].setProperty(property_name, value), f"{class_name}.{property_name} ayarlanamadı"
            _pump(10)
    elif driver is not None:
        controller_name, slot_name, driver_values = driver
        for value in driver_values:
            getattr(controllers[controller_name], slot_name)(value)
            _pump(10)

    assert warnings == [], "\n".join(warnings)


def _extract_qml_blocks(text: str, component_name: str) -> list[str]:
    blocks: list[str] = []
    pattern = re.compile(rf"\b{component_name}\s*\{{")
    for match in pattern.finditer(text):
        depth = 0
        end = match.end()
        for idx in range(match.end() - 1, len(text)):
            ch = text[idx]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = idx + 1
                    break
        blocks.append(text[match.start():end])
    return blocks


@pytest.mark.parametrize(
    "relative_path",
    [
        "views/Stock360View.qml",
        "views/MyPortfolioView.qml",
        "views/WatchlistView.qml",
        "views/SettingsView.qml",
    ],
)
def test_page_scroll_views_reserve_right_gutter_for_vertical_scrollbar(qml_env, relative_path):
    engine, _warnings, _controllers = qml_env
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / relative_path)))
    assert component.isReady(), "; ".join(e.toString() for e in component.errors())

    item = component.create()
    assert item is not None
    item.setProperty("width", 1280)
    item.setProperty("height", 820)
    _pump()

    scroll_views = children_of_class(item, "ScrollView")
    assert scroll_views, f"{relative_path} içinde ScrollView bulunamadı"
    sv = scroll_views[0]
    assert float(sv.property("rightPadding")) >= 12.0
    assert float(sv.property("availableWidth")) <= float(sv.property("width")) - 12.0


def test_interactive_listviews_and_scrollviews_do_not_let_scrollbar_overlap_content():
    offending_scrollviews: list[str] = []
    offending_listviews: list[str] = []
    for path in sorted(QML_DIR.rglob("*.qml")):
        rel = path.relative_to(QML_DIR).as_posix()
        text = path.read_text(encoding="utf-8")
        for block in _extract_qml_blocks(text, "ScrollView"):
            if not re.search(r"\brightPadding\s*:", block):
                offending_scrollviews.append(rel)
        for block in _extract_qml_blocks(text, "ListView"):
            if re.search(r"\binteractive\s*:\s*false\b", block):
                continue
            id_match = re.search(r"\bid\s*:\s*(\w+)", block)
            if not id_match:
                continue
            list_id = id_match.group(1)
            if re.search(rf"\bwidth\s*:\s*{re.escape(list_id)}\.width(?:\s*[;\n\r}}]|$)", block):
                offending_listviews.append(f"{rel} ({list_id})")

    assert not offending_scrollviews, f"ScrollView sağ boşluğu (rightPadding) eksik: {offending_scrollviews}"
    assert not offending_listviews, f"Etkileşimli ListView delegate scrollbar altında kalıyor: {offending_listviews}"
