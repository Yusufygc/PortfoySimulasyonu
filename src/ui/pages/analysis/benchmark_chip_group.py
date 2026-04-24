from __future__ import annotations

from typing import Dict, List

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QFrame, QGridLayout, QPushButton, QSizePolicy

from src.application.services.analysis import BenchmarkDefinition


class BenchmarkChipGroup(QFrame):
    selection_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("cssClass", "benchmarkChipGroup")
        self._buttons: Dict[str, QPushButton] = {}
        self._column_count = 4

        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setHorizontalSpacing(8)
        self._layout.setVerticalSpacing(10)
        for col in range(self._column_count):
            self._layout.setColumnStretch(col, 1)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

    def set_benchmarks(self, definitions: List[BenchmarkDefinition]) -> None:
        selected_codes = set(self.selected_codes()) if self._buttons else set()
        self.blockSignals(True)

        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._buttons.clear()

        for index, definition in enumerate(definitions):
            button = QPushButton(self._format_label(definition.label))
            button.setCheckable(True)
            button.setChecked(definition.code in selected_codes if selected_codes else True)
            button.setProperty("cssClass", "benchmarkChip")
            button.setMinimumWidth(0)
            button.setMinimumHeight(48)
            button.toggled.connect(self.selection_changed.emit)
            row = index // self._column_count
            col = index % self._column_count
            self._layout.addWidget(button, row, col)
            self._buttons[definition.code] = button

        self.blockSignals(False)
        self.setMinimumHeight(max(48, self._layout.sizeHint().height()))
        self.updateGeometry()

    def selected_codes(self) -> List[str]:
        return [code for code, button in self._buttons.items() if button.isChecked()]

    def _format_label(self, label: str) -> str:
        if len(label) <= 11 or " " not in label:
            return label
        first, rest = label.split(" ", 1)
        return f"{first}\n{rest}"
