from __future__ import annotations
from src.ui.shared.locale_tr import L10N

from datetime import date
from decimal import Decimal

from PyQt5.QtCore import QDate, Qt, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.domain.models.corporate_action import ActionType
from src.domain.models.corporate_action_candidate import CorporateActionCandidate
from src.ui.widgets.dialog_behavior import configure_dialog_behavior
from src.ui.widgets.shared import CurrencySpinBox
from src.ui.widgets.shared import AnimatedButton, Toast


class CorporateActionCandidatesPanel(QWidget):
    def __init__(self, container, parent=None) -> None:
        super().__init__(parent)
        self.container = container
        self.discovery_service = getattr(container, "corporate_action_discovery_service", None)
        self.review_service = getattr(container, "corporate_action_candidate_review_service", None)
        self.stock_repo = getattr(container, "stock_repo", None)
        self._candidates: dict[int, CorporateActionCandidate] = {}
        self._init_ui()
        self.refresh_list()

    def _init_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(18)

        card = QFrame()
        card.setProperty("cssClass", "panelFramePadded")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title_row = QHBoxLayout()
        title = QLabel(L10N.KURUMSAL_AKSIYON_TAKIP)
        title.setProperty("cssClass", "panelTitle")
        title_row.addWidget(title)
        title_row.addStretch()

        self.btn_refresh_remote = self._action_button(" KAP/MKK Yenile", "refresh-cw", self.discover)
        self.btn_refresh_list = self._action_button(L10N.LISTEYI_YENILE, "list", self.refresh_list)
        title_row.addWidget(self.btn_refresh_remote)
        title_row.addWidget(self.btn_refresh_list)
        layout.addLayout(title_row)

        desc = QLabel(
            L10N.BEDELLI_VE_BEDELSIZ_SERMAYE_ARTIRIMI +
            L10N.PORTFOY_VE_FIYAT_DUZELTMESI_YALNIZCA
        )
        desc.setWordWrap(True)
        desc.setProperty("cssClass", "pageDescription")
        layout.addWidget(desc)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["Hisse", "Tip", "Durum", "Oran", "Kullanim", "Ex-Date", "Guven", "Kaynak"]
        )
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setProperty("cssClass", "dataTable")
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table, 1)

        action_row = QHBoxLayout()
        self.btn_apply = self._action_button(L10N.ONAYLA_VE_UYGULA, L10N.PLUSCIRCLE, self.apply_selected)
        self.btn_edit = self._action_button(L10N.DUZENLE, "pencil", self.edit_selected)
        self.btn_ignore = self._action_button(L10N.YOKSAY, "trash-2", self.ignore_selected, L10N.DANGERTEXTBUTTON, "@COLOR_DANGER")
        self.btn_open_source = self._action_button(L10N.KAYNAGI_AC, "arrow-right", self.open_selected_source)
        for button in (self.btn_apply, self.btn_edit, self.btn_ignore, self.btn_open_source):
            action_row.addWidget(button)
        action_row.addStretch()
        layout.addLayout(action_row)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setMinimumHeight(92)
        self.detail_text.setProperty("cssClass", "plainTextPanel")
        layout.addWidget(self.detail_text)

        root_layout.addWidget(card)
        if self.discovery_service is None or self.review_service is None:
            self._set_controls_enabled(False)
            self.detail_text.setText(L10N.KURUMSAL_AKSIYON_ADAY_SERVISLERI_KULLANILAMIYOR)
        else:
            self._on_selection_changed()

    def _action_button(
        self,
        text: str,
        icon_name: str,
        slot,
        css_class: str = "secondaryButton",
        icon_color: str = "@COLOR_TEXT_PRIMARY",
    ) -> AnimatedButton:
        button = AnimatedButton(text)
        button.setIconName(icon_name, color=icon_color)
        button.setProperty("cssClass", css_class)
        button.clicked.connect(slot)
        return button

    def discover(self) -> None:
        if self.discovery_service is None:
            return
        self._set_controls_enabled(False)
        try:
            result = self.discovery_service.discover()
            if getattr(result, "source_unavailable", False):
                Toast.warning(self, _discovery_error_message(result))
            else:
                Toast.success(self, L10N.KURUMSAL_AKSIYON_TARAMASI_TAMAMLANDI_TMPL.format(count=result.saved_count))
            self.refresh_list()
        except Exception as exc:
            Toast.error(self, L10N.KURUMSAL_AKSIYON_TARAMASI_CALISTIRILAMADI_TMPL.format(exc=exc))
        finally:
            self._set_controls_enabled(True)

    def refresh_list(self) -> None:
        if self.review_service is None:
            return
        try:
            candidates = self.review_service.list_reviewable()
        except Exception as exc:
            self.table.setRowCount(0)
            self.detail_text.setText(
                L10N.KURUMSAL_AKSIYON_ADAY_TABLOSU_OKUNAMADI +
                "Mevcut DB için scripts/apply_corporate_action_candidate_schema.py çalıştırılmalıdır.\n" +
                f"Hata: {exc}"
            )
            return
        self._candidates = {candidate.id: candidate for candidate in candidates if candidate.id is not None}
        self.table.setRowCount(len(candidates))
        for row, candidate in enumerate(candidates):
            self._set_row(row, candidate)
        self._on_selection_changed()

    def apply_selected(self) -> None:
        candidate = self._selected_candidate()
        if candidate is None or candidate.id is None:
            return
        try:
            result = self.review_service.approve_and_apply(candidate.id)
            Toast.success(self, result.result.description)
            self.refresh_list()
        except Exception as exc:
            Toast.warning(self, L10N.ADAY_UYGULANAMADI_TMPL.format(exc=exc))
            self.refresh_list()

    def ignore_selected(self) -> None:
        candidate = self._selected_candidate()
        if candidate is None or candidate.id is None:
            return
        self.review_service.ignore(candidate.id)
        Toast.success(self, L10N.ADAY_YOKSAYILDI)
        self.refresh_list()

    def edit_selected(self) -> None:
        candidate = self._selected_candidate()
        if candidate is None:
            return
        dialog = CorporateActionCandidateEditDialog(candidate, self.stock_repo, self)
        if dialog.exec_() != QDialog.Accepted:
            return
        updated = dialog.to_candidate()
        try:
            self.review_service.update_candidate(updated)
            Toast.success(self, L10N.ADAY_GUNCELLENDI)
            self.refresh_list()
        except Exception as exc:
            Toast.error(self, L10N.ADAY_GUNCELLENEMEDI_TMPL.format(exc=exc))

    def open_selected_source(self) -> None:
        candidate = self._selected_candidate()
        if candidate and candidate.source_url:
            QDesktopServices.openUrl(QUrl(candidate.source_url))

    def _set_row(self, row: int, candidate: CorporateActionCandidate) -> None:
        values = [
            candidate.ticker,
            candidate.action_type.value,
            candidate.status.value,
            _fmt_decimal(candidate.ratio),
            _fmt_decimal(candidate.subscription_price),
            candidate.ex_date.isoformat() if candidate.ex_date else "-",
            _fmt_decimal(candidate.confidence),
            candidate.source,
        ]
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignCenter)
            if col == 0 and candidate.id is not None:
                item.setData(Qt.UserRole, candidate.id)
            self.table.setItem(row, col, item)

    def _selected_candidate(self) -> CorporateActionCandidate | None:
        selected = self.table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        item = self.table.item(row, 0)
        candidate_id = item.data(Qt.UserRole) if item else None
        return self._candidates.get(candidate_id)

    def _on_selection_changed(self) -> None:
        candidate = self._selected_candidate()
        has_selection = candidate is not None
        self.btn_apply.setEnabled(has_selection and candidate.status.value in ("READY", L10N.APPROVED))
        self.btn_edit.setEnabled(has_selection)
        self.btn_ignore.setEnabled(has_selection)
        self.btn_open_source.setEnabled(has_selection and bool(candidate.source_url))
        if candidate is None:
            self.detail_text.setText(L10N.ADAY_SECILMEDI)
            return
        self.detail_text.setText(_candidate_detail(candidate))

    def _set_controls_enabled(self, enabled: bool) -> None:
        for button in (
            self.btn_refresh_remote,
            self.btn_refresh_list,
            self.btn_apply,
            self.btn_edit,
            self.btn_ignore,
            self.btn_open_source,
        ):
            button.setEnabled(enabled)


