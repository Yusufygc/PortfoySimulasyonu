# src/ui/pages/planning_page.py

from __future__ import annotations
from src.ui.shared.locale_tr import L10N

from datetime import datetime

from PyQt5.QtWidgets import (
    QHBoxLayout, QPushButton, QLabel,
    QTabWidget, QWidget, QComboBox, QMessageBox, QDialog,
)
from PyQt5.QtCore import Qt, QSize

from .base_page import BasePage
from src.ui.widgets.planning import BudgetFormPanel, ContributionDialog, GoalInputDialog, GoalsPanel
from src.ui.widgets.shared import AnimatedButton, Toast
from src.ui.core.icon_manager import IconManager
from src.ui.widgets.shared.controls.icon_label import IconLabel


class PlanningPage(BasePage):
    """
    Finansal Planlama sayfası — koordinatör katmanı.
    Görsel yapı BudgetFormPanel ve GoalsPanel widget'larına devredilmiştir.
    Bu sınıf yalnızca servis çağrılarını ve event handler'ları koordine eder.
    """

    def __init__(self, container, parent=None):
        super().__init__(parent)
        self.container = container
        self.page_title = L10N.FINANSAL_PLANLAMA
        self._service = container.planning_service
        self._pinned_budget_items = []
        self._init_ui()

    # ------------------------------------------------------------------
    # UI Kurulumu
    # ------------------------------------------------------------------

    def _init_ui(self):
        header = QHBoxLayout()
        header.setSpacing(10)
        
        icon_lbl = IconLabel("wallet", color="@COLOR_ACCENT", size=28)
        header.addWidget(icon_lbl)
        
        lbl_title = QLabel(L10N.FINANSAL_PLANLAMA)
        lbl_title.setProperty("cssClass", "pageTitle")
        header.addWidget(lbl_title)
        header.addStretch()
        self.main_layout.addLayout(header)

        lbl_desc = QLabel(L10N.FINANSAL_DURUMUNUZU_ANALIZ_EDIN_BUTCENIZI)
        lbl_desc.setWordWrap(True)
        lbl_desc.setProperty("cssClass", "pageDescription")
        self.main_layout.addWidget(lbl_desc)

        self.tab_widget = QTabWidget()
        self.tab_widget.setProperty("cssClass", "mainTabWidget")

        # Sekme 1: Bütçe
        budget_tab = QWidget()
        self.tab_widget.addTab(budget_tab, L10N.BUTCE_YONETIMI)
        self._build_budget_tab(budget_tab)

        # Sekme 2: Hedefler
        goals_tab = QWidget()
        self.tab_widget.addTab(goals_tab, L10N.HEDEF_TAKIBI)
        self._build_goals_tab(goals_tab)

        self.tab_widget.currentChanged.connect(self._update_tab_icons)
        self._update_tab_icons()
        self.main_layout.addWidget(self.tab_widget)

    def _update_tab_icons(self, index: int = -1) -> None:
        idx = self.tab_widget.currentIndex() if index == -1 else index
        c0 = "@COLOR_TEXT_WHITE" if idx == 0 else "@COLOR_TEXT_SECONDARY"
        c1 = "@COLOR_TEXT_WHITE" if idx == 1 else "@COLOR_TEXT_SECONDARY"
        self.tab_widget.setTabIcon(0, IconManager.get_icon("list", color=c0))
        self.tab_widget.setTabIcon(1, IconManager.get_icon("target", color=c1))

    def _build_budget_tab(self, tab: QWidget) -> None:
        from PyQt5.QtWidgets import QVBoxLayout
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Ay seçici + Kaydet
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        
        icon_month = IconLabel("calendar", color="@COLOR_PRIMARY", size=18)
        top_row.addWidget(icon_month)
        
        lbl_month = QLabel(L10N.AY)
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

        btn_save = AnimatedButton(L10N.BUTCEYI_KAYDET)
        btn_save.setIconName("save", color="@COLOR_TEXT_WHITE", size=16)
        btn_save.setMinimumHeight(38)
        btn_save.setProperty("cssClass", "primaryButton")
        btn_save.clicked.connect(self._on_save_budget)
        top_row.addWidget(btn_save)
        layout.addLayout(top_row)

        # Durum mesajı
        self.lbl_budget_status = QLabel("")
        self.lbl_budget_status.setProperty("cssClass", "statusLabelInfo")
        self.lbl_budget_status.setAlignment(Qt.AlignCenter)
        self.lbl_budget_status.setVisible(False)
        layout.addWidget(self.lbl_budget_status)

        # Form paneli (BudgetFormPanel widget'ı)
        self.budget_form = BudgetFormPanel()
        self.budget_form.pin_toggle_requested.connect(self._on_budget_pin_toggled)
        layout.addWidget(self.budget_form, stretch=1)

    def _build_goals_tab(self, tab: QWidget) -> None:
        from PyQt5.QtWidgets import QVBoxLayout
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        self.goals_panel = GoalsPanel()
        self.goals_panel.add_requested.connect(self._on_add_goal)
        self.goals_panel.edit_requested.connect(self._on_edit_goal)
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
        self._pinned_budget_items = self._service.get_pinned_budget_items()
        self.budget_form.set_pinned_items(self._pinned_budget_items)
        budget = self._service.get_budget_for_month(month)
        if budget:
            self.budget_form.load(budget)
            self._update_budget_cards(budget)
        else:
            self.budget_form.load(self._service.get_budget_draft_from_pinned_items(month))
            self._update_budget_cards(None)

    def _on_save_budget(self) -> None:
        month = self.combo_month.currentData()
        if not month:
            return
        try:
            budget = self.budget_form.get_budget(month)
            saved = self._service.save_budget(budget)
            self._update_budget_cards(saved)
            Toast.success(self, f"{month} bütçesi kaydedildi!")
        except Exception as e:
            Toast.error(self, f"Bütçe kaydedilemedi: {e}")

    def _update_budget_cards(self, budget=None) -> None:
        if budget:
            self.lbl_budget_status.setText(budget.status_message)
            self.lbl_budget_status.setVisible(True)
        else:
            self.lbl_budget_status.setVisible(False)

    def _on_budget_pin_toggled(self, item_type: str, name: str, amount: float, pinned: bool) -> None:
        try:
            if pinned:
                self._service.pin_budget_item(item_type, name, amount)
                Toast.success(self, f"'{name}' pinlendi.")
            else:
                self._service.unpin_budget_item(item_type, name)
                Toast.success(f"'{name}' pini kaldırıldı.")
            self._pinned_budget_items = self._service.get_pinned_budget_items()
            self.budget_form.set_pinned_items(self._pinned_budget_items)
        except Exception as e:
            self.budget_form.set_pinned_items(self._pinned_budget_items)
            Toast.error(self, f"Pin işlemi başarısız: {e}")

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
            Toast.success(self, f"'{result['name']}' hedefi eklendi!")
        except Exception as e:
            Toast.error(self, f"Hedef eklenemedi: {e}")

    def _on_edit_goal(self, goal_id: int) -> None:
        if goal_id is None:
            return
        goal = next((g for g in self._service.get_all_goals() if g.id == goal_id), None)
        if not goal:
            return
        dialog = GoalInputDialog(self)
        dialog.load_goal(goal)
        if dialog.exec_() != QDialog.Accepted:
            return
        result = dialog.get_result()
        if not result:
            return
        try:
            self._service.update_goal(
                goal_id=goal_id,
                name=result["name"],
                target_amount=result["target_amount"],
                deadline=result["deadline"],
                priority=result["priority"],
            )
            self._load_goals()
            Toast.success(self, f"'{result['name']}' hedefi güncellendi!")
        except Exception as e:
            Toast.error(self, f"Hedef güncellenemedi: {e}")

    def _on_contribute(self, goal_id: int, goal_name: str) -> None:
        if goal_id is None:
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
            Toast.success(self, f"₺ {amount:,.2f} katkı eklendi!")
        except Exception as e:
            Toast.error(self, f"Katkı eklenemedi: {e}")

    def _on_delete_goal(self, goal_id: int, goal_name: str) -> None:
        if goal_id is None:
            return
        reply = QMessageBox.question(
            self, L10N.HEDEF_SIL,
            f"'{goal_name}' hedefini silmek istediğinizden emin misiniz?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            self._service.delete_goal(goal_id)
            self._load_goals()
            Toast.success(self, L10N.HEDEF_SILINDI)
        except Exception as e:
            Toast.error(self, f"Hedef silinemedi: {e}")

    def _on_analyze(self) -> None:
        try:
            result = self._service.analyze_feasibility()
        except Exception as e:
            Toast.error(self, f"Analiz yapılamadı: {e}")
            return
        if "monthly_power" not in result:
            Toast.info(self, result.get("message", L10N.VERI_YOK))
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
        self.refresh_data()

    def changeEvent(self, event):
        from PyQt5.QtCore import QEvent
        if event.type() == QEvent.StyleChange:
            self._update_tab_icons()
        super().changeEvent(event)

    def refresh_data(self):
        self._on_month_changed()
        self._load_goals()

