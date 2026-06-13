# src/ui/widgets/shared/feedback/toast.py
"""
Toast / Snackbar Bildirim Sistemi

QMessageBox.information / warning / critical çağrılarının modern,
kullanıcı akışını kesmez Toast bildirimleriyle değiştirilmesi için.

Kullanım (herhangi bir QWidget içinden):
    from src.ui.widgets.shared import Toast
    Toast.success(self, "İşlem başarıyla tamamlandı.")
    Toast.error(self, "Bir hata oluştu.")
    Toast.warning(self, "Dikkat!")
    Toast.info(self, "Bilgi mesajı.")

Mimari Notlar:
    - Toast, ebeveyn pencerenin SAĞ ÜST köşesine overlay olarak yapışır.
    - Birden fazla toast üst üste yığılır (stacking).
    - 3.5 saniye sonra fade-out animasyonuyla kaybolur.
    - Kullanıcı üzerine tıklayarak da kapatabilir.
"""
from __future__ import annotations

import re
from typing import ClassVar, List, Literal, Tuple

from src.qt_compat.qtwidgets import QWidget, QLabel, QHBoxLayout, QToolButton
from src.qt_compat.qtcore import QEvent, Qt, QTimer, QPropertyAnimation, QEasingCurve, QSize

from src.ui.widgets.shared.controls.icon_label import IconLabel

try:
    from shiboken6 import isValid as _qt_is_valid
except ImportError:  # pragma: no cover - PySide runtime provides shiboken6
    def _qt_is_valid(_obj) -> bool:
        return True

ToastType = Literal["success", "error", "warning", "info"]
ToastPosition = Literal["top", "bottom"]

# ──────────────────────────────────────────────────────────────
#  Sabitleri buradan değiştirerek tüm Toast görünümü güncellenir
# ──────────────────────────────────────────────────────────────
_STYLE: dict[str, dict] = {
    # Renk/border artık QSS'te (shared/feedback.qss — @TOAST_* token'ları).
    # Her iki tema için ayrı değerler ThemeManager tarafından çözülür.
    "success": {"icon_name": "shield-check", "icon_color": "@TOAST_SUCCESS_BORDER"},
    "error":   {"icon_name": "alert-triangle", "icon_color": "@TOAST_ERROR_BORDER"},
    "warning": {"icon_name": "alert-triangle", "icon_color": "@TOAST_WARNING_BORDER"},
    "info":    {"icon_name": "info", "icon_color": "@TOAST_INFO_BORDER"},
}

_MARGIN   = 18   # Kenardan boşluk (px)
_SPACING  = 8    # Toastlar arası boşluk (px)
_DURATION = 3500 # Görünme süresi (ms)
_FADE_MS  = 300  # Fade animasyon süresi (ms)
_MIN_W    = 460  # Minimum genişlik (px)
_MAX_W    = 620  # Maksimum genişlik (px)

_EMOJI_RANGES = (
    (0x1F000, 0x1FAFF),  # emoji blocks, symbols, pictographs
    (0x2600, 0x27BF),    # miscellaneous symbols and dingbats
)
_EMOJI_SYMBOL_CODEPOINTS = {
    0x00A9,
    0x00AE,
    0x203C,
    0x2049,
    0x2122,
    0x2139,
    0x3030,
    0x303D,
    0x3297,
    0x3299,
}
_EMOJI_JOINERS_AND_SELECTORS = {0x200D, 0x20E3, 0xFE0E, 0xFE0F}


