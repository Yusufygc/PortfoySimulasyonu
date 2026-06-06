from __future__ import annotations

from decimal import Decimal, InvalidOperation

from PyQt5.QtGui import QValidator
from PyQt5.QtWidgets import QDoubleSpinBox


def _normalize_suffix(suffix: str) -> str:
    clean = (suffix or "").strip()
    if not clean:
        return ""
    if clean == "â‚º":
        return " TL"
    return f" {clean}" if not clean.startswith(" ") else clean


def _cursor_after_reformat(old_text: str, new_text: str, old_cursor: int) -> int:
    if old_text[:old_cursor].endswith((".", ",")):
        comma_pos = new_text.find(",")
        if comma_pos >= 0:
            return comma_pos + 1

    digits_left = sum(char.isdigit() for char in old_text[:old_cursor])
    if digits_left <= 0:
        return 0

    seen = 0
    for index, char in enumerate(new_text):
        if char.isdigit():
            seen += 1
            if seen == digits_left:
                return index + 1
    return len(new_text)


class CurrencySpinBox(QDoubleSpinBox):
    """Financial input that edits raw numbers and displays formatted TRY values on blur."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._display_suffix = " TL"
        self._editing = False
        super().setSuffix("")
        self.setGroupSeparatorShown(False)
        self.lineEdit().textEdited.connect(self._sanitize_edited_text)
        self.lineEdit().cursorPositionChanged.connect(self._keep_cursor_inside_number)

    def setSuffix(self, suffix: str) -> None:  # noqa: N802 - Qt API
        self._display_suffix = _normalize_suffix(suffix)
        super().setSuffix("")
        self._refresh_text()

    def suffix(self) -> str:
        return self._display_suffix

    def decimal_value(self) -> Decimal:
        return Decimal(str(self.value()))

    get_raw_value = decimal_value

    def setText(self, text: str) -> None:  # noqa: N802 - compatibility with QLineEdit call sites
        if not (text or "").strip():
            self.clear()
            return

        self.setValue(self.valueFromText(text))
        self._refresh_text()

    def clear(self) -> None:
        self.setValue(self.minimum())
        self.lineEdit().clear()

    def textFromValue(self, value: float) -> str:  # noqa: N802 - Qt API
        if self._editing:
            return self._format_edit(value)
        return self._format_display(value)

    def valueFromText(self, text: str) -> float:  # noqa: N802 - Qt API
        try:
            return float(self._decimal_from_text(text))
        except (InvalidOperation, ValueError):
            return self.minimum()

    def validate(self, text: str, pos: int):  # noqa: N802 - Qt API
        clean = self._clean_edit_text(text)
        if clean in {"", "-", ".", "-."}:
            return QValidator.Intermediate, text, pos
        try:
            Decimal(clean)
        except InvalidOperation:
            return QValidator.Invalid, text, pos

        decimals = clean.partition(".")[2]
        if len(decimals) > self.decimals():
            return QValidator.Invalid, text, pos
        return QValidator.Acceptable, text, pos

    def focusInEvent(self, event) -> None:  # noqa: N802 - Qt API
        self._editing = True
        self.lineEdit().setText(self._format_edit(self.value()))
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:  # noqa: N802 - Qt API
        self.setValue(self.valueFromText(self.lineEdit().text()))
        self._editing = False
        super().focusOutEvent(event)
        self._refresh_text()

    def _refresh_text(self) -> None:
        self.lineEdit().setText(self.textFromValue(self.value()))

    def _keep_cursor_inside_number(self, _old_pos: int, new_pos: int) -> None:
        if self._editing or not self._display_suffix:
            return

        text = self.lineEdit().text()
        suffix_start = text.rfind(self._display_suffix)
        if suffix_start < 0 or new_pos <= suffix_start:
            return

        self.lineEdit().blockSignals(True)
        self.lineEdit().setCursorPosition(suffix_start)
        self.lineEdit().blockSignals(False)

    def _sanitize_edited_text(self, text: str) -> None:
        if not self._editing:
            return

        formatted = self._format_edit_text(text)
        if formatted == text:
            return

        cursor = _cursor_after_reformat(text, formatted, self.lineEdit().cursorPosition())
        self.lineEdit().blockSignals(True)
        self.lineEdit().setText(formatted)
        self.lineEdit().setCursorPosition(cursor)
        self.lineEdit().blockSignals(False)

    def _format_edit(self, value: float) -> str:
        text = f"{value:,.{self.decimals()}f}".replace(",", "_").replace(".", ",").replace("_", ".")
        if "," in text:
            text = text.rstrip("0").rstrip(",")
        return text

    def _format_edit_text(self, text: str) -> str:
        clean = self._clean_edit_text(text)
        if clean in {"", "-", ".", "-."}:
            return clean

        sign = "-" if clean.startswith("-") else ""
        unsigned = clean[1:] if sign else clean
        int_part, dot, dec_part = unsigned.partition(".")
        int_part = int_part.lstrip("0") or "0"
        grouped = f"{int(int_part):,}".replace(",", ".")

        if dot:
            return f"{sign}{grouped},{dec_part[:self.decimals()]}"
        return f"{sign}{grouped}"

    def _format_display(self, value: float) -> str:
        number = f"{value:,.{self.decimals()}f}".replace(",", "_").replace(".", ",").replace("_", ".")
        return f"{number}{self._display_suffix}"

    def _decimal_from_text(self, text: str) -> Decimal:
        clean = self._clean_edit_text(text)
        if clean in {"", "-", ".", "-."}:
            return Decimal("0")
        return Decimal(clean)

    def _clean_edit_text(self, text: str) -> str:
        clean = (text or "").strip()
        suffix = self._display_suffix.strip()
        if suffix and clean.endswith(suffix):
            clean = clean[: -len(suffix)].strip()
        clean = clean.replace("₺", "").replace("TL", "").replace("tl", "").strip()

        dot_count = clean.count(".")
        if "," in clean:
            clean = clean.replace(".", "").replace(",", ".")
        elif dot_count >= 1:
            if dot_count == 1 and clean.endswith("."):
                clean = clean
            else:
                clean = clean.replace(".", "")
        else:
            clean = clean.replace(",", ".")

        allowed = []
        decimal_seen = False
        for index, char in enumerate(clean):
            if char.isdigit():
                allowed.append(char)
            elif char == "." and not decimal_seen:
                allowed.append(char)
                decimal_seen = True
            elif char == "-" and index == 0:
                allowed.append(char)
        return "".join(allowed)

    @staticmethod
    def _normalize_suffix(suffix: str) -> str:
        clean = (suffix or "").strip()
        if not clean:
            return ""
        if clean == "₺":
            return " TL"
        return f" {clean}" if not clean.startswith(" ") else clean