class CorporateActionCandidateEditDialog(QDialog):
    def __init__(self, candidate: CorporateActionCandidate, stock_repo, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._candidate = candidate
        self._stock_repo = stock_repo
        self.setWindowTitle(L10N.KURUMSAL_AKSIYON_ADAYI)
        self.setMinimumWidth(420)
        self._init_ui()
        configure_dialog_behavior(self, self.btn_save, self.accept)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.ticker_edit = QLineEdit(self._candidate.ticker)
        self.type_combo = QComboBox()
        self.type_combo.addItems([ActionType.BEDELSIZ.value, ActionType.BEDELLI.value])
        self.type_combo.setCurrentText(self._candidate.action_type.value)

        self.ratio_spin = QDoubleSpinBox()
        self.ratio_spin.setRange(0.000001, 10000)
        self.ratio_spin.setDecimals(6)
        self.ratio_spin.setSuffix(" %")
        self.ratio_spin.setValue(float((self._candidate.ratio or Decimal("0")) * Decimal("100")))

        self.sub_price_spin = CurrencySpinBox()
        self.sub_price_spin.setRange(0, 100000)
        self.sub_price_spin.setDecimals(4)
        self.sub_price_spin.setSuffix(" TL")
        self.sub_price_spin.setValue(float(self._candidate.subscription_price or Decimal("0")))

        self.ex_date_edit = QDateEdit()
        self.ex_date_edit.setCalendarPopup(True)
        self.ex_date_edit.setDisplayFormat("dd.MM.yyyy")
        ex_date = self._candidate.ex_date or date.today()
        self.ex_date_edit.setDate(QDate(ex_date.year, ex_date.month, ex_date.day))

        self.notes_edit = QLineEdit(self._candidate.parse_notes or "")

        form.addRow("Hisse:", self.ticker_edit)
        form.addRow("Tip:", self.type_combo)
        form.addRow("Oran:", self.ratio_spin)
        form.addRow(L10N.KULLANIM_FIYATI, self.sub_price_spin)
        form.addRow("Ex-date:", self.ex_date_edit)
        form.addRow(L10N.NOT, self.notes_edit)
        layout.addLayout(form)

        button_row = QHBoxLayout()
        button_row.addStretch()
        cancel = QPushButton(L10N.IPTAL)
        cancel.clicked.connect(self.reject)
        self.btn_save = QPushButton(L10N.SAVE)
        self.btn_save.clicked.connect(self.accept)
        self.btn_save.setDefault(True)
        button_row.addWidget(cancel)
        button_row.addWidget(self.btn_save)
        layout.addLayout(button_row)

    def to_candidate(self) -> CorporateActionCandidate:
        ticker = self.ticker_edit.text().strip().upper()
        stock = self._stock_repo.get_stock_by_ticker(ticker) if self._stock_repo is not None else None
        action_type = ActionType(self.type_combo.currentText())
        ratio = Decimal(str(self.ratio_spin.value())) / Decimal("100")
        sub_price = self.sub_price_spin.decimal_value()
        qdate = self.ex_date_edit.date()
        return CorporateActionCandidate(
            id=self._candidate.id,
            ticker=ticker,
            stock_id=stock.id if stock is not None else self._candidate.stock_id,
            source=self._candidate.source,
            source_disclosure_id=self._candidate.source_disclosure_id,
            source_url=self._candidate.source_url,
            action_type=action_type,
            status=self._candidate.status,
            ratio=ratio,
            subscription_price=sub_price if action_type == ActionType.BEDELLI and sub_price > 0 else None,
            announcement_date=self._candidate.announcement_date,
            ex_date=date(qdate.year(), qdate.month(), qdate.day()),
            confidence=self._candidate.confidence,
            raw_payload_json=self._candidate.raw_payload_json,
            parse_notes=self.notes_edit.text().strip() or None,
            created_at=self._candidate.created_at,
            updated_at=self._candidate.updated_at,
        )


def _fmt_decimal(value: Decimal | None) -> str:
    return f"{value.normalize()}" if value is not None else "-"


def _candidate_detail(candidate: CorporateActionCandidate) -> str:
    lines = [
        f"Hisse: {candidate.ticker}",
        f"Tip: {candidate.action_type.value}",
        f"Durum: {candidate.status.value}",
        f"Kaynak: {candidate.source}:{candidate.source_disclosure_id}",
    ]
    if candidate.parse_notes:
        lines.append(f"Not: {candidate.parse_notes}")
    if candidate.source_url:
        lines.append(f"Kaynak linki: {candidate.source_url}")
    return "\n".join(lines)


def _discovery_error_message(result) -> str:
    errors = getattr(result, "errors", []) or []
    if errors:
        return f"KAP/MKK kaynagi gecici olarak okunamadi: {errors[0]}"
    return "KAP/MKK kaynagi gecici olarak okunamadi."
