"""Gerçek kullanıcı gibi davranan sürücü: Main.qml penceresinde fare tıklaması ve klavye olayı gönderir.

Denetleyici slotlarını doğrudan çağırmaz; ekranda görünen metni bulur, merkezine tıklar, alanlara klavye ile yazar.
Böylece QML bağlama hataları, örtülü düğmeler, görünmeyen öğeler ve yanlış tıklama alanları da yakalanır.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, List, Optional

from PySide6.QtCore import QCoreApplication, QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

_TEXT_CLASSES = ("QQuickText", "QQuickTextInput", "QQuickTextEdit", "QQuickLabel")


class Human:
    """Pencere üzerinde görünür öğeleri metne göre bulup tıklayan, yazan ve ekran görüntüsü alan test kullanıcısı."""

    def __init__(self, engine, controllers, container, shots_dir: Optional[Path] = None) -> None:
        self.engine = engine
        self.c = controllers
        self.container = container
        self.window = engine.rootObjects()[0]
        self.shots_dir = shots_dir

    # --- zaman ---------------------------------------------------------------------------------------------------
    def pump(self, rounds: int = 6, delay: float = 0.0) -> None:
        for _ in range(rounds):
            QCoreApplication.processEvents()
            if delay:
                time.sleep(delay)

    def wait_until(self, condition: Callable[[], bool], timeout: float = 8.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.pump(2, 0.01)
            if condition():
                return True
        return bool(condition())

    def settle(self, timeout: float = 6.0) -> None:
        """Arka plan işleri bitene kadar bekler (Portföyüm varlık işlemleri ve fiyat yenilemesi)."""
        assets = self.c.get("assetsController")
        self.wait_until(lambda: not getattr(assets, "busy", False), timeout)
        self.pump(8)

    # --- ağaç dolaşımı -------------------------------------------------------------------------------------------
    def _walk(self, root: QQuickItem):
        stack = [root]
        while stack:
            item = stack.pop()
            yield item
            stack.extend(reversed(item.childItems()))

    @staticmethod
    def _shown(item: QQuickItem) -> bool:
        node = item
        while node is not None:
            if not node.isVisible() or node.opacity() <= 0.01:
                return False
            node = node.parentItem()
        return item.width() > 0 and item.height() > 0

    def _inside_window(self, item: QQuickItem) -> bool:
        """Öğenin merkezi pencere sınırları içinde mi (kaydırma alanında görünür bölge dışına taşanları ayıklar)."""
        point = self.center_of(item)
        return 0 <= point.x() < self.window.width() and 0 <= point.y() < self.window.height()

    @staticmethod
    def _is_input(item: QQuickItem) -> bool:
        """TextInput/TextField/TextEdit ve bunlardan türeyen QML tipleri (ör. ModernInput) imleç özelliği taşır."""
        return item.property("cursorPosition") is not None

    @staticmethod
    def _shown_text(item: QQuickItem) -> str:
        """Ekranda görünen metin: parola alanlarında `text` gerçek değeri verir, `displayText` maskeli halini."""
        display = item.property("displayText")
        return str(display if display is not None else (item.property("text") or ""))

    def _is_text(self, item: QQuickItem) -> bool:
        return item.metaObject().className().startswith(_TEXT_CLASSES) or self._is_input(item)

    def items_with_text(self, needle: str, exact: bool = False, include_placeholder: bool = True) -> List[QQuickItem]:
        found = []
        for item in self._walk(self.window.contentItem()):
            if not self._is_text(item) or not self._shown(item):
                continue
            values = [self._shown_text(item)]
            if include_placeholder:
                values.append(str(item.property("placeholderText") or ""))
            if any((v == needle) if exact else (needle in v) for v in values if v):
                found.append(item)
        return found

    def inputs(self) -> List[dict]:
        """Görünen giriş alanları (yukarıdan aşağıya): değer, ipucu, konum. Keşif ve hata ayıklama içindir."""
        found = []
        for item in self._walk(self.window.contentItem()):
            if self._is_input(item) and self._shown(item):
                point = self.center_of(item)
                found.append({"text": str(item.property("text") or ""), "hint": str(item.property("placeholderText") or ""),
                              "x": point.x(), "y": point.y(), "focus": bool(item.property("activeFocus"))})
        return sorted(found, key=lambda d: (d["y"], d["x"]))

    def icon_buttons(self, name: str) -> List[QQuickItem]:
        """Metinsiz (simge) düğmeler: `tooltip` özelliği (erişilebilir ad ile aynı) `name` olan görünür öğeler."""
        return self._ordered([i for i in self._walk(self.window.contentItem())
                              if str(i.property("tooltip") or "") == name and self._shown(i) and self._inside_window(i)])

    def click_icon(self, name: str, nth: int = 0) -> None:
        """Simge düğmesine adıyla tıklar (koordinat yerine erişilebilir ad)."""
        buttons = self.icon_buttons(name)
        assert len(buttons) > nth, f"'{name}' simge düğmesi yok. Görünen: {self.visible_texts()[:40]}"
        self.click_item(buttons[nth])

    def visible_texts(self) -> List[str]:
        out = []
        for item in self._walk(self.window.contentItem()):
            if self._is_text(item) and self._shown(item):
                text = self._shown_text(item).strip()
                if text:
                    out.append(text)
        return out

    def page_text(self) -> str:
        return "\n".join(self.visible_texts())

    def sees(self, needle: str, exact: bool = False) -> bool:
        return bool(self.items_with_text(needle, exact=exact))

    def count(self, needle: str, exact: bool = False) -> int:
        return len(self.items_with_text(needle, exact=exact))

    def wait_sees(self, needle: str, timeout: float = 8.0, exact: bool = False) -> bool:
        return self.wait_until(lambda: self.sees(needle, exact), timeout)

    def wait_gone(self, needle: str, timeout: float = 8.0, exact: bool = False) -> bool:
        return self.wait_until(lambda: not self.sees(needle, exact), timeout)

    # --- fare ----------------------------------------------------------------------------------------------------
    def center_of(self, item: QQuickItem) -> QPoint:
        point = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
        return QPoint(int(point.x()), int(point.y()))

    def click_at(self, point: QPoint, button=Qt.LeftButton) -> None:
        # Gerçek fare gibi: önce imleci götür, bas, kısa süre sonra bırak (QQC2 düğmeleri üzerine gelmeden gelen anlık
        # tıklamayı bazen yutar).
        QTest.mouseMove(self.window, point)
        self.pump(4, 0.01)
        QTest.mousePress(self.window, button, Qt.NoModifier, point)
        self.pump(3, 0.02)
        QTest.mouseRelease(self.window, button, Qt.NoModifier, point)
        self.pump(12, 0.01)

    def click_item(self, item: QQuickItem) -> None:
        self.click_at(self.center_of(item))

    def click(self, text: str, nth: int = 0, exact: bool = False) -> None:
        """Ekrandaki `nth` eşleşmenin (üstten alta sıralı) ortasına tıklar; bulunamazsa AssertionError."""
        items = self._ordered([i for i in self.items_with_text(text, exact=exact) if self._inside_window(i)])
        assert len(items) > nth, f"Ekranda tıklanacak '{text}' yok. Görünen: {self.visible_texts()[:40]}"
        self.click_item(items[nth])

    def click_beside(self, anchor: str, text: str, exact: bool = True) -> None:
        """`anchor` (ör. İptal) ile aynı satırdaki `text` düğmesine tıklar: iletişim kutusunun onay düğmesi sayfadaki aynı
        adlı düğmeden ayrılır."""
        anchors = [i for i in self.items_with_text(anchor, exact=True) if self._inside_window(i)]
        assert anchors, f"'{anchor}' görünmüyor"
        row_y = self.center_of(self._ordered(anchors)[0]).y()
        candidates = [i for i in self.items_with_text(text, exact=exact) if abs(self.center_of(i).y() - row_y) <= 24]
        assert candidates, f"'{anchor}' satırında '{text}' yok. Görünen: {self.visible_texts()[-20:]}"
        self.click_item(min(candidates, key=lambda i: abs(self.center_of(i).y() - row_y)))

    def _ordered(self, items: List[QQuickItem]) -> List[QQuickItem]:
        def key(item):
            point = item.mapToScene(QPointF(0, 0))
            return (round(point.y()), round(point.x()))

        return sorted(items, key=key)

    def hover(self, text: str, nth: int = 0) -> None:
        items = self._ordered(self.items_with_text(text))
        assert len(items) > nth, f"Üzerine gelinecek '{text}' yok"
        QTest.mouseMove(self.window, self.center_of(items[nth]))
        self.pump(6)

    def scroll_down(self, at_text: Optional[str] = None, clicks: int = 3) -> None:
        from PySide6.QtCore import QPointF as PF
        from PySide6.QtGui import QWheelEvent
        from PySide6.QtWidgets import QApplication

        point = self.center_of(self.items_with_text(at_text)[0]) if at_text else QPoint(self.window.width() // 2, self.window.height() // 2)
        for _ in range(clicks):
            event = QWheelEvent(PF(point), PF(self.window.mapToGlobal(point)), QPoint(0, 0), QPoint(0, -120),
                                Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
            QApplication.sendEvent(self.window, event)
            self.pump(4)

    # --- klavye --------------------------------------------------------------------------------------------------
    def type(self, text: str) -> None:
        for char in text:
            if char.isascii():
                QTest.keyClick(self.window, char)
            else:
                # ASCII dışı karakter (ş, ğ, ı, ü ...) QTest.keyClick'te Latin-1'e bozulur; gerçek klavye gibi metinli olay gönder
                for kind in (QEvent.KeyPress, QEvent.KeyRelease):
                    QApplication.sendEvent(self.window, QKeyEvent(kind, 0, Qt.NoModifier, char))
            QCoreApplication.processEvents()
        self.pump(6, 0.01)

    def key(self, key, modifier=Qt.NoModifier) -> None:
        QTest.keyClick(self.window, key, modifier)
        self.pump(15, 0.01)

    def _input_items(self) -> List[QQuickItem]:
        items = [i for i in self._walk(self.window.contentItem()) if self._is_input(i) and self._shown(i)]
        return self._ordered(items)

    def field_below(self, label: str, nth: int = 0) -> QQuickItem:
        """`label` metninin altındaki (aynı sütun) ilk giriş alanı; insanın etiketi okuyup kutuya yazması gibi."""
        labels = self._ordered(self.items_with_text(label, include_placeholder=False))
        assert len(labels) > nth, f"Etiket '{label}' yok. Görünen: {self.visible_texts()[:40]}"
        lab = labels[nth]
        lab_pos = lab.mapToScene(QPointF(0, 0))
        best, best_dy = None, 10 ** 9
        for field in self._input_items():
            if field is lab:
                continue
            pos = field.mapToScene(QPointF(0, 0))
            dy = pos.y() - lab_pos.y()
            overlaps = pos.x() < lab_pos.x() + lab.width() + 4 and pos.x() + field.width() > lab_pos.x() - 4
            if overlaps and dy > 2 and dy < best_dy:
                best, best_dy = field, dy
        assert best is not None, f"'{label}' altında giriş alanı yok. Alanlar: {self.inputs()}"
        return best

    def type_into(self, field: QQuickItem, value: str, clear: bool = True) -> None:
        self.click_item(field)
        if clear:
            self.key(Qt.Key_A, Qt.ControlModifier)
            self.key(Qt.Key_Delete)
        if value:
            self.type(value)

    def fill(self, label: str, value: str, nth: int = 0) -> None:
        """Etiketin altındaki alanı doldurur."""
        self.type_into(self.field_below(label, nth), value)

    def fill_hint(self, hint: str, value: str, nth: int = 0) -> None:
        """İpucu metni (placeholder) ya da mevcut değerle bulunan alanı doldurur."""
        fields = [i for i in self._input_items()
                  if hint in str(i.property("placeholderText") or "") or hint == str(i.property("text") or "")]
        assert len(fields) > nth, f"Alan '{hint}' yok. Alanlar: {self.inputs()}"
        self.type_into(fields[nth], value)

    def value_of(self, label: str, nth: int = 0) -> str:
        return str(self.field_below(label, nth).property("text") or "")

    def press_enter(self) -> None:
        self.key(Qt.Key_Return)

    def escape(self) -> None:
        self.key(Qt.Key_Escape)

    CANCEL_LABELS = ("İptal", "Vazgeç")

    def cancel(self) -> None:
        """Açık iletişim kutusunu kapatır: İptal/Vazgeç düğmesi görünürse ona, değilse kutunun dışındaki karartmaya tıklar.

        Kutular Escape tuşuna yanıt vermez (bilinen UX eksiği, bkz. docs/wiki/product_test_plan.md bulgular).
        """
        labelled = [i for label in self.CANCEL_LABELS for i in self.items_with_text(label, exact=True)]
        if not labelled:
            return
        buttons = [i for i in labelled if self._inside_window(i)]
        if buttons:
            self.click_item(self._ordered(buttons)[0])
        else:
            self.click_at(QPoint(self.window.width() - 40, self.window.height() - 40))
        self.pump(20, 0.01)

    # --- görüntü -------------------------------------------------------------------------------------------------
    def screenshot(self, name: str) -> Optional[Path]:
        if self.shots_dir is None:
            return None
        self.shots_dir.mkdir(parents=True, exist_ok=True)
        path = self.shots_dir / f"{name}.png"
        self.pump(6)
        self.window.grabWindow().save(str(path))
        return path

    # --- kısa yollar ---------------------------------------------------------------------------------------------
    def open_page(self, title: str) -> None:
        """Kenar çubuğundan sayfa açar (yalnızca sol sütundaki etiket)."""
        sidebar_items = [i for i in self.items_with_text(title, exact=True)
                         if self.center_of(i).x() < self.window.width() * 0.25]
        assert sidebar_items, f"Kenar çubuğunda '{title}' yok. Görünen: {self.visible_texts()[:30]}"
        self.click_item(sidebar_items[0])
        self.pump(20, 0.005)

    @property
    def active_page(self) -> int:
        return int(self.c["shellController"].activePage)
