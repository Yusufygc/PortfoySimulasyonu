from PyQt5.QtCore import QObject, QEvent, QCoreApplication, Qt, QSize
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMenu, QAction, QWidget
from src.ui.core.icon_manager import IconManager


class WheelRedirectFilter(QObject):
    def __init__(self, scroll_area, parent=None):
        super().__init__(parent)
        self.scroll_area = scroll_area
        
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            QCoreApplication.sendEvent(self.scroll_area, event)
            return True
        return super().eventFilter(obj, event)


class ChartPlaceholder(QFrame):
    def __init__(self, text="Grafik hazırlanıyor...", parent=None):
        super().__init__(parent)
        self.setProperty("cssClass", "panelFrame")
        self.setStyleSheet("""
            QFrame[cssClass="panelFrame"] {
                background-color: #0f172a;
                border: 1px dashed #1e293b;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        self.label = QLabel(text)
        self.label.setStyleSheet("color: #64748b; font-size: 15px; font-weight: 500;")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        self.setMinimumHeight(600)


class ChartInfoCard(QFrame):
    def __init__(self, title: str, nedir: str, yorum: str, parent=None):
        super().__init__(parent)
        self.setProperty("cssClass", "panelFramePadded")
        self.setStyleSheet("""
            QFrame[cssClass="panelFramePadded"] {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)
        
        icon_path = IconManager.get_icon_path("info", color="#00ffff")
        
        html_content = f"""
        <div style="font-family: 'Segoe UI', sans-serif; line-height: 1.5; padding: 5px;">
            <b style="color: #00ffff; font-size: 19px; text-shadow: 0 0 10px rgba(0, 255, 255, 0.4);">
                <img src="file:///{icon_path}" width="22" height="22" style="vertical-align: middle; margin-right: 8px;" />
                {title}
            </b>
            <p style="margin: 12px 0 0 0; color: #ffffff; font-size: 17px;">
                <b style="color: #fbbf24;">Nedir:</b> {nedir}
            </p>
            <p style="margin: 8px 0 0 0; color: #ffffff; font-size: 17px;">
                <b style="color: #fbbf24;">Nasıl Yorumlanır:</b> {yorum}
            </p>
        </div>
        """
        self.label = QLabel(html_content)
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.RichText)
        layout.addWidget(self.label)


class ChartPanel(QFrame):
    def __init__(self, title: str, content_widget: QWidget, icon_name: str | None = None, parent=None):
        super().__init__(parent)
        self.setProperty("cssClass", "panelFrame")
        self.setStyleSheet("""
            QFrame[cssClass="panelFrame"] {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # Header
        header_layout = QHBoxLayout()
        
        if icon_name:
            self.icon_label = QLabel()
            pixmap = IconManager.get_icon(icon_name, color="#38bdf8", size=QSize(24, 24)).pixmap(24, 24)
            self.icon_label.setPixmap(pixmap)
            header_layout.addWidget(self.icon_label)
            
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #e2e8f0; font-size: 16px; font-weight: bold;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        # Action Button for portfolio compare
        self.inspect_btn = QPushButton()
        self.inspect_btn.setMinimumHeight(32)
        inspect_icon = IconManager.get_icon("layers", color="#38bdf8", size=QSize(16, 16))
        self.inspect_btn.setIcon(inspect_icon)
        self.inspect_btn.setText("Portföy İçeriğini Kıyasla")
        self.inspect_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #38bdf8;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 12px;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #0ea5e9;
            }
            QPushButton::menu-indicator {
                image: none;
            }
        """)
        header_layout.addWidget(self.inspect_btn)
        layout.addLayout(header_layout)
        layout.addWidget(content_widget)
        
        self.inspect_btn.setVisible(False) # Invisible by default
        
    def update_portfolio_options(self, portfolio_options: list[tuple[str, str]], current_override: str | None, on_portfolio_selected) -> None:
        if not portfolio_options:
            self.inspect_btn.setVisible(False)
            return
            
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 25px 6px 25px;
                border-radius: 4px;
                color: #f8fafc;
            }
            QMenu::item:selected {
                background-color: #334155;
                color: #38bdf8;
            }
            QMenu::item:checked {
                font-weight: bold;
                color: #00ffff;
            }
        """)
        
        self.actions = []
        
        # 1. Add "Küresel Seçime Dön" action
        global_action = QAction(IconManager.get_icon("refresh-cw", color="#ef4444", size=QSize(16, 16)), "Küresel Seçime Dön", self)
        global_action.setCheckable(True)
        global_action.setChecked(current_override is None)
        global_action.triggered.connect(lambda checked: on_portfolio_selected(None))
        menu.addAction(global_action)
        self.actions.append(global_action)
        
        menu.addSeparator()
        
        # 2. Add portfolio options
        for label, code in portfolio_options:
            action = QAction(label, self)
            action.setCheckable(True)
            action.setChecked(current_override == code)
            action.triggered.connect(lambda checked, c=code: on_portfolio_selected(c))
            menu.addAction(action)
            self.actions.append(action)
            
        self.inspect_btn.setMenu(menu)
        self.inspect_btn.setVisible(True)
