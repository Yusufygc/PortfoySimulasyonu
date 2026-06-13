from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re

from src.qt_compat.qtgui import QValidator
from src.qt_compat.qtwidgets import QDoubleSpinBox


def _normalize_suffix(suffix: str) -> str:
    clean = (suffix or "").strip()
    if not clean:
        return ""
    if clean in {"₺", "â‚º", "Ã¢â€šÂº"}:
        return " TL"
    return f" {clean}" if not clean.startswith(" ") else clean


def _normalize_numeric_text(text: str) -> str:
    clean = (text or "").replace(" ", "")
    if clean.count("-") > 1 or ("-" in clean and not clean.startswith("-")):
        raise ValueError("invalid numeric input")

    sign = ""
    if clean.startswith("-"):
        sign = "-"
        clean = clean[1:]
    if not clean:
        return sign
    if re.search(r"[^0-9.,]", clean):
        raise ValueError("invalid numeric input")

    comma_count = clean.count(",")
    dot_count = clean.count(".")
    if comma_count and dot_count:
        last_comma = clean.rfind(",")
        last_dot = clean.rfind(".")
        decimal_sep = "," if last_comma > last_dot else "."
        group_sep = "." if decimal_sep == "," else ","
        clean = clean.replace(group_sep, "").replace(decimal_sep, ".")
    elif comma_count:
        if comma_count > 1:
            raise ValueError("invalid numeric input")
        clean = clean.replace(",", ".")
    elif dot_count:
        if dot_count > 1:
            parts = clean.split(".")
            if not all(part.isdigit() for part in parts) or not all(len(part) == 3 for part in parts[1:]):
                raise ValueError("invalid numeric input")
            clean = "".join(parts)
        else:
            whole, fraction = clean.split(".", 1)
            if fraction == "":
                clean = f"{whole}."
            elif len(fraction) == 3 and 1 <= len(whole) <= 3:
                clean = whole + fraction
            else:
                clean = f"{whole}.{fraction}"
    return sign + clean


