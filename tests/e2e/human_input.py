"""Sürücünün girdi yarısı: gerçek fare olayı, klavye olayı ve etiketten alan bulup doldurma."""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QCoreApplication, QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication


class InputMixin:
    """`ScreenReaderMixin` ile birlikte `Human` içinde kullanılır; `window` ve `pump` sağlayıcıdan gelir."""

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
