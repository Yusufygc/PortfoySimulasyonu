"""ToastNotification: uzun mesaj kutudan taşmaz, satıra sarılır ve kutu yüksekliği büyür.

2026-11-14 ekran görüntüsü: "5 hisse bölünmesi adayı tek kaynakla bulundu..." kutudan sağa ve sola taşıyordu
(genişlik 420 ile sınırlıydı ama metin sarılmıyordu)."""
from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtQuick import QQuickWindow

QML_DIR = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "qml"
LONG = "5 hisse bölünmesi adayı tek kaynakla bulundu ve onay bekliyor. Ayarlar > Kurumsal Aksiyonlar'dan inceleyin."


def _toast(qapp):
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / "components" / "ToastNotification.qml")))
    assert component.isReady(), "; ".join(e.toString() for e in component.errors())
    item = component.create()
    window = QQuickWindow()  # yerleşim (polish) bir pencere olmadan çalışmaz
    window.resize(700, 300)
    item.setParentItem(window.contentItem())
    window.show()
    item._engine, item._component, item._window = engine, component, window  # kapsam dışına çıkıp silinmesin
    return item


def _pump():
    for _ in range(12):
        QCoreApplication.processEvents()


def _text(item):
    return item.findChild(QObject, "toastText")


@pytest.mark.parametrize("message", [LONG, "Kısa mesaj", "Çok uzun tek kelime " + "x" * 120])
def test_message_stays_inside_the_toast(qapp, message):
    item = _toast(qapp)
    item.show(message, True)
    _pump()
    text = _text(item)
    width = item.property("width")
    assert width <= 420
    assert text.property("x") >= 0 and text.property("x") + text.property("width") <= width + 0.5
    assert text.property("contentWidth") <= text.property("width") + 0.5, "metin kendi alanından taşıyor"
    assert item.property("height") >= text.property("contentHeight") + 16, "kutu yüksekliği metne uymuyor"


def test_long_message_wraps_and_short_message_keeps_the_single_line_height(qapp):
    item = _toast(qapp)
    item.show("Kısa mesaj", True)
    _pump()
    short_height = item.property("height")
    item.show(LONG, True)
    _pump()
    assert item.property("height") > short_height
    assert short_height == 46
