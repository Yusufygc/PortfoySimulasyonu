# src/ui/shared/style_constants.py

class Colors:
    """Proje geneli renk sabitleri (Dark Theme)"""
    BG_DARK = "#0f172a"
    BG_LIGHT = "#1e293b"
    BORDER = "#334155"
    BORDER_FOCUS = "#3b82f6"
    TEXT_MAIN = "#f1f5f9"
    TEXT_MUTED = "#94a3b8"
    
    SUCCESS = "#10b981"
    SUCCESS_HOVER = "#059669"
    DANGER = "#ef4444"
    DANGER_HOVER = "#dc2626"
    INFO = "#3b82f6"

def get_input_style(font_size=14) -> str:
    """Ortak input, spinbox ve combobox stillerini döner."""
    return f"""
        QLineEdit, QDoubleSpinBox, QDateEdit, QComboBox {{
            background-color: {Colors.BG_DARK};
            color: {Colors.TEXT_MAIN};
            border: 1px solid {Colors.BORDER};
            border-radius: 6px;
            padding: 8px;
            font-size: {font_size}px;
        }}
        QLineEdit:focus, QDoubleSpinBox:focus, QDateEdit:focus, QComboBox:focus {{
            border: 1px solid {Colors.BORDER_FOCUS};
        }}
    """
