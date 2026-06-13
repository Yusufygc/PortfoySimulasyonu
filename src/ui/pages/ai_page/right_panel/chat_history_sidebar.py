from src.ui.shared.locale_tr import L10N
from src.qt_compat.qtcore import Qt, Signal
from src.qt_compat.qtwidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from src.ui.core.icon_manager import IconManager
from src.domain.models.ai_analysis import ChatSession
from src.ui.widgets.shared.controls.animated_button import AnimatedButton


class ChatHistorySidebar(QFrame):
    session_selected = Signal(str)
    session_deleted = Signal(str)
    new_session_requested = Signal()
    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[_ChatHistoryRow] = []
        self.setProperty("cssClass", "aiHistorySidebar")
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self._init_ui()
        self.hide()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel(L10N.SOHBETLER)
        title.setProperty("cssClass", "aiHistoryHeader")

        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        self.btn_new = AnimatedButton(L10N.YENI_SOHBET_1)
        self.btn_new.setIconName("plus", color="@COLOR_BG_BASE", size=18)
        self.btn_new.setProperty("cssClass", "aiHistoryNewButton")
        self.btn_new.clicked.connect(self.new_session_requested.emit)
        layout.addWidget(self.btn_new)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setProperty("cssClass", "aiHistoryScroll")

        self.content = QWidget()
        self.list_layout = QVBoxLayout(self.content)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.content)
        layout.addWidget(self.scroll_area, 1)

        self.empty_label = QLabel(L10N.HENUZ_KAYITLI_SOHBET_YOK)
        self.empty_label.setWordWrap(True)
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setProperty("cssClass", "aiHistoryEmpty")
        self.list_layout.addWidget(self.empty_label)

    def refresh(self, sessions: list[ChatSession], active_session_id: str | None) -> None:
        self._clear_rows()
        ordered = sorted(sessions, key=lambda item: item.updated_at, reverse=True)
        self.empty_label.setVisible(not ordered)
        for session in ordered:
            row = _ChatHistoryRow(session, selected=session.id == active_session_id)
            row.selected.connect(self.session_selected.emit)
            row.deleted.connect(self.session_deleted.emit)
            self._rows.append(row)
            self.list_layout.addWidget(row)
        self.list_layout.addStretch()

    def _clear_rows(self) -> None:
        while self.list_layout.count():
            child = self.list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._rows.clear()
        self.empty_label = QLabel(L10N.HENUZ_KAYITLI_SOHBET_YOK)
        self.empty_label.setWordWrap(True)
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setProperty("cssClass", "aiHistoryEmpty")
        self.list_layout.addWidget(self.empty_label)


class _ChatHistoryRow(QFrame):
    selected = Signal(str)
    deleted = Signal(str)

    def __init__(self, session: ChatSession, selected: bool = False):
        super().__init__()
        self.session = session
        self.setProperty("cssClass", "aiHistoryRow")
        self.setProperty("selected", selected)
        self.setCursor(Qt.PointingHandCursor)
        self._init_ui()

    def _init_ui(self) -> None:
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 9, 8, 9)
        row.setSpacing(8)

        icon = QLabel()
        icon.setPixmap(IconManager.get_icon(L10N.MESSAGESQUARE, color="@COLOR_PRIMARY").pixmap(16, 16))
        icon.setFixedWidth(18)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(3)

        title = QLabel(self.session.title)
        title.setWordWrap(True)
        title.setProperty("cssClass", "aiHistoryRowTitle")

        meta = QLabel(self.session.updated_at.strftime(L10N.DM_HM))
        meta.setProperty("cssClass", "aiHistoryRowMeta")

        text_col.addWidget(title)
        text_col.addWidget(meta)

        btn_delete = AnimatedButton()
        btn_delete.setIconName("trash-2", color="@COLOR_DANGER", size=16)
        btn_delete.setFixedSize(30, 30)
        btn_delete.setProperty("cssClass", "aiHistoryIconButton")
        btn_delete.clicked.connect(lambda checked=False: self.deleted.emit(self.session.id))

        row.addWidget(icon, 0, Qt.AlignTop)
        row.addLayout(text_col, 1)
        row.addWidget(btn_delete, 0, Qt.AlignTop)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.selected.emit(self.session.id)
        super().mouseReleaseEvent(event)
