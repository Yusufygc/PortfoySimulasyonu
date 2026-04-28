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
    - Toast, ebeveyn pencerenin SAĞ ALT köşesine overlay olarak yapışır.
    - Birden fazla toast üst üste yığılır (stacking).
    - 3.5 saniye sonra fade-out animasyonuyla kaybolur.
    - Kullanıcı üzerine tıklayarak da kapatabilir.
"""
from __future__ import annotations

from typing import ClassVar, List, Literal, Tuple

from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout, QPushButton
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, pyqtProperty
from PyQt5.QtGui import QFont, QColor

ToastType = Literal["success", "error", "warning", "info"]
ToastPosition = Literal["top", "bottom"]

# ──────────────────────────────────────────────────────────────
#  Sabitleri buradan değiştirerek tüm Toast görünümü güncellenir
# ──────────────────────────────────────────────────────────────
_STYLE: dict[str, dict] = {
    "success": {
        "bg":     "#064e3b",
        "border": "#10b981",
        "icon":   "✅",
        "label":  "Başarılı",
    },
    "error": {
        "bg":     "#450a0a",
        "border": "#ef4444",
        "icon":   "❌",
        "label":  "Hata",
    },
    "warning": {
        "bg":     "#451a03",
        "border": "#f59e0b",
        "icon":   "⚠️",
        "label":  "Uyarı",
    },
    "info": {
        "bg":     "#0c1a3d",
        "border": "#3b82f6",
        "icon":   "ℹ️",
        "label":  "Bilgi",
    },
}

_MARGIN   = 16   # Kenardan boşluk (px)
_SPACING  = 8    # Toastlar arası boşluk (px)
_DURATION = 3500 # Görünme süresi (ms)
_FADE_MS  = 300  # Fade animasyon süresi (ms)
_MAX_W    = 380  # Maksimum genişlik (px)


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
        position: ToastPosition = "bottom",
    ):
        # parentless floating window — ama parent'ı referans için saklıyoruz
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self._parent_ref = parent
        self._kind = kind
        self._position = position
        self._opacity_val: float = 0.0

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowOpacity(0.0)

        self._build_ui(message, kind)
        self._register()
        self._reposition_all()

        # Fade-in
        self._animate_opacity(0.0, 1.0, _FADE_MS)

        # Otomatik kapanma
        QTimer.singleShot(duration_ms, self._begin_close)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self, message: str, kind: ToastType) -> None:
        cfg = _STYLE[kind]

        container = QWidget(self)
        container.setObjectName("toastContainer")
        container.setStyleSheet(f"""
            QWidget#toastContainer {{
                background-color: {cfg['bg']};
                border: 1px solid {cfg['border']};
                border-left: 4px solid {cfg['border']};
                border-radius: 8px;
            }}
        """)

        row = QHBoxLayout(container)
        row.setContentsMargins(14, 10, 10, 10)
        row.setSpacing(10)

        lbl_icon = QLabel(cfg["icon"])
        lbl_icon.setStyleSheet("background: transparent; font-size: 16px; border: none;")
        lbl_icon.setFixedWidth(20)

        lbl_msg = QLabel(message)
        lbl_msg.setWordWrap(True)
        lbl_msg.setMaximumWidth(_MAX_W - 90)
        lbl_msg.setStyleSheet(f"""
            background: transparent;
            color: #f1f5f9;
            font-size: 13px;
            border: none;
        """)

        btn_close = QPushButton("×")
        btn_close.setFixedSize(20, 20)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94a3b8;
                font-size: 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { color: #f1f5f9; }
        """)
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
        self.close()
        # Kalan toastları yeniden konumlandır
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
        _ToastWidget._reposition_for_parent(self._parent_ref, self._position)

    @staticmethod
    def _reposition_for_parent(parent: QWidget, position: ToastPosition = "bottom") -> None:
        key = (id(parent), position)
        stack = _ToastWidget._registry.get(key, [])

        # Üst pencerenin global konumu
        if hasattr(parent, "centralWidget"):
            anchor = parent.centralWidget()
        else:
            anchor = parent
        global_pos = anchor.mapToGlobal(QPoint(0, 0))

        panel_w = anchor.width()
        panel_h = anchor.height()

        if position == "top":
            y_offset = global_pos.y() + _MARGIN
            for toast in stack:
                toast.adjustSize()
                w = min(toast.width(), _MAX_W)
                x = global_pos.x() + panel_w - w - _MARGIN
                y = y_offset
                toast.move(x, y)
                toast.show()
                y_offset = y + toast.height() + _SPACING
        else:
            y_offset = global_pos.y() + panel_h - _MARGIN
            for toast in reversed(stack):
                toast.adjustSize()
                w = min(toast.width(), _MAX_W)
                x = global_pos.x() + panel_w - w - _MARGIN
                y = y_offset - toast.height()
                toast.move(x, y)
                toast.show()
                y_offset = y - _SPACING

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
        position: ToastPosition = "bottom",
    ) -> None:
        _ToastWidget(message, "success", _root(parent), duration_ms, position)

    @staticmethod
    def error(
        parent: QWidget,
        message: str,
        duration_ms: int = _DURATION,
        position: ToastPosition = "bottom",
    ) -> None:
        _ToastWidget(message, "error", _root(parent), duration_ms, position)

    @staticmethod
    def warning(
        parent: QWidget,
        message: str,
        duration_ms: int = _DURATION,
        position: ToastPosition = "bottom",
    ) -> None:
        _ToastWidget(message, "warning", _root(parent), duration_ms, position)

    @staticmethod
    def info(
        parent: QWidget,
        message: str,
        duration_ms: int = _DURATION,
        position: ToastPosition = "bottom",
    ) -> None:
        _ToastWidget(message, "info", _root(parent), duration_ms, position)


def _root(widget: QWidget) -> QWidget:
    """En üst QMainWindow'u bul — Toast oraya çıpalar."""
    w = widget
    while w.parent() is not None:
        w = w.parent()
    return w