class _ToastCloseButton(QToolButton):
    """Theme-aware SVG close button for toast notifications."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(26, 26)
        self.setIconSize(QSize(16, 16))
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("cssClass", "toastClose")
        self.setAutoRaise(True)
        self._refresh_icon()

    def _refresh_icon(self) -> None:
        from src.ui.core.icon_manager import IconManager

        self.setIcon(IconManager.get_icon("x", color="@TOAST_CLOSE_ICON", size=QSize(16, 16)))

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.StyleChange:
            self._refresh_icon()
        super().changeEvent(event)


class _ToastWidget(QWidget):
    """Tek bir Toast baloncuğu."""

    # Üst pencere başına açık toast listesi
    _registry: ClassVar[dict[Tuple[int, ToastPosition], List["_ToastWidget"]]] = {}

    def __init__(
        self,
        message: str,
        kind: ToastType,
        parent: QWidget,
        duration_ms: int = _DURATION,
        position: ToastPosition = "top",
    ):
        # Alt widget (child widget) olarak başlat
        anchor = self._anchor_for(parent)
        super().__init__(anchor)
        self._parent_ref = parent
        self._anchor_ref = anchor
        self._kind = kind
        self._position = position
        self._opacity_val: float = 0.0

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowOpacity(0.0)

        self._build_ui(_strip_emoji(message), kind)
        self._install_parent_filters()
        self._register()
        self._reposition_all()

        # Fade-in
        self._animate_opacity(0.0, 1.0, _FADE_MS)

        # Otomatik kapanma
        QTimer.singleShot(duration_ms, self._begin_close)

    def eventFilter(self, watched, event) -> bool:
        try:
            is_anchor_event = watched is self._parent_ref or watched is self._anchor_ref
            if is_anchor_event and event.type() in {
                QEvent.Move,
                QEvent.Resize,
                QEvent.Show,
                QEvent.WindowStateChange,
            }:
                QTimer.singleShot(0, self._reposition_all)
        except RuntimeError:
            return False
        return False

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self, message: str, kind: ToastType) -> None:
        cfg = _STYLE[kind]

        container = QWidget(self)
        container.setObjectName("toastContainer")
        # Renk/border QSS'te (shared/feedback.qss): toastKind property'si ile
        # her bildirim türü kendi @TOAST_* token'larını alır — tema-duyarlı.
        container.setProperty("toastKind", kind)

        row = QHBoxLayout(container)
        row.setContentsMargins(16, 12, 12, 12)
        row.setSpacing(12)

        lbl_icon = IconLabel(
            cfg["icon_name"],
            color=cfg["icon_color"],
            size=20,
        )
        lbl_icon.setProperty("cssClass", "toastIcon")
        lbl_icon.setFixedSize(24, 24)
        lbl_icon.setAlignment(Qt.AlignCenter)

        lbl_msg = QLabel(message)
        lbl_msg.setWordWrap(True)
        lbl_msg.setMinimumWidth(_MIN_W - 120)
        lbl_msg.setMaximumWidth(_MAX_W - 120)
        lbl_msg.setProperty("cssClass", "toastMessage")

        btn_close = _ToastCloseButton()
        btn_close.clicked.connect(self._begin_close)

        row.addWidget(lbl_icon, 0, Qt.AlignTop)
        row.addWidget(lbl_msg, 1)
        row.addWidget(btn_close, 0, Qt.AlignTop)

        # Ana layout
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(container)

        container.adjustSize()
        self.adjustSize()
        self.setMinimumWidth(_MIN_W)
        self.setMaximumWidth(_MAX_W)

    # ------------------------------------------------------------------
    # Animasyon
    # ------------------------------------------------------------------

    def _animate_opacity(self, start: float, end: float, duration: int) -> None:
        self._anim = QPropertyAnimation(self, b"windowOpacity")
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.setDuration(duration)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()

    def _begin_close(self) -> None:
        self._anim_out = QPropertyAnimation(self, b"windowOpacity")
        self._anim_out.setStartValue(self.windowOpacity())
        self._anim_out.setEndValue(0.0)
        self._anim_out.setDuration(_FADE_MS)
        self._anim_out.finished.connect(self._cleanup)
        self._anim_out.start()

    def _cleanup(self) -> None:
        key = (id(self._parent_ref), self._position)
        if key in _ToastWidget._registry:
            try:
                _ToastWidget._registry[key].remove(self)
            except ValueError:
                pass
            if not _ToastWidget._registry[key]:
                del _ToastWidget._registry[key]
        self._remove_parent_filters()
        try:
            self.close()
        except RuntimeError:
            pass
        # Kalan toastları yeniden konumlandır
        if _is_live_qobject(self._parent_ref):
            _ToastWidget._reposition_for_parent(self._parent_ref, self._position)

    # ------------------------------------------------------------------
    # Konumlandırma
    # ------------------------------------------------------------------

    def _register(self) -> None:
        key = (id(self._parent_ref), self._position)
        if key not in _ToastWidget._registry:
            _ToastWidget._registry[key] = []
        _ToastWidget._registry[key].append(self)

    def _reposition_all(self) -> None:
        if _is_live_qobject(self._parent_ref):
            _ToastWidget._reposition_for_parent(self._parent_ref, self._position)

    @staticmethod
    def _reposition_for_parent(parent: QWidget, position: ToastPosition = "top") -> None:
        if not _is_live_qobject(parent):
            return
        key = (id(parent), position)
        stack = _ToastWidget._registry.get(key, [])

        try:
            anchor = _ToastWidget._anchor_for(parent)
            if not _is_live_qobject(anchor):
                return

            panel_w = anchor.width()
            panel_h = anchor.height()
        except RuntimeError:
            return

        if position == "top":
            y_offset = _MARGIN
            for toast in list(stack):
                if not _is_live_qobject(toast):
                    continue
                try:
                    toast.adjustSize()
                    w = min(toast.width(), _MAX_W)
                    x = panel_w - w - _MARGIN
                    y = y_offset
                    toast.move(x, y)
                    toast.raise_()
                    toast.show()
                    y_offset = y + toast.height() + _SPACING
                except RuntimeError:
                    continue
        else:
            y_offset = panel_h - _MARGIN
            for toast in reversed(list(stack)):
                if not _is_live_qobject(toast):
                    continue
                try:
                    toast.adjustSize()
                    w = min(toast.width(), _MAX_W)
                    x = panel_w - w - _MARGIN
                    y = y_offset - toast.height()
                    toast.move(x, y)
                    toast.raise_()
                    toast.show()
                    y_offset = y - _SPACING
                except RuntimeError:
                    continue

    @staticmethod
    def _anchor_for(parent: QWidget) -> QWidget:
        try:
            if hasattr(parent, "centralWidget") and parent.centralWidget() is not None:
                return parent.centralWidget()
        except RuntimeError:
            return parent
        return parent

    def _install_parent_filters(self) -> None:
        for watched in {self._parent_ref, self._anchor_ref}:
            if not _is_live_qobject(watched):
                continue
            try:
                watched.installEventFilter(self)
            except RuntimeError:
                pass

    def _remove_parent_filters(self) -> None:
        for watched in {self._parent_ref, self._anchor_ref}:
            if not _is_live_qobject(watched):
                continue
            try:
                watched.removeEventFilter(self)
            except RuntimeError:
                pass

    def mouseReleaseEvent(self, event) -> None:
        self._begin_close()


# ──────────────────────────────────────────────────────────────
#  Public API
# ──────────────────────────────────────────────────────────────

class Toast:
    """
    Statik yardımcı sınıf — tek satırda toast bildirimi gösterir.

    Örnek:
        Toast.success(self, "Kayıt başarılı!")
        Toast.error(self, "Bağlantı hatası.")
    """

    @staticmethod
    def success(
        parent: QWidget,
        message: str,
        duration_ms: int = _DURATION,
        position: ToastPosition = "top",
    ) -> None:
        _ToastWidget(message, "success", _root(parent), duration_ms, position)

    @staticmethod
    def error(
        parent: QWidget,
        message: str,
        duration_ms: int = _DURATION,
        position: ToastPosition = "top",
    ) -> None:
        _ToastWidget(message, "error", _root(parent), duration_ms, position)

    @staticmethod
    def warning(
        parent: QWidget,
        message: str,
        duration_ms: int = _DURATION,
        position: ToastPosition = "top",
    ) -> None:
        _ToastWidget(message, "warning", _root(parent), duration_ms, position)

    @staticmethod
    def info(
        parent: QWidget,
        message: str,
        duration_ms: int = _DURATION,
        position: ToastPosition = "top",
    ) -> None:
        _ToastWidget(message, "info", _root(parent), duration_ms, position)


def _root(widget: QWidget) -> QWidget:
    """En üst QMainWindow'u bul — Toast oraya çıpalar."""
    w = widget
    while _is_live_qobject(w):
        try:
            parent = w.parent()
        except RuntimeError:
            break
        if parent is None:
            break
        w = parent
    return w


def _is_live_qobject(obj) -> bool:
    if obj is None:
        return False
    try:
        return bool(_qt_is_valid(obj))
    except (RuntimeError, TypeError):
        return False


def _strip_emoji(message: str) -> str:
    """Toast mesajını emoji karakterlerinden arındırır."""
    cleaned = "".join(ch for ch in str(message) if not _is_emoji_char(ch))
    return re.sub(r"\s{2,}", " ", cleaned).strip()


def _is_emoji_char(char: str) -> bool:
    codepoint = ord(char)
    if codepoint in _EMOJI_JOINERS_AND_SELECTORS or codepoint in _EMOJI_SYMBOL_CODEPOINTS:
        return True
    return any(start <= codepoint <= end for start, end in _EMOJI_RANGES)
