# src/ui/pages/risk_profile_page.py

from __future__ import annotations

from typing import Optional

from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QSpinBox,
    QRadioButton,
    QButtonGroup,
    QFrame,
    QMessageBox,
    QGroupBox,
    QSizePolicy,
)
from PyQt5.QtCore import Qt

from .base_page import BasePage
from src.domain.models.risk_profile import RiskProfile, PROFILE_INFO


class RiskProfilePage(BasePage):
    """
    Risk Profil Analizi sayfası.
    3 soruluk anket ile yatırımcı risk profilini belirler.
    Mevcut profil varsa üstte gösterir, yeni anket doldurulabilir.
    """

    def __init__(self, container, parent=None):
        super().__init__(parent)
        self.container = container
        self.page_title = "Risk Profili"
        self._service = container.risk_profile_service
        self._init_ui()

    def _init_ui(self):
        # ====== BAŞLIK ====== #
        header = QHBoxLayout()
        lbl_title = QLabel("🛡️ Risk Profil Analizi")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #f1f5f9;")
        header.addWidget(lbl_title)
        header.addStretch()
        self.main_layout.addLayout(header)

        lbl_desc = QLabel("Yatırım tarzınızı belirlemek için 3 kısa soruya cevap verin.")
        lbl_desc.setStyleSheet("color: #94a3b8; font-size: 13px; margin-bottom: 5px;")
        self.main_layout.addWidget(lbl_desc)

        # ====== MEVCUT PROFİL KARTI ====== #
        self.profile_card = QFrame()
        self.profile_card.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border-radius: 12px;
                border: 2px solid #334155;
            }
        """)
        card_layout = QVBoxLayout(self.profile_card)
        card_layout.setContentsMargins(25, 20, 25, 20)
        card_layout.setSpacing(10)

        self.lbl_profile_header = QLabel("📊 Mevcut Profiliniz")
        self.lbl_profile_header.setStyleSheet(
            "color: #94a3b8; font-size: 14px; font-weight: bold; border: none;"
        )
        card_layout.addWidget(self.lbl_profile_header)

        # Skor + etiket satırı
        score_row = QHBoxLayout()
        self.lbl_score = QLabel("Puan: —")
        self.lbl_score.setStyleSheet("color: #f1f5f9; font-size: 16px; font-weight: bold; border: none;")
        self.lbl_label = QLabel("")
        self.lbl_label.setStyleSheet("font-size: 22px; font-weight: bold; border: none;")
        score_row.addWidget(self.lbl_score)
        score_row.addStretch()
        score_row.addWidget(self.lbl_label)
        card_layout.addLayout(score_row)

        self.lbl_profile_desc = QLabel("")
        self.lbl_profile_desc.setWordWrap(True)
        self.lbl_profile_desc.setStyleSheet("color: #94a3b8; font-size: 13px; border: none;")
        card_layout.addWidget(self.lbl_profile_desc)

        # Detay satırı
        detail_row = QHBoxLayout()
        self.lbl_age_detail = QLabel("")
        self.lbl_age_detail.setStyleSheet("color: #64748b; font-size: 12px; border: none;")
        self.lbl_horizon_detail = QLabel("")
        self.lbl_horizon_detail.setStyleSheet("color: #64748b; font-size: 12px; border: none;")
        self.lbl_reaction_detail = QLabel("")
        self.lbl_reaction_detail.setStyleSheet("color: #64748b; font-size: 12px; border: none;")
        detail_row.addWidget(self.lbl_age_detail)
        detail_row.addWidget(self.lbl_horizon_detail)
        detail_row.addWidget(self.lbl_reaction_detail)
        detail_row.addStretch()
        card_layout.addLayout(detail_row)

        self.profile_card.setVisible(False)
        self.main_layout.addWidget(self.profile_card)

        # ====== ANKET FORMU ====== #
        survey_frame = QFrame()
        survey_frame.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border-radius: 12px;
                border: 1px solid #334155;
            }
        """)
        survey_layout = QVBoxLayout(survey_frame)
        survey_layout.setContentsMargins(25, 20, 25, 25)
        survey_layout.setSpacing(18)

        lbl_survey_title = QLabel("📝 Risk Profili Anketi")
        lbl_survey_title.setStyleSheet(
            "color: #f1f5f9; font-size: 16px; font-weight: bold; border: none;"
        )
        survey_layout.addWidget(lbl_survey_title)

        # --- Soru 1: Yaş ---
        q1_group = self._create_question_group("1️⃣ Yaşınız kaç?")
        q1_layout = QHBoxLayout()
        self.spin_age = QSpinBox()
        self.spin_age.setRange(18, 100)
        self.spin_age.setValue(30)
        self.spin_age.setMinimumHeight(40)
        self.spin_age.setMinimumWidth(100)
        self.spin_age.setStyleSheet("""
            QSpinBox {
                background-color: #0f172a; color: #f1f5f9;
                border: 1px solid #334155; border-radius: 8px;
                padding: 8px; font-size: 16px;
            }
            QSpinBox:focus { border: 1px solid #3b82f6; }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 20px; background-color: #334155; border: none; margin: 1px;
            }
        """)
        q1_layout.addWidget(self.spin_age)
        q1_layout.addStretch()
        q1_group.layout().addLayout(q1_layout)
        survey_layout.addWidget(q1_group)

        # --- Soru 2: Yatırım Vadesi ---
        q2_group = self._create_question_group(
            "2️⃣ Yatırımlarınızı genelde ne kadar süre tutarsınız?"
        )
        self.horizon_group = QButtonGroup(self)
        q2_options = QHBoxLayout()
        q2_options.setSpacing(15)

        self.rb_short = self._create_radio_button("⏱️ Kısa Vade\n(< 1 Ay)", "short")
        self.rb_medium = self._create_radio_button("📅 Orta Vade\n(1-12 Ay)", "medium")
        self.rb_long = self._create_radio_button("📈 Uzun Vade\n(> 1 Yıl)", "long")

        self.horizon_group.addButton(self.rb_short)
        self.horizon_group.addButton(self.rb_medium)
        self.horizon_group.addButton(self.rb_long)
        self.rb_medium.setChecked(True)

        q2_options.addWidget(self.rb_short)
        q2_options.addWidget(self.rb_medium)
        q2_options.addWidget(self.rb_long)
        q2_group.layout().addLayout(q2_options)
        survey_layout.addWidget(q2_group)

        # --- Soru 3: Kayıp Tepkisi ---
        q3_group = self._create_question_group(
            "3️⃣ Portföyünüz bir haftada %20 değer kaybetse ne yaparsınız?"
        )
        self.reaction_group = QButtonGroup(self)
        q3_options = QHBoxLayout()
        q3_options.setSpacing(15)

        self.rb_sell = self._create_radio_button("😰 Panik yapıp\nsatarım", "sell")
        self.rb_hold = self._create_radio_button("🧘 Sakince\nbeklerim", "hold")
        self.rb_buy_more = self._create_radio_button("💪 Fırsat bilip\ndaha çok alırım", "buy_more")

        self.reaction_group.addButton(self.rb_sell)
        self.reaction_group.addButton(self.rb_hold)
        self.reaction_group.addButton(self.rb_buy_more)
        self.rb_hold.setChecked(True)

        q3_options.addWidget(self.rb_sell)
        q3_options.addWidget(self.rb_hold)
        q3_options.addWidget(self.rb_buy_more)
        q3_group.layout().addLayout(q3_options)
        survey_layout.addWidget(q3_group)

        # --- Hesapla Butonu ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_calculate = QPushButton("🎯 Profili Hesapla")
        self.btn_calculate.setCursor(Qt.PointingHandCursor)
        self.btn_calculate.setMinimumHeight(48)
        self.btn_calculate.setMinimumWidth(220)
        self.btn_calculate.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6; color: white; border: none;
                border-radius: 10px; font-size: 16px; font-weight: bold;
                padding: 12px 30px;
            }
            QPushButton:hover { background-color: #7c3aed; }
        """)
        self.btn_calculate.clicked.connect(self._on_calculate)
        btn_layout.addWidget(self.btn_calculate)
        btn_layout.addStretch()
        survey_layout.addLayout(btn_layout)

        self.main_layout.addWidget(survey_frame)
        self.main_layout.addStretch()

    # ==================== Widget Yardımcıları ==================== #

    @staticmethod
    def _create_question_group(title: str) -> QGroupBox:
        group = QGroupBox()
        group.setStyleSheet("""
            QGroupBox {
                border: none;
                margin-top: 0;
                padding: 0;
            }
        """)
        layout = QVBoxLayout()
        layout.setSpacing(10)

        lbl = QLabel(title)
        lbl.setStyleSheet("color: #e2e8f0; font-size: 14px; font-weight: bold;")
        layout.addWidget(lbl)

        group.setLayout(layout)
        return group

    @staticmethod
    def _create_radio_button(text: str, value: str) -> QRadioButton:
        rb = QRadioButton(text)
        rb.setProperty("optionValue", value)
        rb.setCursor(Qt.PointingHandCursor)
        rb.setMinimumHeight(55)
        rb.setStyleSheet("""
            QRadioButton {
                background-color: #0f172a;
                color: #f1f5f9;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 12px 18px;
                font-size: 13px;
                spacing: 8px;
            }
            QRadioButton:hover {
                border: 1px solid #3b82f6;
                background-color: #1e293b;
            }
            QRadioButton:checked {
                border: 2px solid #8b5cf6;
                background-color: rgba(139, 92, 246, 0.15);
            }
            QRadioButton::indicator {
                width: 16px; height: 16px;
                border: 2px solid #64748b;
                border-radius: 8px;
                background-color: #0f172a;
            }
            QRadioButton::indicator:checked {
                background-color: #8b5cf6;
                border: 2px solid #8b5cf6;
            }
        """)
        return rb

    # ==================== İş Mantığı ==================== #

    def _get_selected_value(self, group: QButtonGroup) -> Optional[str]:
        checked = group.checkedButton()
        if checked:
            return checked.property("optionValue")
        return None

    def _on_calculate(self):
        age = self.spin_age.value()
        horizon = self._get_selected_value(self.horizon_group)
        reaction = self._get_selected_value(self.reaction_group)

        if not horizon or not reaction:
            QMessageBox.warning(self, "Uyarı", "Lütfen tüm soruları cevaplayın.")
            return

        try:
            profile = self._service.calculate_and_save_profile(
                age=age, horizon=horizon, reaction=reaction
            )
            self._display_profile(profile)
            QMessageBox.information(
                self, "Profil Hesaplandı",
                f"Risk Skorunuz: {profile.risk_score}\n"
                f"Profiliniz: {profile.emoji} {profile.risk_label}\n\n"
                f"{profile.description}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Profil hesaplanamadı: {e}")

    def _display_profile(self, profile: RiskProfile):
        """Profil kartını günceller ve gösterir."""
        self.profile_card.setVisible(True)

        # Kart kenarlık rengini profile göre ayarla
        self.profile_card.setStyleSheet(f"""
            QFrame {{
                background-color: #1e293b;
                border-radius: 12px;
                border: 2px solid {profile.color};
            }}
        """)

        self.lbl_score.setText(f"Puan: {profile.risk_score} / 100")
        self.lbl_label.setText(f"{profile.emoji} {profile.risk_label}")
        self.lbl_label.setStyleSheet(
            f"color: {profile.color}; font-size: 22px; font-weight: bold; border: none;"
        )
        self.lbl_profile_desc.setText(profile.description)

        self.lbl_age_detail.setText(f"🎂 Yaş: {profile.age}")
        self.lbl_horizon_detail.setText(f"⏳ Vade: {profile.horizon_display}")
        self.lbl_reaction_detail.setText(f"💭 Tepki: {profile.reaction_display}")

    # ==================== Sayfa Olayları ==================== #

    def on_page_enter(self):
        """Sayfa açıldığında mevcut profili yükler."""
        try:
            profile = self._service.get_current_profile()
            if profile:
                self._display_profile(profile)
                # Form alanlarını da doldur
                self.spin_age.setValue(profile.age)
                self._select_radio(self.horizon_group, profile.horizon)
                self._select_radio(self.reaction_group, profile.reaction)
            else:
                self.profile_card.setVisible(False)
        except Exception:
            self.profile_card.setVisible(False)

    def refresh_data(self):
        self.on_page_enter()

    @staticmethod
    def _select_radio(group: QButtonGroup, value: str):
        """ButtonGroup'taki belirli değere sahip radio'yu seçer."""
        for btn in group.buttons():
            if btn.property("optionValue") == value:
                btn.setChecked(True)
                return
