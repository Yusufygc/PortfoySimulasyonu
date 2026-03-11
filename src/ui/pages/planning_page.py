# src/ui/pages/planning_page.py

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTabWidget,
    QWidget,
    QFormLayout,
    QDoubleSpinBox,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QFrame,
    QDialog,
    QLineEdit,
    QDateEdit,
    QProgressBar,
    QSizePolicy,
)
from PyQt5.QtCore import Qt, QDate

from .base_page import BasePage


class PlanningPage(BasePage):
    """
    Finansal Planlama sayfası.
    QTabWidget ile iki ana modül sunar:
        1. Bütçe Yönetimi: Aylık gelir/gider takibi ve tasarruf analizi
        2. Hedef Takibi: Finansal hedef yönetimi ve fizibilite analizi
    """

    def __init__(self, planning_service, parent=None):
        super().__init__(parent)
        self.page_title = "Finansal Planlama"
        self._service = planning_service
        self._init_ui()

    def _init_ui(self):
        # Başlık
        header_layout = QHBoxLayout()
        lbl_title = QLabel("💰 Finansal Planlama")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #f1f5f9;")
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        self.main_layout.addLayout(header_layout)

        # Tab Widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #334155;
                border-radius: 8px;
                background-color: #0f172a;
            }
            QTabBar::tab {
                background-color: #1e293b;
                color: #94a3b8;
                padding: 10px 25px;
                margin-right: 3px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #3b82f6;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background-color: #334155;
                color: #f1f5f9;
            }
        """)

        # Sekme 1: Bütçe
        self.budget_tab = QWidget()
        self._build_budget_tab()
        self.tab_widget.addTab(self.budget_tab, "📊 Bütçe Yönetimi")

        # Sekme 2: Hedefler
        self.goals_tab = QWidget()
        self._build_goals_tab()
        self.tab_widget.addTab(self.goals_tab, "🎯 Hedef Takibi")

        self.main_layout.addWidget(self.tab_widget)

    # ====================================================================
    #                        BÜTÇE SEKMESİ
    # ====================================================================

    def _build_budget_tab(self):
        layout = QVBoxLayout(self.budget_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # --- Ay seçici + Kaydet ---
        top_row = QHBoxLayout()

        lbl_month = QLabel("📅 Ay:")
        lbl_month.setStyleSheet("color: #94a3b8; font-weight: bold; font-size: 14px;")
        top_row.addWidget(lbl_month)

        self.combo_month = QComboBox()
        self.combo_month.setMinimumWidth(150)
        self.combo_month.setMinimumHeight(36)
        self.combo_month.setStyleSheet("""
            QComboBox {
                background-color: #1e293b;
                color: #f1f5f9;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 14px;
            }
            QComboBox:hover { border: 1px solid #3b82f6; }
            QComboBox::drop-down { border: none; width: 25px; }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #94a3b8;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e293b; color: #f1f5f9;
                border: 1px solid #334155;
                selection-background-color: #3b82f6;
            }
        """)
        self._populate_months()
        self.combo_month.currentIndexChanged.connect(self._on_month_changed)
        top_row.addWidget(self.combo_month)

        top_row.addStretch()

        self.btn_save_budget = QPushButton("💾 Bütçeyi Kaydet")
        self.btn_save_budget.setCursor(Qt.PointingHandCursor)
        self.btn_save_budget.setMinimumHeight(38)
        self.btn_save_budget.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6; color: white; border: none;
                border-radius: 8px; font-weight: bold; padding: 8px 20px; font-size: 14px;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        self.btn_save_budget.clicked.connect(self._on_save_budget)
        top_row.addWidget(self.btn_save_budget)
        layout.addLayout(top_row)

        # --- Analiz kartları ---
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)

        self.card_income = self._create_info_card("💵 Toplam Gelir", "₺ 0")
        self.card_expense = self._create_info_card("💸 Toplam Gider", "₺ 0")
        self.card_savings = self._create_info_card("🏦 Tasarruf Potansiyeli", "₺ 0")

        cards_layout.addWidget(self.card_income)
        cards_layout.addWidget(self.card_expense)
        cards_layout.addWidget(self.card_savings)
        layout.addLayout(cards_layout)

        # --- Durum mesajı ---
        self.lbl_budget_status = QLabel("")
        self.lbl_budget_status.setStyleSheet("""
            background-color: #1e293b; color: #94a3b8;
            border-radius: 8px; padding: 12px; font-size: 14px;
        """)
        self.lbl_budget_status.setAlignment(Qt.AlignCenter)
        self.lbl_budget_status.setVisible(False)
        layout.addWidget(self.lbl_budget_status)

        # --- Form: Gelir/Gider ---
        form_frame = QFrame()
        form_frame.setStyleSheet("""
            QFrame { background-color: #1e293b; border-radius: 10px; }
        """)
        form_layout_outer = QVBoxLayout(form_frame)
        form_layout_outer.setContentsMargins(20, 15, 20, 15)

        # Gelirler
        lbl_income_header = QLabel("📥 Gelirler")
        lbl_income_header.setStyleSheet("color: #10b981; font-weight: bold; font-size: 14px;")
        form_layout_outer.addWidget(lbl_income_header)

        income_form = QHBoxLayout()
        income_form.setSpacing(20)
        self.spin_salary = self._create_money_spin("Maaş Geliri")
        self.spin_additional = self._create_money_spin("Ek Gelir")
        income_form.addLayout(self._labeled_spin("Maaş:", self.spin_salary))
        income_form.addLayout(self._labeled_spin("Ek Gelir:", self.spin_additional))
        form_layout_outer.addLayout(income_form)

        # Giderler
        lbl_expense_header = QLabel("📤 Giderler")
        lbl_expense_header.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 14px; margin-top: 10px;")
        form_layout_outer.addWidget(lbl_expense_header)

        expense_form1 = QHBoxLayout()
        expense_form1.setSpacing(20)
        self.spin_rent = self._create_money_spin("Kira/Konut")
        self.spin_bills = self._create_money_spin("Faturalar")
        self.spin_food = self._create_money_spin("Market/Mutfak")
        expense_form1.addLayout(self._labeled_spin("Kira:", self.spin_rent))
        expense_form1.addLayout(self._labeled_spin("Fatura:", self.spin_bills))
        expense_form1.addLayout(self._labeled_spin("Market:", self.spin_food))
        form_layout_outer.addLayout(expense_form1)

        expense_form2 = QHBoxLayout()
        expense_form2.setSpacing(20)
        self.spin_transport = self._create_money_spin("Ulaşım")
        self.spin_luxury = self._create_money_spin("Eğlence/Lüks")
        self.spin_target = self._create_money_spin("Hedef Tasarruf")
        expense_form2.addLayout(self._labeled_spin("Ulaşım:", self.spin_transport))
        expense_form2.addLayout(self._labeled_spin("Lüks:", self.spin_luxury))
        expense_form2.addLayout(self._labeled_spin("🎯 Hedef:", self.spin_target))
        form_layout_outer.addLayout(expense_form2)

        layout.addWidget(form_frame)
        layout.addStretch()

    def _populate_months(self):
        """Son 12 ayı ComboBox'a ekler."""
        now = datetime.now()
        for i in range(12):
            year = now.year
            month = now.month - i
            if month <= 0:
                month += 12
                year -= 1
            month_str = f"{year}-{month:02d}"
            self.combo_month.addItem(month_str, month_str)

    def _create_money_spin(self, placeholder: str = "") -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0, 10_000_000)
        spin.setDecimals(2)
        spin.setSuffix(" TL")
        spin.setMinimumHeight(36)
        spin.setMinimumWidth(140)
        spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #0f172a; color: #f1f5f9;
                border: 1px solid #334155; border-radius: 6px;
                padding: 6px; font-size: 14px;
            }
            QDoubleSpinBox:focus { border: 1px solid #3b82f6; }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                width: 18px; background-color: #334155; border: none; margin: 1px;
            }
        """)
        return spin

    @staticmethod
    def _labeled_spin(label_text: str, spin: QDoubleSpinBox) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(4)
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(lbl)
        layout.addWidget(spin)
        return layout

    def _create_info_card(self, title: str, value: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1e293b; border-radius: 10px;
                border: 1px solid #334155;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(5)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: bold; border: none;")
        lbl_value = QLabel(value)
        lbl_value.setObjectName("cardValue")
        lbl_value.setStyleSheet("color: #f1f5f9; font-size: 20px; font-weight: bold; border: none;")

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_value)
        return card

    def _on_month_changed(self):
        """Ay değiştiğinde mevcut veriyi yükler."""
        month = self.combo_month.currentData()
        if not month:
            return

        budget = self._service.get_budget_for_month(month)
        if budget:
            self.spin_salary.setValue(budget.income_salary)
            self.spin_additional.setValue(budget.income_additional)
            self.spin_rent.setValue(budget.expense_rent)
            self.spin_bills.setValue(budget.expense_bills)
            self.spin_food.setValue(budget.expense_food)
            self.spin_transport.setValue(budget.expense_transport)
            self.spin_luxury.setValue(budget.expense_luxury)
            self.spin_target.setValue(budget.savings_target)
            self._update_budget_cards(budget)
        else:
            # Sıfırla
            for spin in [self.spin_salary, self.spin_additional, self.spin_rent,
                         self.spin_bills, self.spin_food, self.spin_transport,
                         self.spin_luxury, self.spin_target]:
                spin.setValue(0.0)
            self._reset_budget_cards()

    def _on_save_budget(self):
        """Bütçeyi kaydet."""
        month = self.combo_month.currentData()
        if not month:
            return

        try:
            budget = self._service.save_budget(
                month=month,
                income_salary=self.spin_salary.value(),
                income_additional=self.spin_additional.value(),
                expense_rent=self.spin_rent.value(),
                expense_bills=self.spin_bills.value(),
                expense_food=self.spin_food.value(),
                expense_transport=self.spin_transport.value(),
                expense_luxury=self.spin_luxury.value(),
                savings_target=self.spin_target.value(),
            )
            self._update_budget_cards(budget)
            QMessageBox.information(self, "Başarılı", f"{month} bütçesi kaydedildi!")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Bütçe kaydedilemedi: {e}")

    def _update_budget_cards(self, budget):
        """Analiz kartlarını günceller."""
        income_lbl = self.card_income.findChild(QLabel, "cardValue")
        expense_lbl = self.card_expense.findChild(QLabel, "cardValue")
        savings_lbl = self.card_savings.findChild(QLabel, "cardValue")

        if income_lbl:
            income_lbl.setText(f"₺ {budget.total_income:,.2f}")
        if expense_lbl:
            expense_lbl.setText(f"₺ {budget.total_expense:,.2f}")

        net = budget.net_savings_potential
        if savings_lbl:
            savings_lbl.setText(f"₺ {net:,.2f}")
            color = "#10b981" if net >= 0 else "#ef4444"
            savings_lbl.setStyleSheet(f"color: {color}; font-size: 20px; font-weight: bold; border: none;")

        self.lbl_budget_status.setText(budget.status_message)
        self.lbl_budget_status.setVisible(True)

    def _reset_budget_cards(self):
        for card in [self.card_income, self.card_expense, self.card_savings]:
            lbl = card.findChild(QLabel, "cardValue")
            if lbl:
                lbl.setText("₺ 0")
                lbl.setStyleSheet("color: #f1f5f9; font-size: 20px; font-weight: bold; border: none;")
        self.lbl_budget_status.setVisible(False)

    # ====================================================================
    #                       HEDEF SEKMESİ
    # ====================================================================

    def _build_goals_tab(self):
        layout = QVBoxLayout(self.goals_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Üst butonlar
        top_row = QHBoxLayout()

        self.btn_add_goal = QPushButton("➕ Yeni Hedef")
        self.btn_add_goal.setCursor(Qt.PointingHandCursor)
        self.btn_add_goal.setMinimumHeight(38)
        self.btn_add_goal.setStyleSheet("""
            QPushButton {
                background-color: #10b981; color: white; border: none;
                border-radius: 8px; font-weight: bold; padding: 8px 20px; font-size: 14px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        self.btn_add_goal.clicked.connect(self._on_add_goal)
        top_row.addWidget(self.btn_add_goal)

        self.btn_contribute = QPushButton("💵 Katkı Ekle")
        self.btn_contribute.setCursor(Qt.PointingHandCursor)
        self.btn_contribute.setMinimumHeight(38)
        self.btn_contribute.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6; color: white; border: none;
                border-radius: 8px; font-weight: bold; padding: 8px 20px; font-size: 14px;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        self.btn_contribute.clicked.connect(self._on_contribute)
        top_row.addWidget(self.btn_contribute)

        self.btn_delete_goal = QPushButton("🗑️ Sil")
        self.btn_delete_goal.setCursor(Qt.PointingHandCursor)
        self.btn_delete_goal.setMinimumHeight(38)
        self.btn_delete_goal.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #ef4444; border: 1px solid #ef4444;
                border-radius: 8px; font-weight: bold; padding: 8px 16px; font-size: 14px;
            }
            QPushButton:hover { background-color: #ef4444; color: white; }
        """)
        self.btn_delete_goal.clicked.connect(self._on_delete_goal)
        top_row.addWidget(self.btn_delete_goal)

        top_row.addStretch()

        self.btn_analyze = QPushButton("📊 Fizibilite Analizi")
        self.btn_analyze.setCursor(Qt.PointingHandCursor)
        self.btn_analyze.setMinimumHeight(38)
        self.btn_analyze.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6; color: white; border: none;
                border-radius: 8px; font-weight: bold; padding: 8px 20px; font-size: 14px;
            }
            QPushButton:hover { background-color: #7c3aed; }
        """)
        self.btn_analyze.clicked.connect(self._on_analyze)
        top_row.addWidget(self.btn_analyze)

        layout.addLayout(top_row)

        # Fizibilite sonucu kartı
        self.feasibility_frame = QFrame()
        self.feasibility_frame.setStyleSheet("""
            QFrame {
                background-color: #1e293b; border-radius: 10px;
                border: 1px solid #334155;
            }
        """)
        feas_layout = QHBoxLayout(self.feasibility_frame)
        feas_layout.setContentsMargins(18, 12, 18, 12)

        self.lbl_feas_power = QLabel("Aylık Tasarruf Gücü: —")
        self.lbl_feas_power.setStyleSheet("color: #94a3b8; font-size: 14px; font-weight: bold; border: none;")
        self.lbl_feas_need = QLabel("Toplam Aylık İhtiyaç: —")
        self.lbl_feas_need.setStyleSheet("color: #94a3b8; font-size: 14px; font-weight: bold; border: none;")
        self.lbl_feas_status = QLabel("")
        self.lbl_feas_status.setStyleSheet("font-size: 14px; font-weight: bold; border: none;")

        feas_layout.addWidget(self.lbl_feas_power)
        feas_layout.addWidget(self.lbl_feas_need)
        feas_layout.addStretch()
        feas_layout.addWidget(self.lbl_feas_status)

        self.feasibility_frame.setVisible(False)
        layout.addWidget(self.feasibility_frame)

        # Hedefler tablosu
        self.goals_table = QTableWidget()
        self.goals_table.setColumnCount(7)
        self.goals_table.setHorizontalHeaderLabels([
            "Hedef", "Hedef Tutar", "Biriken", "Kalan Ay", "Aylık Gereken", "İlerleme", "Durum"
        ])
        self.goals_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, 7):
            self.goals_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.goals_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.goals_table.setAlternatingRowColors(True)
        self.goals_table.verticalHeader().setVisible(False)
        self.goals_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.goals_table)

    def _load_goals(self):
        """Hedef tablosunu doldurur."""
        self.goals_table.setRowCount(0)

        try:
            goals = self._service.get_all_goals()
        except Exception:
            return

        for i, goal in enumerate(goals):
            self.goals_table.insertRow(i)

            # Hedef adı
            item_name = QTableWidgetItem(goal.name)
            item_name.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item_name.setData(Qt.UserRole, goal.id)
            self.goals_table.setItem(i, 0, item_name)

            # Hedef tutar
            item_target = QTableWidgetItem(f"₺ {goal.target_amount:,.2f}")
            item_target.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item_target.setTextAlignment(Qt.AlignCenter)
            self.goals_table.setItem(i, 1, item_target)

            # Biriken
            item_saved = QTableWidgetItem(f"₺ {goal.current_amount:,.2f}")
            item_saved.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item_saved.setTextAlignment(Qt.AlignCenter)
            self.goals_table.setItem(i, 2, item_saved)

            # Kalan ay
            months = goal.months_remaining()
            item_months = QTableWidgetItem(f"{months} ay")
            item_months.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item_months.setTextAlignment(Qt.AlignCenter)
            if months == 0:
                item_months.setForeground(Qt.red)
            self.goals_table.setItem(i, 3, item_months)

            # Aylık gereken
            required = goal.required_monthly_contribution()
            item_req = QTableWidgetItem(f"₺ {required:,.2f}")
            item_req.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item_req.setTextAlignment(Qt.AlignCenter)
            self.goals_table.setItem(i, 4, item_req)

            # İlerleme (yüzde)
            progress_pct = goal.progress_ratio * 100
            item_progress = QTableWidgetItem(f"%{progress_pct:.1f}")
            item_progress.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item_progress.setTextAlignment(Qt.AlignCenter)
            if progress_pct >= 100:
                item_progress.setForeground(Qt.green)
            elif progress_pct >= 50:
                item_progress.setForeground(Qt.yellow)
            self.goals_table.setItem(i, 5, item_progress)

            # Durum
            item_status = QTableWidgetItem(goal.status)
            item_status.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item_status.setTextAlignment(Qt.AlignCenter)
            if goal.status == "COMPLETED":
                item_status.setForeground(Qt.green)
            self.goals_table.setItem(i, 6, item_status)

    def _on_add_goal(self):
        dialog = _GoalInputDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return

        result = dialog.get_result()
        if not result:
            return

        try:
            self._service.add_goal(
                name=result["name"],
                target_amount=result["target_amount"],
                deadline=result["deadline"],
                priority=result["priority"],
            )
            self._load_goals()
            QMessageBox.information(self, "Başarılı", f"'{result['name']}' hedefi eklendi!")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Hedef eklenemedi: {e}")

    def _on_contribute(self):
        """Seçili hedefe katkı ekler."""
        row = self.goals_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir hedef seçin.")
            return

        goal_id = self.goals_table.item(row, 0).data(Qt.UserRole)
        goal_name = self.goals_table.item(row, 0).text()

        dialog = _ContributionDialog(goal_name, self)
        if dialog.exec_() != QDialog.Accepted:
            return

        amount = dialog.get_amount()
        if amount <= 0:
            return

        try:
            self._service.add_contribution(goal_id, amount)
            self._load_goals()
            QMessageBox.information(self, "Başarılı", f"₺ {amount:,.2f} katkı eklendi!")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Katkı eklenemedi: {e}")

    def _on_delete_goal(self):
        """Seçili hedefi siler."""
        row = self.goals_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir hedef seçin.")
            return

        goal_id = self.goals_table.item(row, 0).data(Qt.UserRole)
        goal_name = self.goals_table.item(row, 0).text()

        reply = QMessageBox.question(
            self, "Hedef Sil",
            f"'{goal_name}' hedefini silmek istediğinizden emin misiniz?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            self._service.delete_goal(goal_id)
            self._load_goals()
            QMessageBox.information(self, "Başarılı", "Hedef silindi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Hedef silinemedi: {e}")

    def _on_analyze(self):
        """Fizibilite analizi yapar."""
        try:
            result = self._service.analyze_feasibility()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Analiz yapılamadı: {e}")
            return

        if "monthly_power" not in result:
            QMessageBox.information(self, "Bilgi", result.get("message", "Veri yok."))
            return

        self.feasibility_frame.setVisible(True)

        power = result["monthly_power"]
        need = result["total_monthly_need"]
        status = result["status"]

        self.lbl_feas_power.setText(f"Aylık Tasarruf Gücü: ₺ {power:,.2f}")
        self.lbl_feas_need.setText(f"Toplam Aylık İhtiyaç: ₺ {need:,.2f}")

        status_color = "#10b981" if status == "BAŞARILI" else "#ef4444"
        self.lbl_feas_status.setText(status)
        self.lbl_feas_status.setStyleSheet(
            f"color: {status_color}; font-size: 16px; font-weight: bold; border: none;"
        )

        # Tablodaki durum sütunlarını da güncelle
        self._load_goals()

    # ==================== Sayfa Olayları ==================== #

    def on_page_enter(self):
        self._on_month_changed()
        self._load_goals()

    def refresh_data(self):
        self._on_month_changed()
        self._load_goals()


# ====================================================================
#                          DİYALOGLAR
# ====================================================================


class _GoalInputDialog(QDialog):
    """Yeni hedef ekleme diyaloğu."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎯 Yeni Hedef")
        self.setFixedSize(420, 300)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #0f172a; }
            QLabel { color: #e2e8f0; font-weight: bold; font-size: 14px; }
            QLineEdit, QDoubleSpinBox, QDateEdit, QComboBox {
                background-color: #1e293b; color: #f1f5f9;
                border: 1px solid #334155; border-radius: 8px;
                padding: 8px; font-size: 14px; min-height: 25px;
            }
            QLineEdit:focus, QDoubleSpinBox:focus, QDateEdit:focus {
                border: 1px solid #3b82f6;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(25, 25, 25, 25)

        form = QFormLayout()
        form.setSpacing(12)

        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("Örn: Araba, Ev, Tatil...")
        form.addRow("Hedef Adı:", self.txt_name)

        self.spin_amount = QDoubleSpinBox()
        self.spin_amount.setRange(1, 100_000_000)
        self.spin_amount.setDecimals(2)
        self.spin_amount.setSuffix(" TL")
        self.spin_amount.setValue(50000)
        form.addRow("Hedef Tutar:", self.spin_amount)

        self.date_deadline = QDateEdit()
        self.date_deadline.setDate(QDate.currentDate().addMonths(12))
        self.date_deadline.setCalendarPopup(True)
        form.addRow("Hedef Tarih:", self.date_deadline)

        self.combo_priority = QComboBox()
        self.combo_priority.addItems(["LOW", "MEDIUM", "HIGH"])
        self.combo_priority.setCurrentIndex(1)
        form.addRow("Öncelik:", self.combo_priority)

        layout.addLayout(form)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet("background-color: #475569; color: white; padding: 8px 20px; border-radius: 6px;")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Ekle")
        btn_save.setStyleSheet("background-color: #10b981; color: white; padding: 8px 30px; border-radius: 6px; font-weight: bold;")
        btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def get_result(self):
        name = self.txt_name.text().strip()
        if not name:
            return None
        return {
            "name": name,
            "target_amount": self.spin_amount.value(),
            "deadline": self.date_deadline.date().toPyDate(),
            "priority": self.combo_priority.currentText(),
        }


class _ContributionDialog(QDialog):
    """Hedefe katkı ekleme diyaloğu."""

    def __init__(self, goal_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"💵 Katkı Ekle — {goal_name}")
        self.setFixedSize(350, 180)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #0f172a; }
            QLabel { color: #e2e8f0; font-weight: bold; font-size: 14px; }
            QDoubleSpinBox {
                background-color: #1e293b; color: #f1f5f9;
                border: 1px solid #334155; border-radius: 8px;
                padding: 10px; font-size: 16px; min-height: 30px;
            }
            QDoubleSpinBox:focus { border: 1px solid #3b82f6; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        lbl = QLabel("Eklenecek Tutar:")
        layout.addWidget(lbl)

        self.spin_amount = QDoubleSpinBox()
        self.spin_amount.setRange(0.01, 100_000_000)
        self.spin_amount.setDecimals(2)
        self.spin_amount.setSuffix(" TL")
        self.spin_amount.setValue(1000)
        layout.addWidget(self.spin_amount)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet("background-color: #475569; color: white; padding: 8px 20px; border-radius: 6px;")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Ekle")
        btn_save.setStyleSheet("background-color: #3b82f6; color: white; padding: 8px 30px; border-radius: 6px; font-weight: bold;")
        btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def get_amount(self) -> float:
        return self.spin_amount.value()
