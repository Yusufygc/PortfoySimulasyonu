# src/ui/pages/optimization_page.py

from __future__ import annotations

from typing import Optional, List

from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QFrame,
    QProgressBar,
    QSizePolicy,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from .base_page import BasePage
from src.domain.models.optimization_result import OptimizationResult


class _OptimizationWorker(QThread):
    """
    Arka plan thread'inde optimizasyon çalıştırır.
    Ağır scipy hesaplaması ve yfinance ağ çağrıları UI'ı bloklamasın diye ayrı thread.
    """
    finished = pyqtSignal(object)   # OptimizationResult veya Exception
    error = pyqtSignal(str)

    def __init__(self, func, parent=None):
        super().__init__(parent)
        self._func = func

    def run(self):
        try:
            result = self._func()
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class OptimizationPage(BasePage):
    """
    Portföy Optimizasyonu sayfası.
    Markowitz Modern Portföy Teorisi ile Sharpe Oranını maximize eden
    optimal dağılımı hesaplar. Dashboard veya model portföyler üzerinde çalışır.
    """

    # Kaynak tipleri
    SOURCE_DASHBOARD = "dashboard"
    SOURCE_MODEL = "model"

    def __init__(
        self,
        optimization_service,
        price_lookup_func=None,
        parent=None,
    ):
        super().__init__(parent)
        self.page_title = "Portföy Optimizasyonu"
        self._optimization_service = optimization_service
        self._price_lookup_func = price_lookup_func
        self._worker: Optional[_OptimizationWorker] = None
        self._model_portfolios: list = []

        self._init_ui()

    def _init_ui(self):
        # ====== BAŞLIK ====== #
        header_layout = QHBoxLayout()
        lbl_title = QLabel("⚡ Portföy Optimizasyonu")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #f1f5f9;")
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        self.main_layout.addLayout(header_layout)

        # Açıklama
        lbl_desc = QLabel(
            "Markowitz Modern Portföy Teorisi kullanarak Sharpe Oranını\n"
            "maksimize eden optimal portföy ağırlıklarını hesaplar."
        )
        lbl_desc.setStyleSheet("color: #94a3b8; font-size: 13px; margin-bottom: 5px;")
        self.main_layout.addWidget(lbl_desc)

        # ====== KAYNAK SEÇİMİ ====== #
        source_frame = QFrame()
        source_frame.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        source_layout = QHBoxLayout(source_frame)
        source_layout.setContentsMargins(15, 12, 15, 12)
        source_layout.setSpacing(15)

        lbl_source = QLabel("📂 Kaynak:")
        lbl_source.setStyleSheet("color: #94a3b8; font-weight: bold; font-size: 14px;")
        source_layout.addWidget(lbl_source)

        self.combo_source = QComboBox()
        self.combo_source.setMinimumWidth(280)
        self.combo_source.setMinimumHeight(38)
        self.combo_source.setStyleSheet("""
            QComboBox {
                background-color: #0f172a;
                color: #f1f5f9;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
            }
            QComboBox:hover {
                border: 1px solid #3b82f6;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #94a3b8;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e293b;
                color: #f1f5f9;
                border: 1px solid #334155;
                selection-background-color: #3b82f6;
            }
        """)
        source_layout.addWidget(self.combo_source)
        source_layout.addStretch()

        self.btn_optimize = QPushButton("🚀 Optimize Et")
        self.btn_optimize.setCursor(Qt.PointingHandCursor)
        self.btn_optimize.setMinimumHeight(42)
        self.btn_optimize.setMinimumWidth(160)
        self.btn_optimize.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
                padding: 10px 25px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:disabled {
                background-color: #475569;
                color: #94a3b8;
            }
        """)
        self.btn_optimize.clicked.connect(self._on_optimize)
        source_layout.addWidget(self.btn_optimize)

        self.main_layout.addWidget(source_frame)

        # ====== PROGRESS BAR ====== #
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setMaximumHeight(4)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1e293b;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 2px;
            }
        """)
        self.progress_bar.setVisible(False)
        self.main_layout.addWidget(self.progress_bar)

        # ====== METRİK KARTLARI ====== #
        self.metrics_frame = QFrame()
        metrics_layout = QHBoxLayout(self.metrics_frame)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        metrics_layout.setSpacing(15)

        self.card_return = self._create_metric_card(
            "📈 Beklenen Yıllık Getiri", "—", "—", "—"
        )
        self.card_risk = self._create_metric_card(
            "📊 Risk (Volatilite)", "—", "—", "—"
        )
        self.card_sharpe = self._create_metric_card(
            "⭐ Sharpe Oranı", "—", "—", "—"
        )

        metrics_layout.addWidget(self.card_return)
        metrics_layout.addWidget(self.card_risk)
        metrics_layout.addWidget(self.card_sharpe)

        self.metrics_frame.setVisible(False)
        self.main_layout.addWidget(self.metrics_frame)

        # ====== ÖNERİLER TABLOSU ====== #
        self.lbl_suggestions = QLabel("📋 Önerilen Dağılım")
        self.lbl_suggestions.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #f1f5f9; margin-top: 5px;"
        )
        self.lbl_suggestions.setVisible(False)
        self.main_layout.addWidget(self.lbl_suggestions)

        self.suggestions_table = QTableWidget()
        self.suggestions_table.setColumnCount(5)
        self.suggestions_table.setHorizontalHeaderLabels([
            "Hisse", "Mevcut %", "Optimal %", "Fark", "Öneri"
        ])
        self.suggestions_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        for col in range(1, 5):
            self.suggestions_table.horizontalHeader().setSectionResizeMode(
                col, QHeaderView.ResizeToContents
            )
        self.suggestions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.suggestions_table.setAlternatingRowColors(True)
        self.suggestions_table.verticalHeader().setVisible(False)
        self.suggestions_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.suggestions_table.setVisible(False)
        self.main_layout.addWidget(self.suggestions_table)

        # Boş durum etiketi
        self.lbl_empty = QLabel(
            "Bir portföy kaynağı seçin ve 'Optimize Et' butonuna tıklayın."
        )
        self.lbl_empty.setStyleSheet("color: #64748b; font-size: 15px; padding: 40px;")
        self.lbl_empty.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.lbl_empty)

        self.main_layout.addStretch()

    # ==================== Metrik Kartı Oluşturma ==================== #

    def _create_metric_card(
        self, title: str, current_val: str, optimal_val: str, delta_val: str
    ) -> QFrame:
        """Mevcut vs Optimal karşılaştırmalı metrik kartı oluşturur."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border-radius: 10px;
                border: 1px solid #334155;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        # Başlık
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: bold; border: none;")
        layout.addWidget(lbl_title)

        # Mevcut değer
        row_current = QHBoxLayout()
        lbl_curr_label = QLabel("Mevcut:")
        lbl_curr_label.setStyleSheet("color: #64748b; font-size: 12px; border: none;")
        lbl_curr_value = QLabel(current_val)
        lbl_curr_value.setObjectName("currentValue")
        lbl_curr_value.setStyleSheet("color: #94a3b8; font-size: 14px; font-weight: bold; border: none;")
        row_current.addWidget(lbl_curr_label)
        row_current.addStretch()
        row_current.addWidget(lbl_curr_value)
        layout.addLayout(row_current)

        # Optimal değer
        row_optimal = QHBoxLayout()
        lbl_opt_label = QLabel("Optimal:")
        lbl_opt_label.setStyleSheet("color: #64748b; font-size: 12px; border: none;")
        lbl_opt_value = QLabel(optimal_val)
        lbl_opt_value.setObjectName("optimalValue")
        lbl_opt_value.setStyleSheet("color: #f1f5f9; font-size: 18px; font-weight: bold; border: none;")
        row_optimal.addWidget(lbl_opt_label)
        row_optimal.addStretch()
        row_optimal.addWidget(lbl_opt_value)
        layout.addLayout(row_optimal)

        # Delta
        lbl_delta = QLabel(delta_val)
        lbl_delta.setObjectName("deltaValue")
        lbl_delta.setStyleSheet("color: #94a3b8; font-size: 12px; border: none;")
        lbl_delta.setAlignment(Qt.AlignRight)
        layout.addWidget(lbl_delta)

        return card

    # ==================== Sayfa Olayları ==================== #

    def on_page_enter(self):
        """Sayfa aktif olduğunda kaynak listesini günceller."""
        self._load_sources()

    def refresh_data(self):
        self._load_sources()

    def _load_sources(self):
        """Kaynak ComboBox'ını doldurur."""
        self.combo_source.clear()
        self.combo_source.addItem("🏠 Dashboard Portföyü", self.SOURCE_DASHBOARD)

        try:
            self._model_portfolios = self._optimization_service.get_model_portfolios()
            for mp in self._model_portfolios:
                self.combo_source.addItem(
                    f"📊 {mp.name}", f"{self.SOURCE_MODEL}:{mp.id}"
                )
        except Exception:
            pass

    # ==================== Optimizasyon İşlemi ==================== #

    def _on_optimize(self):
        """Optimize Et butonuna tıklanınca çalışır."""
        source_data = self.combo_source.currentData()
        if source_data is None:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir portföy kaynağı seçin.")
            return

        self._set_loading(True)

        if source_data == self.SOURCE_DASHBOARD:
            func = self._optimization_service.optimize_dashboard_portfolio
        else:
            # model:ID formatı
            portfolio_id = int(source_data.split(":")[1])
            func = lambda pid=portfolio_id: self._optimization_service.optimize_model_portfolio(
                pid, self._price_lookup_func
            )

        self._worker = _OptimizationWorker(func, self)
        self._worker.finished.connect(self._on_optimization_finished)
        self._worker.error.connect(self._on_optimization_error)
        self._worker.start()

    def _on_optimization_finished(self, result: OptimizationResult):
        """Optimizasyon başarıyla tamamlandığında çağrılır."""
        self._set_loading(False)
        self._display_result(result)

    def _on_optimization_error(self, error_msg: str):
        """Optimizasyon hata verdiğinde çağrılır."""
        self._set_loading(False)
        QMessageBox.warning(self, "Optimizasyon Uyarısı", error_msg)

    def _set_loading(self, loading: bool):
        """Loading durumunu yönetir."""
        self.btn_optimize.setEnabled(not loading)
        self.btn_optimize.setText("⏳ Hesaplanıyor..." if loading else "🚀 Optimize Et")
        self.progress_bar.setVisible(loading)

    # ==================== Sonuç Gösterimi ==================== #

    def _display_result(self, result: OptimizationResult):
        """Optimizasyon sonucunu UI'da gösterir."""
        self.lbl_empty.setVisible(False)
        self.metrics_frame.setVisible(True)
        self.lbl_suggestions.setVisible(True)
        self.suggestions_table.setVisible(True)

        curr = result.current_metrics
        opt = result.optimized_metrics

        # --- Getiri kartı ---
        self._update_metric_card(
            self.card_return,
            current_val=f"%{curr.expected_return * 100:.2f}",
            optimal_val=f"%{opt.expected_return * 100:.2f}",
            delta=(opt.expected_return - curr.expected_return) * 100,
            positive_is_good=True,
        )

        # --- Risk kartı (düşük daha iyi) ---
        self._update_metric_card(
            self.card_risk,
            current_val=f"%{curr.volatility * 100:.2f}",
            optimal_val=f"%{opt.volatility * 100:.2f}",
            delta=(curr.volatility - opt.volatility) * 100,  # Ters: azalma iyi
            positive_is_good=True,
        )

        # --- Sharpe kartı ---
        self._update_metric_card(
            self.card_sharpe,
            current_val=f"{curr.sharpe_ratio:.3f}",
            optimal_val=f"{opt.sharpe_ratio:.3f}",
            delta=opt.sharpe_ratio - curr.sharpe_ratio,
            positive_is_good=True,
        )

        # --- Öneriler tablosu ---
        self._populate_suggestions_table(result.suggestions)

    def _update_metric_card(
        self,
        card: QFrame,
        current_val: str,
        optimal_val: str,
        delta: float,
        positive_is_good: bool = True,
    ):
        """Metrik kartının değerlerini günceller."""
        lbl_current = card.findChild(QLabel, "currentValue")
        lbl_optimal = card.findChild(QLabel, "optimalValue")
        lbl_delta = card.findChild(QLabel, "deltaValue")

        if lbl_current:
            lbl_current.setText(current_val)
        if lbl_optimal:
            lbl_optimal.setText(optimal_val)

        if lbl_delta:
            is_positive = delta > 0
            is_good = is_positive if positive_is_good else not is_positive

            color = "#10b981" if is_good else "#ef4444"
            arrow = "▲" if is_positive else "▼"
            lbl_delta.setText(f"{arrow} {abs(delta):+.2f}")
            lbl_delta.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: bold; border: none;")

    def _populate_suggestions_table(self, suggestions):
        """Öneriler tablosunu doldurur."""
        self.suggestions_table.setRowCount(0)

        for i, sug in enumerate(suggestions):
            self.suggestions_table.insertRow(i)

            # Hisse
            item_symbol = QTableWidgetItem(sug.symbol)
            item_symbol.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.suggestions_table.setItem(i, 0, item_symbol)

            # Mevcut %
            item_current = QTableWidgetItem(f"{sug.current_weight:.2f}%")
            item_current.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item_current.setTextAlignment(Qt.AlignCenter)
            self.suggestions_table.setItem(i, 1, item_current)

            # Optimal %
            item_optimal = QTableWidgetItem(f"{sug.optimal_weight:.2f}%")
            item_optimal.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item_optimal.setTextAlignment(Qt.AlignCenter)
            item_optimal.setForeground(Qt.white)
            self.suggestions_table.setItem(i, 2, item_optimal)

            # Fark
            item_change = QTableWidgetItem(f"{sug.change:+.2f}%")
            item_change.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item_change.setTextAlignment(Qt.AlignCenter)
            change_color = Qt.green if sug.change > 0 else Qt.red if sug.change < 0 else Qt.gray
            item_change.setForeground(change_color)
            self.suggestions_table.setItem(i, 3, item_change)

            # Öneri (Aksiyon)
            item_action = QTableWidgetItem(sug.action)
            item_action.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item_action.setTextAlignment(Qt.AlignCenter)

            if sug.action == "EKLE":
                item_action.setForeground(Qt.green)
            elif sug.action == "AZALT":
                item_action.setForeground(Qt.red)
            else:
                item_action.setForeground(Qt.gray)

            self.suggestions_table.setItem(i, 4, item_action)
