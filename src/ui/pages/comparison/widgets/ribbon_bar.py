from __future__ import annotations
from src.ui.shared.locale_tr import L10N
from datetime import date, timedelta
from src.qt_compat.qtcore import QDate, Signal, Qt
from src.qt_compat.qtwidgets import (
    QComboBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget
)
from src.ui.pages.analysis.checkable_combo_box import CheckableComboBox

class ComparisonRibbonBar(QFrame):
    filter_changed = Signal()
    _DATE_EDIT_WIDTH = 138
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_range_start_provider = None
        self.setProperty("cssClass", "panelFramePadded")
        self.setMinimumHeight(60)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._init_ui()
        
    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(0)
        self.controls_layout = QHBoxLayout()
        self.controls_layout.setSpacing(18)
        self.controls_layout.setContentsMargins(0, 0, 0, 0)
        self.left_container = self._build_left_container()
        self.right_container = self._build_right_container()
        self.controls_layout.addWidget(self.left_container, 0, Qt.AlignTop | Qt.AlignLeft)
        self.controls_layout.addStretch(1)
        self.controls_layout.addWidget(self.right_container, 0, Qt.AlignTop | Qt.AlignRight)
        main_layout.addLayout(self.controls_layout)

    def _build_left_container(self) -> QWidget:
        container = QWidget()
        container.setProperty("cssClass", "comparisonFilterBlock")
        container.setAttribute(Qt.WA_StyledBackground, True)
        container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.ratio_widget = container
        self.left_grid = QGridLayout(container)
        self.left_grid.setContentsMargins(0, 0, 0, 0)
        self.left_grid.setHorizontalSpacing(10)
        self.left_grid.setVerticalSpacing(6)
        self.left_grid.setColumnStretch(1, 1)
        self.left_grid.setColumnStretch(3, 1)
        self.compare_label = QLabel(L10N.KIYASLANACAK_VARLIKLAR)
        self.left_grid.addWidget(self.compare_label, 0, 0, Qt.AlignRight)
        self.compare_combo = CheckableComboBox(L10N.VARLIK_SECIN)
        self.compare_combo.setMinimumWidth(220)
        self.compare_combo.selection_changed.connect(self.filter_changed.emit)
        self.left_grid.addWidget(self.compare_combo, 0, 1)
        self.mode_label = QLabel(L10N.GRAFIK_MODU_1)
        self.left_grid.addWidget(self.mode_label, 0, 2, Qt.AlignRight)
        self.combo_mode = QComboBox()
        self.combo_mode.setProperty("cssClass", "customComboBox")
        self.combo_mode.addItems(["Normal", L10N.NORMALIZE_BAZ_100, L10N.RASYO_MODU])
        self.combo_mode.setMinimumWidth(160)
        self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)
        self.left_grid.addWidget(self.combo_mode, 0, 3)
        self.ratio_label = QLabel(L10N.PAY)
        self.left_grid.addWidget(self.ratio_label, 1, 0, Qt.AlignRight)
        self.combo_num = QComboBox()
        self.combo_num.setProperty("cssClass", "customComboBox")
        self.combo_num.setMinimumWidth(220)
        self.combo_num.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_num.currentIndexChanged.connect(self.filter_changed.emit)
        self.left_grid.addWidget(self.combo_num, 1, 1)
        self.ratio_den_label = QLabel(f"/ {L10N.PAYDA}")
        self.left_grid.addWidget(self.ratio_den_label, 1, 2, Qt.AlignRight)
        self.combo_den = QComboBox()
        self.combo_den.setProperty("cssClass", "customComboBox")
        self.combo_den.setMinimumWidth(220)
        self.combo_den.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_den.currentIndexChanged.connect(self.filter_changed.emit)
        self.left_grid.addWidget(self.combo_den, 1, 3)
        self._set_ratio_controls_visible(False)
        return container

    def _build_right_container(self) -> QWidget:
        container = QWidget()
        container.setProperty("cssClass", "comparisonFilterBlock")
        container.setAttribute(Qt.WA_StyledBackground, True)
        container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.right_vbox = QVBoxLayout(container)
        self.right_vbox.setContentsMargins(0, 0, 0, 0)
        self.right_vbox.setSpacing(6)
        self.date_row = self._build_date_row()
        self.right_vbox.addLayout(self.date_row)
        self.time_buttons_layout = self._build_time_buttons_layout()
        self.right_vbox.addLayout(self.time_buttons_layout)
        return container

    def _build_date_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(QLabel(L10N.TARIH_ARALIGI_1))
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDisplayFormat("dd.MM.yyyy")
        self.date_start.setProperty("cssClass", "tradeInputNormal")
        self.date_start.setMinimumHeight(36)
        self.date_start.setFixedWidth(self._DATE_EDIT_WIDTH)
        self.date_start.setDate(QDate.currentDate().addMonths(-3))
        self.date_start.dateChanged.connect(self.filter_changed.emit)
        row.addWidget(self.date_start)
        row.addWidget(QLabel("—"))
        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDisplayFormat("dd.MM.yyyy")
        self.date_end.setProperty("cssClass", "tradeInputNormal")
        self.date_end.setMinimumHeight(36)
        self.date_end.setFixedWidth(self._DATE_EDIT_WIDTH)
        self.date_end.setDate(QDate.currentDate())
        self.date_end.dateChanged.connect(self.filter_changed.emit)
        row.addWidget(self.date_end)
        return row

    def _build_time_buttons_layout(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)
        self.time_buttons = {}
        periods = [
            ("1A", timedelta(days=30)),
            ("3A", timedelta(days=90)),
            ("6A", timedelta(days=180)),
            ("1Y", timedelta(days=365)),
            ("YBB", None),
            ("Tümü", None),
        ]
        for label, delta in periods:
            btn = QPushButton(label)
            btn.setProperty("cssClass", "secondaryButton")
            btn.setMinimumHeight(28)
            btn.setMinimumWidth(50)
            btn.clicked.connect(lambda checked, l=label, d=delta: self._on_time_button_clicked(l, d))
            layout.addWidget(btn)
            self.time_buttons[label] = btn
        return layout
        
    def _on_mode_changed(self, index: int) -> None:
        # 2 is Rasyo Modu
        is_ratio = (index == 2)
        self._set_ratio_controls_visible(is_ratio)
        self.filter_changed.emit()

    def _set_ratio_controls_visible(self, visible: bool) -> None:
        for widget in (
            self.ratio_label,
            self.combo_num,
            self.ratio_den_label,
            self.combo_den,
        ):
            widget.setVisible(visible)
        
    def _on_time_button_clicked(self, label: str, delta: timedelta | None) -> None:
        today = QDate.currentDate()
        self.date_end.blockSignals(True)
        self.date_start.blockSignals(True)
        
        self.date_end.setDate(today)
        
        if label == "YBB":
            start_date = QDate(today.year(), 1, 1)
            self.date_start.setDate(start_date)
        elif label == "Tümü":
            start = self._all_range_start_date()
            self.date_start.setDate(QDate(start.year, start.month, start.day))
        elif delta is not None:
            days = delta.days
            self.date_start.setDate(today.addDays(-days))
            
        self.date_end.blockSignals(False)
        self.date_start.blockSignals(False)
        
        self.filter_changed.emit()

    def _all_range_start_date(self) -> date:
        if callable(self.all_range_start_provider):
            provided = self.all_range_start_provider(self.selected_assets())
            if provided is not None:
                return provided
        return date(2000, 1, 1)
        
    def set_assets(self, assets: list[tuple[str, str]]) -> None:
        self.compare_combo.set_items(assets)
        
        # Populate Pay/Payda combo boxes as well
        self.combo_num.blockSignals(True)
        self.combo_den.blockSignals(True)
        
        self.combo_num.clear()
        self.combo_den.clear()
        
        for name, code in assets:
            self.combo_num.addItem(name, code)
            self.combo_den.addItem(name, code)
            
        self.combo_num.blockSignals(False)
        self.combo_den.blockSignals(False)
        
    def selected_assets(self) -> list[str]:
        return self.compare_combo.selected_data()
        
    def set_selected_assets(self, codes: list[str], emit: bool = True) -> None:
        self.compare_combo.set_selected_data(codes)
        if emit:
            self.filter_changed.emit()
        
    def selected_mode(self) -> str:
        return self.combo_mode.currentText()
        
    def ratio_assets(self) -> tuple[str, str]:
        return self.combo_num.currentData(), self.combo_den.currentData()
        
    def date_range(self) -> tuple[date, date]:
        start = self.date_start.date().toPyDate()
        end = self.date_end.date().toPyDate()
        return start, end
