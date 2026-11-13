"""Sürücünün ekranı okuyan yarısı: öğe ağacında görünür metin, giriş alanı ve simge düğmelerini bulur."""
from __future__ import annotations

from typing import List

from PySide6.QtCore import QPoint, QPointF
from PySide6.QtQuick import QQuickItem

_TEXT_CLASSES = ("QQuickText", "QQuickTextInput", "QQuickTextEdit", "QQuickLabel")


class ScreenReaderMixin:
    """`window` ve `click_item` sağlayan sınıfa karıştırılır (bkz. `Human`)."""

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


    def center_of(self, item: QQuickItem) -> QPoint:
        point = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
        return QPoint(int(point.x()), int(point.y()))

    def _ordered(self, items: List[QQuickItem]) -> List[QQuickItem]:
        def key(item):
            point = item.mapToScene(QPointF(0, 0))
            return (round(point.y()), round(point.x()))

        return sorted(items, key=key)
