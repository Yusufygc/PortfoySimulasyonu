from src.ui.shared.locale_tr import L10N
import re

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from src.ui.pages.ai_page.core.models import ChatMessage, MessageRole


AI_DOCUMENT_STYLE = L10N.P_MARGINTOP_0PX_MARGINBOTTOM_12PX

_LIST_ITEM_RE = re.compile(r"^(\s*[-*+]\s+|\s*[\u2022]\s+|\s*\d+[\.)]\s+)")


def normalize_ai_markdown(content: str) -> str:
    """Make plain LLM section titles render as bold Markdown headings."""
    if not content:
        return content

    lines = content.splitlines()
    normalized: list[str] = []

    for index, line in enumerate(lines):
        stripped = line.strip()
        is_heading = _is_heading_candidate(stripped)

        normalized.append(f"**{stripped}**" if is_heading else line)

        next_line = lines[index + 1].strip() if index + 1 < len(lines) else ""
        if (is_heading or _is_bold_heading(stripped)) and next_line:
            normalized.append("")

    return "\n".join(normalized)


def _is_heading_candidate(line: str) -> bool:
    if not line:
        return False
    if _is_bold_heading(line) or line.startswith(("#", ">", "`")):
        return False
    if _LIST_ITEM_RE.match(line):
        return False
    if line.endswith("."):
        return False
    if len(line) > 72:
        return False
    if len(line.split()) > 9:
        return False
    if line.count(",") > 1 or ";" in line:
        return False
    return any(ch.isalpha() for ch in line)


def _is_bold_heading(line: str) -> bool:
    return (line.startswith("**") and line.endswith("**")) or (line.startswith("__") and line.endswith("__"))


class MessageBubble(QWidget):
    """Single chat message renderer for user, assistant, and system messages."""

    def __init__(self, message: ChatMessage):
        super().__init__()
        self.message = message
        self._width_ratio = 0.82
        self._message_container = None
        self.lbl_content = None
        self.markdown_content = None
        self.normalized_content = None
        self._fill_available_width = False
        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)

        visible_content = self.message.display_content or self.message.content
        time_str = self.message.timestamp.strftime("%H:%M")
        lbl_time = QLabel(time_str)
        lbl_time.setAlignment(Qt.AlignRight)

        if self.message.role == MessageRole.USER:
            self._build_bubble(main_layout, visible_content, lbl_time, "user")
            main_layout.insertStretch(0)
        elif self.message.role == MessageRole.AI:
            main_layout.addStretch()
            self._build_ai_answer(main_layout, visible_content, lbl_time)
            main_layout.addStretch()
        elif self.message.role == MessageRole.SYSTEM:
            self._build_bubble(main_layout, visible_content, lbl_time, "system")

        self._apply_max_width()

    def _build_bubble(self, main_layout: QHBoxLayout, content: str, lbl_time: QLabel, state: str) -> None:
        self.bubble = QFrame()
        self._message_container = self.bubble
        self.bubble.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        bubble_layout = QVBoxLayout(self.bubble)
        bubble_layout.setContentsMargins(14, 10, 14, 10)
        bubble_layout.setSpacing(6)

        self.lbl_content = QLabel(content)
        self.lbl_content.setWordWrap(True)
        self.lbl_content.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_content.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        if state == "user":
            self._width_ratio = 0.72
        elif state == "system":
            self._width_ratio = 0.94
            bubble_layout.addWidget(self._system_header())

        self._apply_bubble_style(state, lbl_time)
        bubble_layout.addWidget(self.lbl_content)
        bubble_layout.addWidget(lbl_time)
        main_layout.addWidget(self.bubble)

    def _build_ai_answer(self, main_layout: QHBoxLayout, content: str, lbl_time: QLabel) -> None:
        self._width_ratio = 0.94
        self._fill_available_width = True
        self.bubble = None
        self.normalized_content = normalize_ai_markdown(content)
        answer = QFrame()
        self._message_container = answer
        answer.setProperty("cssClass", "aiChatAnswer")
        answer.setProperty("centered", True)
        answer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        answer_layout = QVBoxLayout(answer)
        answer_layout.setContentsMargins(0, 0, 0, 0)
        answer_layout.setSpacing(4)

        self.markdown_content = QTextBrowser()
        self.markdown_content.setReadOnly(True)
        self.markdown_content.setOpenExternalLinks(False)
        self.markdown_content.setFrameShape(QFrame.NoFrame)
        self.markdown_content.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.markdown_content.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.markdown_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.markdown_content.setProperty("cssClass", "aiChatAnswerText")
        self.markdown_content.document().setDefaultStyleSheet(AI_DOCUMENT_STYLE)
        self.markdown_content.setMarkdown(self.normalized_content)

        lbl_time.setProperty("cssClass", "chatTime")
        lbl_time.setProperty("cssState", "ai")

        answer_layout.addWidget(self.markdown_content)
        answer_layout.addWidget(lbl_time)
        main_layout.addWidget(answer)
        self._sync_markdown_height()

    def _system_header(self) -> QLabel:
        header_text = "Otomatik Analiz Aktar\u0131m\u0131"
        content_lower = self.message.content.lower()
        if self.message.content.startswith("S\u0130STEM HATASI"):
            header_text = "Sistem Hatas\u0131"
        elif self.message.content.startswith("G\u00fcvenlik Uyar\u0131s\u0131") or "g\u00fcvenlik uyar\u0131s\u0131" in content_lower:
            header_text = "G\u00fcvenlik Uyar\u0131s\u0131"

        lbl_header = QLabel(header_text)
        lbl_header.setProperty("cssClass", "systemChatHeader")
        return lbl_header

    def _apply_bubble_style(self, state: str, lbl_time: QLabel) -> None:
        self.bubble.setProperty("cssClass", "chatBubble")
        self.bubble.setProperty("cssState", state)
        self.lbl_content.setProperty("cssClass", "chatContent")
        self.lbl_content.setProperty("cssState", state)
        lbl_time.setProperty("cssClass", "chatTime")
        lbl_time.setProperty("cssState", state)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_max_width()

    def _apply_max_width(self) -> None:
        if self._message_container is None:
            return
        available = max(280, self.width() - 16)
        target_width = int(available * self._width_ratio)
        self._message_container.setMaximumWidth(target_width)
        if self._fill_available_width:
            self._message_container.setMinimumWidth(target_width)
        self._sync_markdown_height()

    def _sync_markdown_height(self) -> None:
        if self.markdown_content is None:
            return
        viewport_width = max(260, self.markdown_content.viewport().width())
        self.markdown_content.document().setTextWidth(viewport_width)
        height = int(self.markdown_content.document().size().height()) + 8
        self.markdown_content.setFixedHeight(max(36, height))
