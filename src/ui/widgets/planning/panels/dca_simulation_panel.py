"""
DCASimulationPanel — Düzenli Hisse Alımı (DCA) Backtest Paneli.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from src.qt_compat.qtcore import QThreadPool, Qt
from src.qt_compat.qtwidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from src.ui.shared.locale_tr import L10N
from src.ui.widgets.shared import InfoCard
from src.ui.worker import Worker

logger = logging.getLogger(__name__)


def _fmt_money(val) -> str:
    if val is None:
        return "—"
    try:
        return f"{float(val):,.2f} ₺"
    except Exception:
        return str(val)


def _fmt_pct(val) -> str:
    if val is None:
        return "—"
    try:
        v = float(val)
        prefix = "+" if v > 0 else ""
        return f"{prefix}{v:.2f}%"
    except Exception:
        return str(val)


class DCASimulationPanel(QFrame):
    """
    DCA (Dollar-Cost Averaging) / Düzenli Hisse Alımı Backtest Paneli.
    """

    def __init__(self, container, parent=None):
        super().__init__(parent)
        self.container = container
        self._dca_service = getattr(container, "dca_backtest_service", None)
        self._pool = QThreadPool()
        self._active_worker: Optional[Worker] = None
        self.setProperty("cssClass", "panelFrame")

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # Form Kartı
        form_card = QFrame()
        form_card.setProperty("cssClass", "card")
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(14, 12, 14, 12)
        form_layout.setSpacing(10)

        title_lbl = QLabel(L10N.DCA_SIMULATION_TITLE)
        title_lbl.setProperty("cssClass", "panelTitle")
        form_layout.addWidget(title_lbl)

        inputs_row = QHBoxLayout()
        inputs_row.setSpacing(12)

        # Hisseler
        ticker_col = QVBoxLayout()
        ticker_col.setSpacing(4)
        ticker_col.addWidget(QLabel(L10N.DCA_HINT_TICKERS))
        self._ticker_input = QLineEdit()
        self._ticker_input.setPlaceholderText("THYAO, FROTO, SISE, ASELS")
        self._ticker_input.setText("THYAO, FROTO, ASELS")
        ticker_col.addWidget(self._ticker_input)
        inputs_row.addLayout(ticker_col, 2)

        # Aylık Katkı Tutarı
        contrib_col = QVBoxLayout()
        contrib_col.setSpacing(4)
        contrib_col.addWidget(QLabel(L10N.DCA_MONTHLY_CONTRIB))
        self._spin_contrib = QDoubleSpinBox()
        self._spin_contrib.setProperty("cssClass", "customSpinBox")
        self._spin_contrib.setRange(100.0, 10_000_000.0)
        self._spin_contrib.setValue(5000.0)
        self._spin_contrib.setSingleStep(500.0)
        self._spin_contrib.setPrefix("₺ ")
        contrib_col.addWidget(self._spin_contrib)
        inputs_row.addLayout(contrib_col, 1)

        # Süre
        period_col = QVBoxLayout()
        period_col.setSpacing(4)
        period_col.addWidget(QLabel(L10N.DCA_PERIOD))
        self._combo_period = QComboBox()
        self._combo_period.setProperty("cssClass", "customComboBox")
        self._combo_period.addItem("Son 1 Yıl", 365)
        self._combo_period.addItem("Son 2 Yıl", 730)
        self._combo_period.addItem("Son 3 Yıl", 1095)
        self._combo_period.addItem("Son 5 Yıl", 1825)
        self._combo_period.setCurrentIndex(2)
        period_col.addWidget(self._combo_period)
        inputs_row.addLayout(period_col, 1)

        # Başlat Butonu
        btn_col = QVBoxLayout()
        btn_col.setSpacing(4)
        btn_col.addWidget(QLabel(" "))
        self._btn_run = QPushButton(L10N.DCA_RUN_BUTTON)
        self._btn_run.setProperty("cssClass", "primaryButton")
        self._btn_run.clicked.connect(self._on_run_clicked)
        btn_col.addWidget(self._btn_run)
        inputs_row.addLayout(btn_col, 1)

        form_layout.addLayout(inputs_row)
        main_layout.addWidget(form_card)

        # Durum Etiketi
        self._status_lbl = QLabel("")
        self._status_lbl.setProperty("cssClass", "pageDescription")
        main_layout.addWidget(self._status_lbl)

        # Özet Kartları
        self._cards_layout = QHBoxLayout()
        self._cards_layout.setSpacing(12)

        self._card_invested = InfoCard("Toplam Yatırılan", "0 ₺", icon_name="wallet")
        self._card_final_val = InfoCard("Nihai Portföy Değeri", "0 ₺", icon_name="trending-up")
        self._card_pl = InfoCard("Toplam Kâr / Zarar", "0 ₺ (0.00%)", icon_name="bar-chart-2")

        self._cards_layout.addWidget(self._card_invested)
        self._cards_layout.addWidget(self._card_final_val)
        self._cards_layout.addWidget(self._card_pl)
        main_layout.addLayout(self._cards_layout)

        # Hisse Bazlı Döküm Tablosu
        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels([
            "Hisse", "Toplam Alınan Lot", "Katkı Sayısı"
        ])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setProperty("cssClass", "customTable")
        main_layout.addWidget(self._table, 1)

    def _on_run_clicked(self) -> None:
        if self._dca_service is None:
            self._status_lbl.setText(L10N.DCA_SERVICE_NOT_FOUND)
            return

        raw_tickers = self._ticker_input.text()
        tickers = [t.strip().upper() for t in raw_tickers.split(",") if t.strip()]
        if not tickers:
            self._status_lbl.setText(L10N.DCA_ENTER_TICKER)
            return

        contrib_amount = Decimal(str(self._spin_contrib.value()))
        days = self._combo_period.currentData() or 1095
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        self._btn_run.setEnabled(False)
        self._status_lbl.setText(L10N.DCA_CALCULATING)

        worker = Worker(
            self._dca_service.run,
            tickers=tickers,
            monthly_contribution=contrib_amount,
            start_date=start_date,
            end_date=end_date,
        )
        worker.signals.result.connect(self._on_sim_done)
        worker.signals.error.connect(self._on_sim_error)
        worker.signals.cleanup.connect(self._on_sim_cleanup)
        self._active_worker = worker
        self._pool.start(worker)

    def _on_sim_done(self, result) -> None:
        self._card_invested.set_value(_fmt_money(result.total_invested))
        self._card_final_val.set_value(_fmt_money(result.final_value))
        pl = result.final_value - result.total_invested
        pl_pct = result.total_return_pct or 0.0
        pl_str = f"{_fmt_money(pl)} ({_fmt_pct(pl_pct)})"
        self._card_pl.set_value(pl_str)

        shares = getattr(result, "shares_by_ticker", {})
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(shares))

        for row_idx, (ticker, lot) in enumerate(shares.items()):
            cells = [
                QTableWidgetItem(ticker),
                QTableWidgetItem(f"{float(lot):,.2f}"),
                QTableWidgetItem(f"{result.contribution_count} Ay"),
            ]
            for col_idx, item in enumerate(cells):
                if col_idx > 0:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignCenter)
                self._table.setItem(row_idx, col_idx, item)

        self._table.setSortingEnabled(True)
        self._status_lbl.setText(L10N.DCA_SUCCESS)

    def _on_sim_error(self, err_tuple) -> None:
        logger.error("DCA Simülasyon hatası: %s", err_tuple[1])
        self._status_lbl.setText(f"Hata: {err_tuple[1]}")

    def _on_sim_cleanup(self) -> None:
        self._btn_run.setEnabled(True)
        self._active_worker = None
