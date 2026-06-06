from PyQt5.QtWidgets import QDoubleSpinBox

class InstantDoubleSpinBox(QDoubleSpinBox):
    """Instantly formats the currency input with thousands separators as the user types."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lineEdit().textEdited.connect(self._on_text_edited)
        self.lineEdit().cursorPositionChanged.connect(self._on_cursor_position_changed)

    def _on_cursor_position_changed(self, old_pos: int, new_pos: int):
        text = self.lineEdit().text()
        suffix = self.suffix()
        suffix_len = len(suffix) if suffix and text.endswith(suffix) else 0
        max_pos = len(text) - suffix_len
        
        if new_pos > max_pos:
            self.lineEdit().blockSignals(True)
            self.lineEdit().setCursorPosition(max_pos)
            self.lineEdit().blockSignals(False)

    def _on_text_edited(self, text: str):
        cursor_pos = self.lineEdit().cursorPosition()
        suffix = self.suffix()
        suffix_len = len(suffix) if suffix and text.endswith(suffix) else 0
        text_no_suffix = text[:-suffix_len] if suffix_len > 0 else text
        pos_in_val = min(cursor_pos, len(text_no_suffix))
        
        right_non_seps = 0
        for i in range(pos_in_val, len(text_no_suffix)):
            if text_no_suffix[i] != '.':
                right_non_seps += 1
                
        clean_text = text_no_suffix.replace('.', '')
        if ',' in clean_text:
            parts = clean_text.split(',', 1)
            int_part = parts[0]
            dec_part = parts[1]
            has_comma = True
        else:
            int_part = clean_text
            dec_part = ""
            has_comma = False
            
        is_negative = int_part.startswith('-')
        digits = int_part[1:] if is_negative else int_part
        digits = ''.join(c for c in digits if c.isdigit())
        
        formatted_int = ""
        n = len(digits)
        for idx, char in enumerate(digits):
            formatted_int += char
            if (n - 1 - idx) % 3 == 0 and idx != n - 1:
                formatted_int += "."
                
        if is_negative:
            formatted_int = '-' + formatted_int
            
        formatted_text = formatted_int
        if has_comma:
            formatted_text += ',' + dec_part
            
        final_text = formatted_text
        if suffix:
            final_text += suffix
            
        # Parse value first
        val_str = clean_text.replace(',', '.')
        if suffix and val_str.endswith(suffix):
            val_str = val_str[:-len(suffix)]
        val_str = val_str.strip()
        try:
            val = float(val_str)
        except ValueError:
            val = 0.0

        # Set value silently to prevent automatic text reformatting
        self.blockSignals(True)
        self.setValue(val)
        self.blockSignals(False)

        # Set custom formatted text and restore cursor position
        self.lineEdit().blockSignals(True)
        self.lineEdit().setText(final_text)
        
        new_pos = len(formatted_text)
        non_seps_seen = 0
        for i in range(len(formatted_text) - 1, -1, -1):
            if formatted_text[i] != '.':
                non_seps_seen += 1
                if non_seps_seen == right_non_seps:
                    new_pos = i
                    break
                    
        self.lineEdit().setCursorPosition(new_pos)
        self.lineEdit().blockSignals(False)

        # Emit valueChanged signal manually to refresh summaries in real-time
        self.valueChanged.emit(val)