class CurrencySpinBox(QDoubleSpinBox):
    """Financial input that edits raw numbers and displays formatted TRY values on blur."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._display_suffix = " TL"
        self._editing = False
        self._last_user_text = ""
        self._suppress_text_tracking = False
        self._focus_value = self.value()
        super().setSuffix("")
        self.setGroupSeparatorShown(False)
        self.lineEdit().textChanged.connect(self._remember_user_text)
        self.lineEdit().cursorPositionChanged.connect(self._keep_cursor_inside_number)

    def setSuffix(self, suffix: str) -> None:  # noqa: N802 - Qt API
        self._display_suffix = _normalize_suffix(suffix)
        super().setSuffix("")
        self._set_line_text(self.textFromValue(self.value()), track=False)

    def setValue(self, value: float) -> None:  # noqa: N802 - Qt API
        self._last_user_text = ""
        super().setValue(value)
        self._focus_value = self.value()

    def decimal_value(self) -> Decimal:
        return Decimal(str(self.value()))

    get_raw_value = decimal_value

    def input_decimal_value(self) -> Decimal:
        return self._strict_decimal_from_text(self._last_user_text if self._last_user_text else self.lineEdit().text())

    def has_valid_input(self, require_positive: bool = False) -> bool:
        try:
            value = self._strict_decimal_from_text(self._last_user_text if self._last_user_text else self.lineEdit().text())
        except (InvalidOperation, ValueError):
            return False
        if require_positive and value <= 0:
            return False
        return Decimal(str(self.minimum())) <= value <= Decimal(str(self.maximum()))

    def setText(self, text: str) -> None:  # noqa: N802 - compatibility with QLineEdit call sites
        if not (text or "").strip():
            self.clear()
            return
        self._last_user_text = text
        self.setValue(self.valueFromText(text))
        self._set_line_text(self.textFromValue(self.value()), track=False)

    def clear(self) -> None:
        self.setValue(self.minimum())
        self._last_user_text = ""
        self.lineEdit().clear()

    def textFromValue(self, value: float) -> str:  # noqa: N802 - Qt API
        if self._editing:
            return self._format_edit(value)
        number = f"{value:,.{self.decimals()}f}".replace(",", "_").replace(".", ",").replace("_", ".")
        return f"{number}{self._display_suffix}"

    def valueFromText(self, text: str) -> float:  # noqa: N802 - Qt API
        try:
            value = self._strict_decimal_from_text(text)
        except (InvalidOperation, ValueError):
            return self.value()
        if not Decimal(str(self.minimum())) <= value <= Decimal(str(self.maximum())):
            return self.value()
        return float(value)

    def validate(self, text: str, pos: int):  # noqa: N802 - Qt API
        raw = self._strip_currency_text(text)
        if raw in {"", "-", ".", ",", "-.", "-,"}:
            return QValidator.Intermediate, text, pos
        if re.search(r"[^0-9.,\-\s]", raw):
            return QValidator.Invalid, text, pos
        if raw.count("-") > 1 or ("-" in raw and not raw.lstrip().startswith("-")):
            return QValidator.Invalid, text, pos
        try:
            clean = _normalize_numeric_text(raw)
            Decimal(clean)
        except (InvalidOperation, ValueError):
            return QValidator.Invalid, text, pos

        decimals = clean.partition(".")[2]
        if len(decimals) > self.decimals():
            return QValidator.Invalid, text, pos
        return QValidator.Acceptable, text, pos

    def focusInEvent(self, event) -> None:  # noqa: N802 - Qt API
        self._editing = True
        self._focus_value = self.value()
        text = self._format_edit(self.value())
        self._last_user_text = text
        self._set_line_text(text, track=False)
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:  # noqa: N802 - Qt API
        if self.has_valid_input():
            self.setValue(self.valueFromText(self._last_user_text if self._last_user_text else self.lineEdit().text()))
            self._last_user_text = ""
            self._editing = False
            super().focusOutEvent(event)
            self._set_line_text(self.textFromValue(self.value()), track=False)
            return
        self._editing = False
        super().setValue(self._focus_value)
        self._set_line_text(self.textFromValue(self.value()), track=False)
        event.accept()

    def _remember_user_text(self, text: str) -> None:
        if self._suppress_text_tracking:
            return
        self._last_user_text = text

    def _set_line_text(self, text: str, track: bool = False) -> None:
        previous = self._suppress_text_tracking
        self._suppress_text_tracking = not track
        self.lineEdit().setText(text)
        self._suppress_text_tracking = previous

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

    def _format_edit(self, value: float) -> str:
        text = f"{value:,.{self.decimals()}f}".replace(",", "_").replace(".", ",").replace("_", ".")
        if "," in text:
            text = text.rstrip("0").rstrip(",")
        return text

    def _strict_decimal_from_text(self, text: str) -> Decimal:
        raw = self._strip_currency_text(text)
        if not raw:
            raise ValueError("empty numeric input")
        if re.search(r"[^0-9.,\-\s]", raw):
            raise ValueError("invalid numeric input")
        if raw.count("-") > 1 or ("-" in raw and not raw.lstrip().startswith("-")):
            raise ValueError("invalid numeric input")
        clean = _normalize_numeric_text(raw)
        if clean in {"", "-", ".", "-."}:
            raise ValueError("invalid numeric input")
        return Decimal(clean)

    def _strip_currency_text(self, text: str) -> str:
        clean = (text or "").strip()
        suffix = self._display_suffix.strip()
        if suffix and clean.endswith(suffix):
            clean = clean[: -len(suffix)].strip()
        return (
            clean.replace("₺", "")
            .replace("â‚º", "")
            .replace("Ã¢â€šÂº", "")
            .replace("TL", "")
            .replace("tl", "")
            .strip()
        )

