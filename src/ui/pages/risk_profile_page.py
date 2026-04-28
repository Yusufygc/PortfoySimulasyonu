# src/ui/pages/risk_profile_page.py

from __future__ import annotations

from typing import Dict, Optional

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
)

from .base_page import BasePage
from src.application.services.planning.risk_profile_service import DIMENSION_LABELS
from src.domain.models.risk_profile import RiskProfile
from src.ui.core.icon_manager import IconManager
from src.ui.widgets.shared import Toast


SECTION_ICONS = {
    "Finansal Durum": "wallet",
    "Yatirim Hedefi": "target",
    "Risk Toleransi": "trending-down",
    "Bilgi ve Tecrube": "line-chart",
}


class RiskProfilePage(BasePage):
    """MiFID benzeri profesyonel risk profili anketi sayfasi."""

    def __init__(self, container, parent=None):
        super().__init__(parent)
        self.container = container
        self.page_title = "Risk Profili"
        self._service = container.risk_profile_service
        self.questionnaire_sections = list(self._service.get_questionnaire())
        self.questionnaire_items = [
            (section.title, question)
            for section in self.questionnaire_sections
            for question in section.questions
        ]
        self.current_question_index = 0
        self.answer_groups: Dict[str, QButtonGroup] = {}
        self._init_ui()

    def _init_ui(self):
        header = QHBoxLayout()
        header.setSpacing(10)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(
            IconManager.get_icon("shield-check", color="@COLOR_ACCENT", size=QSize(28, 28)).pixmap(28, 28)
        )
        header.addWidget(icon_lbl)

        lbl_title = QLabel("Risk Profil Analizi")
        lbl_title.setProperty("cssClass", "pageTitle")
        header.addWidget(lbl_title)
        header.addStretch()
        self.main_layout.addLayout(header)

        lbl_desc = QLabel(
            "Finansal durum, hedef, risk toleransi ve tecrube yanitlarinizla profesyonel risk profilinizi hesaplayin."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setProperty("cssClass", "pageDescription")
        self.main_layout.addWidget(lbl_desc)

        self._build_profile_card()
        self._build_survey()

    def _build_profile_card(self):
        self.profile_card = QFrame()
        self.profile_card.setProperty("cssClass", "profileCard")
        card_layout = QVBoxLayout(self.profile_card)
        card_layout.setContentsMargins(22, 16, 22, 16)
        card_layout.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setSpacing(16)

        score_col = QVBoxLayout()
        score_col.setSpacing(4)
        self.lbl_profile_header = QLabel("Mevcut Profiliniz")
        self.lbl_profile_header.setProperty("cssClass", "profileHeader")
        self.lbl_score = QLabel("Puan: -")
        self.lbl_score.setProperty("cssClass", "profileScore")
        score_col.addWidget(self.lbl_profile_header)
        score_col.addWidget(self.lbl_score)
        header_row.addLayout(score_col, 1)

        self.lbl_label = QLabel("")
        self.lbl_label.setProperty("cssClass", "profileLabel")
        self.lbl_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header_row.addWidget(self.lbl_label, 0)
        card_layout.addLayout(header_row)

        self.lbl_profile_desc = QLabel("")
        self.lbl_profile_desc.setWordWrap(True)
        self.lbl_profile_desc.setProperty("cssClass", "profileDesc")
        card_layout.addWidget(self.lbl_profile_desc)

        self.dimension_grid = QGridLayout()
        self.dimension_grid.setHorizontalSpacing(10)
        self.dimension_grid.setVerticalSpacing(8)
        self.dimension_labels: Dict[str, QLabel] = {}
        for index, (dimension, label) in enumerate(DIMENSION_LABELS.items()):
            card, value = self._create_dimension_metric(label)
            self.dimension_grid.addWidget(card, index // 4, index % 4)
            self.dimension_grid.setColumnStretch(index % 4, 1)
            self.dimension_labels[dimension] = value
        card_layout.addLayout(self.dimension_grid)

        allocation_block = QFrame()
        allocation_block.setProperty("cssClass", "profileInfoBlock")
        allocation_layout = QVBoxLayout(allocation_block)
        allocation_layout.setContentsMargins(12, 8, 12, 9)
        allocation_layout.setSpacing(4)
        allocation_title = QLabel("Ornek Dagilim")
        allocation_title.setProperty("cssClass", "profileInfoTitle")
        allocation_layout.addWidget(allocation_title)
        self.lbl_allocation = QLabel("")
        self.lbl_allocation.setWordWrap(True)
        self.lbl_allocation.setProperty("cssClass", "profileDesc")
        allocation_layout.addWidget(self.lbl_allocation)
        card_layout.addWidget(allocation_block)

        notes_block = QFrame()
        notes_block.setProperty("cssClass", "profileInfoBlock")
        self.notes_block = notes_block
        notes_layout = QVBoxLayout(notes_block)
        notes_layout.setContentsMargins(12, 8, 12, 9)
        notes_layout.setSpacing(4)
        notes_title = QLabel("Uygunluk Notlari")
        notes_title.setProperty("cssClass", "profileInfoTitle")
        notes_layout.addWidget(notes_title)
        self.lbl_notes = QLabel("")
        self.lbl_notes.setWordWrap(True)
        self.lbl_notes.setProperty("cssClass", "profileDetail")
        notes_layout.addWidget(self.lbl_notes)
        card_layout.addWidget(notes_block)

        self.profile_card.setVisible(False)
        self.main_layout.addWidget(self.profile_card)

    @staticmethod
    def _create_dimension_metric(title: str) -> tuple[QFrame, QLabel]:
        card = QFrame()
        card.setProperty("cssClass", "profileMetricCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        lbl_title = QLabel(title)
        lbl_title.setProperty("cssClass", "profileMetricTitle")
        layout.addWidget(lbl_title)

        lbl_value = QLabel("-")
        lbl_value.setProperty("cssClass", "profileMetricValue")
        layout.addWidget(lbl_value)
        return card, lbl_value

    def _build_survey(self):
        self.survey_frame = QFrame()
        self.survey_frame.setProperty("cssClass", "surveyFrame")
        survey_layout = QVBoxLayout(self.survey_frame)
        survey_layout.setContentsMargins(26, 20, 26, 20)
        survey_layout.setSpacing(16)

        survey_header = QHBoxLayout()
        survey_header.setSpacing(10)
        img_survey = QLabel()
        img_survey.setPixmap(
            IconManager.get_icon("clipboard-list", color="@COLOR_TEXT_SECONDARY", size=QSize(22, 22)).pixmap(22, 22)
        )
        survey_header.addWidget(img_survey)

        lbl_survey_title = QLabel("Risk Profili Anketi")
        lbl_survey_title.setProperty("cssClass", "surveyTitle")
        survey_header.addWidget(lbl_survey_title)
        survey_header.addStretch()

        self.lbl_step = QLabel("")
        self.lbl_step.setProperty("cssClass", "surveyStep")
        survey_header.addWidget(self.lbl_step)
        survey_layout.addLayout(survey_header)

        self.step_stack = QStackedWidget()
        self.step_stack.setProperty("cssClass", "surveyStack")
        for index, (section_title, question) in enumerate(self.questionnaire_items):
            self.step_stack.addWidget(self._create_question_page(section_title, question, index + 1))
        survey_layout.addWidget(self.step_stack, 1)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        self.btn_previous = QPushButton("Geri")
        self.btn_previous.setIcon(IconManager.get_icon("arrow-left", color="@COLOR_TEXT_PRIMARY"))
        self.btn_previous.setIconSize(QSize(18, 18))
        self.btn_previous.setCursor(Qt.PointingHandCursor)
        self.btn_previous.setMinimumHeight(42)
        self.btn_previous.setProperty("cssClass", "secondaryButton")
        self.btn_previous.clicked.connect(self._on_previous_section)
        btn_layout.addWidget(self.btn_previous)

        btn_layout.addStretch()

        self.btn_next = QPushButton("Devam")
        self.btn_next.setIcon(IconManager.get_icon("arrow-right", color="@COLOR_TEXT_WHITE"))
        self.btn_next.setIconSize(QSize(18, 18))
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.setMinimumHeight(42)
        self.btn_next.setMinimumWidth(150)
        self.btn_next.setProperty("cssClass", "primaryButton")
        self.btn_next.clicked.connect(self._on_next_section)
        btn_layout.addWidget(self.btn_next)

        self.btn_calculate = QPushButton("Profili Hesapla")
        self.btn_calculate.setIcon(IconManager.get_icon("refresh-cw", color="@COLOR_TEXT_WHITE"))
        self.btn_calculate.setIconSize(QSize(20, 20))
        self.btn_calculate.setCursor(Qt.PointingHandCursor)
        self.btn_calculate.setMinimumHeight(42)
        self.btn_calculate.setMinimumWidth(220)
        self.btn_calculate.setProperty("cssClass", "calculateButton")
        self.btn_calculate.clicked.connect(self._on_calculate)
        btn_layout.addWidget(self.btn_calculate)
        survey_layout.addLayout(btn_layout)

        self.main_layout.addWidget(self.survey_frame, 1)
        self._update_section_nav()

    @staticmethod
    def _section_icon_name(title: str) -> str:
        return SECTION_ICONS.get(title, "clipboard-list")

    def _create_question_page(self, section_title: str, question, question_number: int) -> QFrame:
        page = QFrame()
        page.setProperty("cssClass", "surveySectionPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        section_header = QHBoxLayout()
        section_header.setSpacing(10)

        icon = QLabel()
        icon.setPixmap(
            IconManager.get_icon(
                self._section_icon_name(section_title),
                color="@COLOR_ACCENT",
                size=QSize(22, 22),
            ).pixmap(22, 22)
        )
        section_header.addWidget(icon)

        title = QLabel(section_title)
        title.setProperty("cssClass", "surveySectionTitle")
        section_header.addWidget(title)
        section_header.addStretch()
        layout.addLayout(section_header)

        layout.addWidget(self._create_question_widget(question, question_number), 1)
        layout.addStretch()

        return page

    def _create_question_widget(self, question, question_number: int) -> QFrame:
        frame = QFrame()
        frame.setProperty("cssClass", "surveyQuestionFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(18)

        lbl = QLabel(f"{question_number}. {question.title}")
        lbl.setWordWrap(True)
        lbl.setProperty("cssClass", "surveyQuestion")
        layout.addWidget(lbl)

        option_layout = QVBoxLayout()
        option_layout.setSpacing(10)

        group = QButtonGroup(self)
        group.setExclusive(True)
        for option in question.options:
            radio = self._create_radio_button(option.label, option.value)
            group.addButton(radio)
            option_layout.addWidget(radio)
        self.answer_groups[question.id] = group

        layout.addLayout(option_layout)
        return frame

    @staticmethod
    def _create_radio_button(text: str, value: str) -> QRadioButton:
        rb = QRadioButton(text)
        rb.setProperty("optionValue", value)
        rb.setCursor(Qt.PointingHandCursor)
        rb.setMinimumHeight(46)
        rb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rb.setProperty("cssClass", "surveyRadio")
        return rb

    def _current_question_is_complete(self) -> bool:
        _section_title, question = self.questionnaire_items[self.current_question_index]
        if self.answer_groups[question.id].checkedButton() is None:
            Toast.warning(self, "Devam etmek icin bu soruyu cevaplayin.")
            return False
        return True

    def _on_previous_section(self):
        if self.current_question_index <= 0:
            return
        self.current_question_index -= 1
        self._update_section_nav()

    def _on_next_section(self):
        if not self._current_question_is_complete():
            return
        if self.current_question_index >= len(self.questionnaire_items) - 1:
            return
        self.current_question_index += 1
        self._update_section_nav()

    def _update_section_nav(self):
        total = len(self.questionnaire_items)
        self.step_stack.setCurrentIndex(self.current_question_index)
        self.lbl_step.setText(f"Soru {self.current_question_index + 1} / {total}")
        self.btn_previous.setEnabled(self.current_question_index > 0)
        is_last = self.current_question_index == total - 1
        self.btn_next.setVisible(not is_last)
        self.btn_calculate.setVisible(is_last)

    def _collect_answers(self) -> Optional[Dict[str, str]]:
        answers: Dict[str, str] = {}
        missing = []
        for question_id, group in self.answer_groups.items():
            checked = group.checkedButton()
            if checked is None:
                missing.append(question_id)
                continue
            answers[question_id] = checked.property("optionValue")

        if missing:
            Toast.warning(self, "Lutfen tum anket sorularini cevaplayin.")
            return None
        return answers

    def _on_calculate(self):
        answers = self._collect_answers()
        if answers is None:
            return

        try:
            profile = self._service.calculate_and_save_profile(answers=answers)
            self._display_profile(profile)
            QMessageBox.information(
                self,
                "Profil Hesaplandi",
                f"Risk Skorunuz: {profile.risk_score}/100\n"
                f"Profiliniz: {profile.emoji} {profile.display_name}\n\n"
                f"{profile.description}",
            )
        except Exception as exc:
            Toast.error(self, self._format_calculation_error(exc))

    def _display_profile(self, profile: RiskProfile):
        self.profile_card.setVisible(True)

        color_state = self._color_to_state(profile.color)
        self.profile_card.setProperty("cssState", color_state)
        self.profile_card.style().unpolish(self.profile_card)
        self.profile_card.style().polish(self.profile_card)

        self.lbl_score.setText(f"Puan: {profile.risk_score} / 100")
        self.lbl_label.setText(f"{profile.emoji} {profile.display_name}")
        self.lbl_label.setProperty("cssState", color_state)
        self.lbl_label.style().unpolish(self.lbl_label)
        self.lbl_label.style().polish(self.lbl_label)
        self.lbl_profile_desc.setText(profile.description)

        for dimension, label in self.dimension_labels.items():
            if dimension in profile.dimension_scores:
                label.setText(f"{profile.dimension_scores[dimension]} / 100")
            else:
                label.setText("-")

        if profile.recommended_allocation:
            allocation = " | ".join(
                f"{asset}: %{weight}" for asset, weight in profile.recommended_allocation.items()
            )
            self.lbl_allocation.setText(allocation)
        else:
            self.lbl_allocation.setText("")

        visible_notes = [
            note
            for note in profile.suitability_notes
            if "Veritabani eski semada" not in note
        ]
        self.lbl_notes.setText("\n".join(visible_notes))
        self.notes_block.setVisible(bool(visible_notes))
        self._select_answers(profile.answers)

    @staticmethod
    def _color_to_state(color: str) -> str:
        mapping = {
            "#10b981": "conservative",
            "#3b82f6": "moderate",
            "#f59e0b": "balanced",
            "#8b5cf6": "growth",
            "#ef4444": "aggressive",
        }
        return mapping.get(color.lower(), "moderate")

    def _select_answers(self, answers: Dict[str, str]):
        for question_id, value in answers.items():
            group = self.answer_groups.get(question_id)
            if group is None:
                continue
            self._select_radio(group, value)

    def on_page_enter(self):
        try:
            profile = self._service.get_current_profile()
            if profile:
                self._display_profile(profile)
            else:
                self.profile_card.setVisible(False)
        except Exception:
            self.profile_card.setVisible(False)

    def refresh_data(self):
        self.on_page_enter()

    @staticmethod
    def _select_radio(group: QButtonGroup, value: str):
        for btn in group.buttons():
            if btn.property("optionValue") == value:
                btn.setChecked(True)
                return

    @staticmethod
    def _format_calculation_error(exc: Exception) -> str:
        message = str(exc)
        if "Unknown column" in message and "risk_profiles" in message:
            return (
                "Risk profili kaydedilemedi: veritabani semasi guncel degil. "
                "scripts/alter_risk_profile_professional.sql dosyasini uygulayin."
            )
        return "Profil hesaplanamadi. Lutfen yanitlari kontrol edip tekrar deneyin."
