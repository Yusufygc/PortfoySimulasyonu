# src/ui/pages/planning_page.py

from __future__ import annotations

from datetime import datetime

from PyQt5.QtWidgets import (
    QHBoxLayout, QPushButton, QLabel,
    QTabWidget, QWidget, QComboBox, QMessageBox, QDialog,
)
from PyQt5.QtCore import Qt

from .base_page import BasePage
from src.ui.widgets.cards import InfoCard
from src.ui.widgets.panels import BudgetFormPanel, GoalsPanel
from src.ui.widgets.goal_input_dialog import GoalInputDialog
from src.ui.widgets.contribution_dialog import ContributionDialog


class PlanningPage(BasePage):
    """
    Finansal Planlama sayfası — koordinatör katmanı.
    Görsel yapı BudgetFormPanel ve GoalsPanel widget'larına devredilmiştir.
    Bu sınıf yalnızca servis çağrılarını ve event handler'ları koordine eder.
    """

    def __init__(self, container, parent=None):
        super().__init__(parent)
        self.container = container
        self.page_title = "Finansal Planlama"
        self._service = container.planning_service
        self._init_ui()

    # ------------------------------------------------------------------
    # UI Kurulumu
    # ------------------------------------------------------------------

    def _init_ui(self):
        header = QHBoxLayout()
        lbl_title = QLabel("💰 Finansal Planlama")
        lbl_title.setProperty("cssClass", "pageTitle")
        header.addWidget(lbl_title)
        header.addStretch()
        self.main_layout.addLayout(header)

        self.tab_widget = QTabWidget()
        self.tab_widget.setProperty("cssClass", "mainTabWidget")

        # Sekme 1: Bütçe
        budget_tab = QWidget()
        self.tab_widget.addTab(budget_tab, "📊 Bütçe Yönetimi")
        self._build_budget_tab(budget_tab)

        # Sekme 2: Hedefler
        goals_tab = QWidget()
        self.tab_widget.addTab(goals_tab, "🎯 Hedef Takibi")
        self._build_goals_tab(goals_tab)

        self.main_layout.addWidget(self.tab_widget)

    def _build_budget_tab(self, tab: QWidget) -> None:
        from PyQt5.QtWidgets import QVBoxLayout
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Ay seçici + Kaydet
        top_row = QHBoxLayout()
        lbl_month = QLabel("📅 Ay:")
        lbl_month.setProperty("cssClass", "panelTitle")
        top_row.addWidget(lbl_month)

        self.combo_month = QComboBox()
        self.combo_month.setMinimumWidth(150)
        self.combo_month.setMinimumHeight(36)
        self.combo_month.setProperty("cssClass", "customComboBox")
        self._populate_months()
        self.combo_month.currentIndexChanged.connect(self._on_month_changed)
        top_row.addWidget(self.combo_month)
        top_row.addStretch()

        btn_save = QPushButton("💾 Bütçeyi Kaydet")
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setMinimumHeight(38)
        btn_save.setProperty("cssClass", "primaryButton")
        btn_save.clicked.connect(self._on_save_budget)
        top_row.addWidget(btn_save)
        layout.addLayout(top_row)

        # Özet kartları
        cards_row = QHBoxLayout()
        cards_row.setSpacing(15)
        self.card_income  = InfoCard("💵 Toplam Gelir",          "₺ 0")
        self.card_expense = InfoCard("💸 Toplam Gider",          "₺ 0")
        self.card_savings = InfoCard("🏦 Tasarruf Potansiyeli",  "₺ 0")
        for card in (self.card_income, self.card_expense, self.card_savings):
            cards_row.addWidget(card)
        layout.addLayout(cards_row)

        # Durum mesajı
        self.lbl_budget_status = QLabel("")
        self.lbl_budget_status.setProperty("cssClass", "statusLabelInfo")
        self.lbl_budget_status.setAlignment(Qt.AlignCenter)
        self.lbl_budget_status.setVisible(False)
        layout.addWidget(self.lbl_budget_status)

        # Form paneli (BudgetFormPanel widget'ı)
        self.budget_form = BudgetFormPanel()
        layout.addWidget(self.budget_form)
        layout.addStretch()

    def _build_goals_tab(self, tab: QWidget) -> None:
        from PyQt5.QtWidgets import QVBoxLayout
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        self.goals_panel = GoalsPanel()
        self.goals_panel.add_requested.connect(self._on_add_goal)
        self.goals_panel.contribute_requested.connect(self._on_contribute)
        self.goals_panel.delete_requested.connect(self._on_delete_goal)
        self.goals_panel.analyze_requested.connect(self._on_analyze)
        layout.addWidget(self.goals_panel)

    # ------------------------------------------------------------------
    # Yardımcılar
    # ------------------------------------------------------------------

    def _populate_months(self) -> None:
        now = datetime.now()
        for i in range(12):
            year = now.year
            month = now.month - i
            if month <= 0:
                month += 12
                year -= 1
            month_str = f"{year}-{month:02d}"
            self.combo_month.addItem(month_str, month_str)

    # ------------------------------------------------------------------
    # Bütçe Event Handler'ları
    # ------------------------------------------------------------------

    def _on_month_changed(self) -> None:
        month = self.combo_month.currentData()
        if not month:
            return
        budget = self._service.get_budget_for_month(month)
        if budget:
            self.budget_form.load(budget)
            self._update_budget_cards(budget)
        else:
            self.budget_form.reset()
            self._reset_budget_cards()

    def _on_save_budget(self) -> None:
        month = self.combo_month.currentData()
        if not month:
            return
        try:
            budget = self._service.save_budget(month=month, **self.budget_form.get_values())
            self._update_budget_cards(budget)
            QMessageBox.information(self, "Başarılı", f"{month} bütçesi kaydedildi!")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Bütçe kaydedilemedi: {e}")

    def _update_budget_cards(self, budget) -> None:
        self.card_income.set_value(f"₺ {budget.total_income:,.2f}")
        self.card_expense.set_value(f"₺ {budget.total_expense:,.2f}")
        net = budget.net_savings_potential
        self.card_savings.set_value(f"₺ {net:,.2f}")
        self.card_savings.set_value_state("positive" if net >= 0 else "negative")
        self.lbl_budget_status.setText(budget.status_message)
        self.lbl_budget_status.setVisible(True)

    def _reset_budget_cards(self) -> None:
        for card in (self.card_income, self.card_expense, self.card_savings):
            card.set_value("₺ 0")
            card.set_value_state("neutral")
        self.lbl_budget_status.setVisible(False)

    # ------------------------------------------------------------------
    # Hedef Event Handler'ları
    # ------------------------------------------------------------------

    def _on_add_goal(self) -> None:
        dialog = GoalInputDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        result = dialog.get_result()
        if not result:
            return
        try:
            self._service.add_goal(**result)
            self._load_goals()
            QMessageBox.information(self, "Başarılı", f"'{result['name']}' hedefi eklendi!")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Hedef eklenemedi: {e}")

    def _on_contribute(self, goal_id: int, goal_name: str) -> None:
        if goal_id is None:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir hedef seçin.")
            return
        dialog = ContributionDialog(goal_name, self)
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

    def _on_delete_goal(self, goal_id: int, goal_name: str) -> None:
        if goal_id is None:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir hedef seçin.")
            return
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

    def _on_analyze(self) -> None:
        try:
            result = self._service.analyze_feasibility()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Analiz yapılamadı: {e}")
            return
        if "monthly_power" not in result:
            QMessageBox.information(self, "Bilgi", result.get("message", "Veri yok."))
            return
        self.goals_panel.show_feasibility(result)
        self._load_goals()

    def _load_goals(self) -> None:
        try:
            goals = self._service.get_all_goals()
            self.goals_panel.load(goals)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Sayfa Yaşam Döngüsü
    # ------------------------------------------------------------------

    def on_page_enter(self):
        self._on_month_changed()
        self._load_goals()

    def refresh_data(self):
        self._on_month_changed()
        self._load_goals()
