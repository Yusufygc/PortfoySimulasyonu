from __future__ import annotations

from src.qt_compat.qtgui import QIntValidator, QValidator
from src.qt_compat.qtwidgets import QSpinBox


class LotSpinBox(QSpinBox):
    """Integer-only lot input that keeps typed values predictable."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setGroupSeparatorShown(False)
        self.setRange(1, 1_000_000)
        self.lineEdit().setValidator(QIntValidator(1, 1_000_000, self))
        self.lineEdit().setMaxLength(7)

    def setMaximum(self, maximum: int) -> None:  # noqa: N802 - Qt API
        super().setMaximum(maximum)
        self._sync_validator()

    def setMinimum(self, minimum: int) -> None:  # noqa: N802 - Qt API
        super().setMinimum(minimum)
        self._sync_validator()

    def setRange(self, minimum: int, maximum: int) -> None:  # noqa: N802 - Qt API
        super().setRange(minimum, maximum)
        self._sync_validator()

    def has_valid_input(self) -> bool:
        text = self.lineEdit().text().strip()
        if not text or not text.isdigit():
            return False
        value = int(text)
        return self.minimum() <= value <= self.maximum()

    def valueFromText(self, text: str) -> int:  # noqa: N802 - Qt API
        cleaned = "".join(char for char in (text or "") if char.isdigit())
        if not cleaned:
            return self.value()
        value = int(cleaned)
        if value < self.minimum() or value > self.maximum():
            return self.value()
        return value

    def validate(self, text: str, pos: int):  # noqa: N802 - Qt API
        if text == "":
            return QValidator.Intermediate, text, pos
        if not text.isdigit():
            return QValidator.Invalid, text, pos
        value = int(text)
        if self.minimum() <= value <= self.maximum():
            return QValidator.Acceptable, text, pos
        return QValidator.Intermediate if value > self.maximum() else QValidator.Invalid, text, pos

    def fixup(self, text: str) -> str:
        cleaned = "".join(char for char in (text or "") if char.isdigit())
        if not cleaned:
            return str(self.value())
        return str(max(self.minimum(), min(self.maximum(), int(cleaned))))

    def _sync_validator(self) -> None:
        line_edit = self.lineEdit()
        if line_edit is None:
            return
        line_edit.setValidator(QIntValidator(self.minimum(), self.maximum(), self))
        line_edit.setMaxLength(max(1, len(str(self.maximum()))))
