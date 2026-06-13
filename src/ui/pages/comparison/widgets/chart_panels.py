from src.ui.shared.locale_tr import L10N
from src.qt_compat.qtcore import QObject, QEvent, Qt, QSize
from src.qt_compat.qtgui import QAction
from src.qt_compat.qtwidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMenu, QWidget
from src.ui.core.icon_manager import IconManager


class WheelRedirectFilter(QObject):
    def __init__(self, scroll_area, parent=None):
        super().__init__(parent)
        self.scroll_area = scroll_area
        
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            delta = event.pixelDelta().y() or event.angleDelta().y()
            if delta:
                bar = self.scroll_area.verticalScrollBar()
                bar.setValue(bar.value() - delta)
            event.accept()
            return True
        return super().eventFilter(obj, event)


class ChartPlaceholder(QFrame):
    def __init__(self, text=L10N.GRAFIK_HAZIRLANIYOR, parent=None):
        super().__init__(parent)
        self.setProperty("cssClass", "comparisonChartPlaceholder")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        self.label = QLabel(text)
        self.label.setProperty("cssClass", "comparisonChartPlaceholderLabel")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        self.setMinimumHeight(600)


class ChartInfoCard(QFrame):
    def __init__(self, title: str, nedir: str, yorum: str, parent=None):
        super().__init__(parent)
        self.setProperty("cssClass", "comparisonChartInfoCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        self._icon_path = IconManager.get_icon_path("info", color="#00ffff")
        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.RichText)
        layout.addWidget(self.label)
        self.update_content(title, nedir, yorum)

    def update_content(
        self,
        title: str,
        nedir: str,
        yorum: str,
        mode_state: str | None = None,
    ) -> None:
        """Kart metnini grafik modu değişiminde yeniden oluşturur."""
        self.setProperty("cssState", mode_state or "")
        html_content = f"""
        <div style="font-family: 'Segoe UI', sans-serif; line-height: 1.5; padding: 5px;">
            <b style="color: #00ffff; font-size: 19px; text-shadow: 0 0 10px rgba(0, 255, 255, 0.4);">
                <img src="file:///{self._icon_path}" width="22" height="22" style="vertical-align: middle; margin-right: 8px;" />
                {title}
            </b>
            <p style="margin: 12px 0 0 0; color: #ffffff; font-size: 17px;">
                <b style="color: #fbbf24;">{L10N.NEDIR}:</b> {nedir}
            </p>
            <p style="margin: 8px 0 0 0; color: #ffffff; font-size: 17px;">
                <b style="color: #fbbf24;">{L10N.NASIL_YORUMLANIR}:</b> {yorum}
            </p>
        </div>
        """
        self.label.setText(html_content)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


class ChartPanel(QFrame):
    def __init__(self, title: str, content_widget: QWidget, icon_name: str | None = None, parent=None):
        super().__init__(parent)
        self.setProperty("cssClass", "comparisonChartPanel")
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
        self.title_label.setProperty("cssClass", "comparisonChartTitle")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        # Action Button for portfolio compare
        self.inspect_btn = QPushButton()
        self.inspect_btn.setMinimumHeight(32)
        inspect_icon = IconManager.get_icon("layers", color="#38bdf8", size=QSize(16, 16))
        self.inspect_btn.setIcon(inspect_icon)
        self.inspect_btn.setText(L10N.PORTFOY_ICERIGINI_KIYASLA)
        self.inspect_btn.setProperty("cssClass", "comparisonInspectButton")
        header_layout.addWidget(self.inspect_btn)
        layout.addLayout(header_layout)
        layout.addWidget(content_widget)
        
        self.inspect_btn.setVisible(False) # Invisible by default
        
    def update_portfolio_options(self, portfolio_options: list[tuple[str, str]], current_override: str | None, on_portfolio_selected) -> None:
        if not portfolio_options:
            self.inspect_btn.setVisible(False)
            return
            
        menu = QMenu(self)
        menu.setProperty("cssClass", "comparisonInspectMenu")
        
        self.actions = []
        
        # 1. Add "Küresel Seçime Dön" action
        global_action = QAction(IconManager.get_icon("refresh-cw", color="#ef4444", size=QSize(16, 16)), L10N.KURESEL_SECIME_DON, self)
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
