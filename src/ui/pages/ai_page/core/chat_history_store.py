import json
from datetime import datetime
from uuid import uuid4

from PyQt5.QtCore import QSettings

from src.ui.pages.ai_page.core.models import ChatMessage, ChatSession, MessageRole


SESSIONS_KEY = "ai_chat/sessions"
LAST_ACTIVE_SESSION_KEY = "ai_chat/last_active_session_id"
WELCOME_MESSAGE = "Merhaba! Finans, piyasa analizi ve portföy yönetimi hakkında size nasıl yardımcı olabilirim?"
EMPTY_CHAT_TITLE = "Yeni sohbet"
MAX_TITLE_LENGTH = 48


class ChatHistoryStore:
    def __init__(self, settings: QSettings | None = None) -> None:
        self._settings = settings or QSettings("PortfoySimulasyonu", "PortfoySimulasyonu")

    def load_sessions(self) -> list[ChatSession]:
        raw = self._settings.value(SESSIONS_KEY, "", type=str)
        if not raw:
            return []
        try:
            payload = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return []
        if not isinstance(payload, list):
            return []
        sessions = []
        for item in payload:
            session = self._session_from_dict(item)
            if session is not None:
                sessions.append(session)
        return sessions

    def save_sessions(self, sessions: list[ChatSession]) -> None:
        payload = [self._session_to_dict(session) for session in sessions]
        self._settings.setValue(SESSIONS_KEY, json.dumps(payload, ensure_ascii=False))
        self._settings.sync()

    def get_last_active_session_id(self) -> str | None:
        value = self._settings.value(LAST_ACTIVE_SESSION_KEY, "", type=str)
        return value or None

    def set_last_active_session_id(self, session_id: str | None) -> None:
        if session_id:
            self._settings.setValue(LAST_ACTIVE_SESSION_KEY, session_id)
        else:
            self._settings.remove(LAST_ACTIVE_SESSION_KEY)
        self._settings.sync()

    def create_session(self, messages: list[ChatMessage] | None = None, title: str = EMPTY_CHAT_TITLE) -> ChatSession:
        now = datetime.now()
        return ChatSession(
            id=uuid4().hex,
            title=title,
            messages=list(messages or []),
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def default_messages() -> list[ChatMessage]:
        return [ChatMessage(MessageRole.AI, WELCOME_MESSAGE)]

    @staticmethod
    def title_from_message(text: str) -> str:
        compact = " ".join(text.strip().split())
        if not compact:
            return EMPTY_CHAT_TITLE
        if len(compact) <= MAX_TITLE_LENGTH:
            return compact
        return compact[: MAX_TITLE_LENGTH - 1].rstrip() + "…"

    @staticmethod
    def _session_to_dict(session: ChatSession) -> dict:
        return {
            "id": session.id,
            "title": session.title,
            "created_at": session.created_at.isoformat(timespec="seconds"),
            "updated_at": session.updated_at.isoformat(timespec="seconds"),
            "messages": [ChatHistoryStore._message_to_dict(message) for message in session.messages],
        }

    @staticmethod
    def _message_to_dict(message: ChatMessage) -> dict:
        return {
            "role": message.role.value,
            "content": message.content,
            "display_content": message.display_content,
            "timestamp": message.timestamp.isoformat(timespec="seconds"),
        }

    @staticmethod
    def _session_from_dict(data) -> ChatSession | None:
        if not isinstance(data, dict):
            return None
        session_id = str(data.get("id") or "").strip()
        if not session_id:
            return None
        messages = []
        for item in data.get("messages") or []:
            message = ChatHistoryStore._message_from_dict(item)
            if message is not None:
                messages.append(message)
        return ChatSession(
            id=session_id,
            title=str(data.get("title") or EMPTY_CHAT_TITLE),
            messages=messages,
            created_at=_parse_datetime(data.get("created_at")),
            updated_at=_parse_datetime(data.get("updated_at")),
        )

    @staticmethod
    def _message_from_dict(data) -> ChatMessage | None:
        if not isinstance(data, dict):
            return None
        try:
            role = MessageRole(data.get("role"))
        except ValueError:
            return None
        content = data.get("content")
        if not isinstance(content, str):
            return None
        display_content = data.get("display_content")
        return ChatMessage(
            role=role,
            content=content,
            display_content=display_content if isinstance(display_content, str) else None,
            timestamp=_parse_datetime(data.get("timestamp")),
        )


def _parse_datetime(value) -> datetime:
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    return datetime.now()
