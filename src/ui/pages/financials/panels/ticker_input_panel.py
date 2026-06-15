"""Ticker giriş + "Getir" butonu paneli."""
from __future__ import annotations

from src.qt_compat.qtcore import Qt, pyqtSignal
from src.qt_compat.qtwidgets import (
    QComboBox,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QWidget,
)
from src.ui.shared.locale_tr import L10N


class TickerInputPanel(QWidget):
    """Kullanıcıdan BIST hisse kodu alır ve 'Getir' sinyali yayar."""

    fetch_requested = pyqtSignal(str, str)  # (ticker, currency)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        from src.qt_compat.qtwidgets import QLabel, QLineEdit
        lbl = QLabel(L10N.HISSE_KODU)
        lbl.setFixedWidth(80)
        layout.addWidget(lbl)

        self._ticker_edit = QLineEdit()
        self._ticker_edit.setPlaceholderText(L10N.HISSE_KODU_ORN_THYAO)
        self._ticker_edit.setMaximumWidth(160)
        self._ticker_edit.returnPressed.connect(self._on_fetch)
        layout.addWidget(self._ticker_edit)

        lbl_cur = QLabel(L10N.PARA_BIRIMI)
        layout.addWidget(lbl_cur)

        self._currency_combo = QComboBox()
        self._currency_combo.addItems(["TRY", "USD"])
        self._currency_combo.setMaximumWidth(80)
        layout.addWidget(self._currency_combo)

        self._btn_fetch = QPushButton(L10N.FINANSALLAR_GETIR)
        self._btn_fetch.setProperty("cssClass", "primaryButton")
        self._btn_fetch.clicked.connect(self._on_fetch)
        layout.addWidget(self._btn_fetch)

        layout.addStretch()

    def _on_fetch(self) -> None:
        ticker = self._ticker_edit.text().strip().upper()
        if not ticker:
            return
        currency = self._currency_combo.currentText()
        self.fetch_requested.emit(ticker, currency)

    def set_loading(self, loading: bool) -> None:
        self._btn_fetch.setEnabled(not loading)
        self._ticker_edit.setEnabled(not loading)
        self._currency_combo.setEnabled(not loading)
        self._btn_fetch.setText(
            L10N.YUKLENIYOR if loading else L10N.FINANSALLAR_GETIR
        )
