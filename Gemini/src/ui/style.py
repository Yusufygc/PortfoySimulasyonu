# src/ui/style.py

from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtWidgets import QApplication


DARK_BG = "#0f172a"      # ana arka plan (slate-900)
PANEL_BG = "#111827"     # paneller
CARD_BG = "#020617"      # summary card
ACCENT_BLUE = "#3b82f6"  # mavi accent
ACCENT_GREEN = "#22c55e"
ACCENT_RED = "#ef4444"
TEXT_PRIMARY = "#e5e7eb"
TEXT_SECONDARY = "#9ca3af"
BORDER_COLOR = "#1f2933"
HEADER_BG = "#020617"


def apply_app_style(app: QApplication) -> None:
    """
    Uygulamaya modern, koyu bir tema ve QSS uygular.
    """
    # Palette (dark mode)
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(DARK_BG))
    palette.setColor(QPalette.WindowText, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.Base, QColor(PANEL_BG))
    palette.setColor(QPalette.AlternateBase, QColor("#020617"))
    palette.setColor(QPalette.Text, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.Button, QColor(PANEL_BG))
    palette.setColor(QPalette.ButtonText, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.Highlight, QColor(ACCENT_BLUE))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))

    app.setPalette(palette)

    # QSS
    app.setStyleSheet(f"""
        QMainWindow {{
            background-color: {DARK_BG};
        }}

        QWidget {{
            font-family: "Segoe UI", "Roboto", "Helvetica Neue", Arial;
            font-size: 10pt;
            color: {TEXT_PRIMARY};
        }}

        QPushButton {{
            background-color: #111827;
            color: {TEXT_PRIMARY};
            border-radius: 6px;
            padding: 6px 12px;
            border: 1px solid #1f2937;
        }}
        QPushButton:hover {{
            background-color: #1f2937;
        }}
        QPushButton:pressed {{
            background-color: #1d4ed8;
            border-color: #1d4ed8;
        }}

        QPushButton#primaryButton {{
            background-color: {ACCENT_BLUE};
            border-color: {ACCENT_BLUE};
            color: #ffffff;
        }}
        QPushButton#primaryButton:hover {{
            background-color: #2563eb;
        }}

        QLabel {{
            color: {TEXT_SECONDARY};
        }}

        QLabel#summaryLabel {{
            color: {TEXT_PRIMARY};
            font-weight: 500;
        }}

        QTableView {{
            background-color: {PANEL_BG};
            gridline-color: #1f2933;
            border: 1px solid #1f2933;
            selection-background-color: rgba(59,130,246,0.25);
            selection-color: {TEXT_PRIMARY};
            alternate-background-color: #020617;
        }}

        QHeaderView::section {{
            background-color: {HEADER_BG};
            color: {TEXT_SECONDARY};
            padding: 6px;
            border: 0px solid #1f2937;
            border-right: 1px solid #1f2937;
            font-weight: 500;
        }}

        QTableCornerButton::section {{
            background-color: {HEADER_BG};
            border: 0px;
        }}

        QStatusBar {{
            background-color: {DARK_BG};
            color: {TEXT_SECONDARY};
        }}

                QDialog {{
            background-color: {PANEL_BG};
            border-radius: 12px;
        }}

        QLineEdit, QSpinBox, QDateEdit, QTimeEdit {{
            background-color: #020617;
            border: 1px solid #1f2937;
            border-radius: 6px;
            padding: 6px 8px;
            color: {TEXT_PRIMARY};
        }}
        QLineEdit:focus, QSpinBox:focus, QDateEdit:focus, QTimeEdit:focus {{
            border-color: {ACCENT_BLUE};
        }}

        QLineEdit::placeholder {{
            color: {TEXT_SECONDARY};
        }}

        QRadioButton {{
            color: {TEXT_PRIMARY};
        }}
        QRadioButton::indicator::unchecked {{
            border: 1px solid #4b5563;
            background-color: transparent;
        }}
        QRadioButton::indicator::checked {{
            border: 1px solid {ACCENT_BLUE};
            background-color: {ACCENT_BLUE};
        }}


    """)
