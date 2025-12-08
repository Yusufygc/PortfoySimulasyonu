# src/ui/style.py

from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtWidgets import QApplication

# --- Renk Paleti (Modern Dark Brokerage) ---
BG_MAIN = "#0f172a"       # Ana pencere arka planı
BG_PANEL = "#1e293b"      # Yan menü ve kartlar
BG_TABLE_ALT = "#334155"  # Tablo alternatif satır
TEXT_WHITE = "#f8fafc"    # Ana metinler
TEXT_GRAY = "#94a3b8"     # Alt metinler / başlıklar
ACCENT_BLUE = "#3b82f6"   # Vurgu rengi (Butonlar)
ACCENT_HOVER = "#2563eb"  # Buton üzerine gelince
BORDER_COLOR = "#334155"  # İnce çizgiler

def apply_app_style(app: QApplication) -> None:
    """
    Uygulamaya modern, profesyonel bir finans arayüzü stili uygular.
    """
    # 1. Temel Palette Ayarları (Yedek olarak)
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(BG_MAIN))
    palette.setColor(QPalette.WindowText, QColor(TEXT_WHITE))
    palette.setColor(QPalette.Base, QColor(BG_MAIN))
    palette.setColor(QPalette.AlternateBase, QColor(BG_PANEL))
    palette.setColor(QPalette.Text, QColor(TEXT_WHITE))
    palette.setColor(QPalette.Button, QColor(BG_PANEL))
    palette.setColor(QPalette.ButtonText, QColor(TEXT_WHITE))
    palette.setColor(QPalette.Highlight, QColor(ACCENT_BLUE))
    palette.setColor(QPalette.HighlightedText, QColor(TEXT_WHITE))
    app.setPalette(palette)

    # 2. Gelişmiş QSS (Style Sheet)
    app.setStyleSheet(f"""
        /* GENEL AYARLAR */
        QMainWindow {{
            background-color: {BG_MAIN};
        }}
        QWidget {{
            font-family: "Segoe UI", "Roboto", Helvetica, Arial, sans-serif;
            font-size: 14px;
            color: {TEXT_WHITE};
        }}

        /* YAN MENÜ (SIDEBAR) */
        QFrame#sidebar {{
            background-color: {BG_PANEL};
            border-right: 1px solid {BORDER_COLOR};
        }}
        
        /* BİLGİ KARTLARI (DASHBOARD CARDS) */
        QFrame#infoCard {{
            background-color: {BG_PANEL};
            border: 1px solid {BORDER_COLOR};
            border-radius: 12px;
        }}
        QLabel#cardTitle {{
            color: {TEXT_GRAY};
            font-size: 13px;
            font-weight: 600;
            background-color: transparent;
        }}
        QLabel#cardValue {{
            color: {TEXT_WHITE};
            font-size: 26px;
            font-weight: 700;
            background-color: transparent;
        }}

        /* BUTONLAR */
        QPushButton {{
            background-color: transparent;
            color: {TEXT_GRAY};
            border: 1px solid transparent;
            border-radius: 8px;
            padding: 10px 15px;
            text-align: left;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: #334155;
            color: {TEXT_WHITE};
        }}
        QPushButton:pressed {{
            background-color: {ACCENT_BLUE};
            color: white;
        }}
        
        /* Primary Button (Öne Çıkan) */
        QPushButton#primaryButton {{
            background-color: {ACCENT_BLUE};
            color: white;
            text-align: center;
            font-weight: 600;
        }}
        QPushButton#primaryButton:hover {{
            background-color: {ACCENT_HOVER};
        }}

        /* TABLO TASARIMI */
        QTableView {{
            background-color: {BG_MAIN};
            gridline-color: {BORDER_COLOR};
            border: none;
            selection-background-color: {ACCENT_BLUE};
            selection-color: white;
        }}
        QHeaderView::section {{
            background-color: {BG_MAIN};
            color: {TEXT_GRAY};
            padding: 8px;
            border: none;
            border-bottom: 2px solid {BORDER_COLOR};
            font-weight: bold;
            text-transform: uppercase;
            font-size: 12px;
        }}
        QTableCornerButton::section {{
            background-color: {BG_MAIN};
            border: none;
        }}

        /* INPUT ALANLARI (Dialoglar vb.) */
        QLineEdit, QSpinBox, QDateEdit, QTimeEdit {{
            background-color: {BG_PANEL};
            border: 1px solid {BORDER_COLOR};
            border-radius: 6px;
            padding: 8px;
            color: {TEXT_WHITE};
            selection-background-color: {ACCENT_BLUE};
        }}
        QLineEdit:focus, QSpinBox:focus {{
            border: 1px solid {ACCENT_BLUE};
        }}
        
        /* DIALOGLAR */
        QDialog {{
            background-color: {BG_MAIN};
        }}
    """)