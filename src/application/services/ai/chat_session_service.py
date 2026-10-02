"""Yapay zeka sohbet oturumlarının yönetimi (liste, oluşturma, kaydetme, silme, son aktif oturum).

Kalıcılığı `IChatHistoryRepository` portuna devreder. Eski arayüzün `ChatSessionManager`ının uygulama katmanındaki karşılığıdır;
arayüzden bağımsızdır ve aynı depoyu paylaştığı için eski arayüzde başlayan sohbetler de listelenir.
Yalnızca kullanıcı mesajı içeren oturumlar kaydedilir (yalnızca karşılama mesajı olan boş sohbet geçmişi kirletmez).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import uuid4

from src.domain.models.ai_analysis import ChatMessage, ChatSession, MessageRole
from src.domain.ports.repositories.i_chat_history_repo import IChatHistoryRepository

MAX_TITLE_LENGTH = 48
MAX_SESSIONS = 50
DEFAULT_TITLE = "Yeni Sohbet"


class ChatSessionService:
    def __init__(self, repo: IChatHistoryRepository, max_sessions: int = MAX_SESSIONS) -> None:
        self._repo = repo
        self._max_sessions = max_sessions

    # ------------------------------------------------------------------ okuma

    def list_sessions(self) -> List[ChatSession]:
        """Kayıtlı oturumlar, en son güncellenen önce."""
        return sorted(self._repo.load_sessions(), key=lambda s: s.updated_at, reverse=True)

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        return next((s for s in self._repo.load_sessions() if s.id == session_id), None)

    def get_last_active_session(self) -> Optional[ChatSession]:
        session_id = self._repo.get_last_active_session_id()
        return self.get_session(session_id) if session_id else None

    # ------------------------------------------------------------------ yazma

    def create_session(self, messages: Optional[List[ChatMessage]] = None, title: str = DEFAULT_TITLE) -> ChatSession:
        """Bellekte yeni oturum üretir; ilk kullanıcı mesajı kaydedilene dek depoya yazılmaz."""
        now = datetime.now()
        return ChatSession(id=uuid4().hex, title=title, messages=list(messages or []), created_at=now, updated_at=now)

    def save_session(self, session: ChatSession) -> bool:
        """Oturumu kaydeder (yeni başlık ilk kullanıcı mesajından türetilir). Kullanıcı mesajı yoksa kaydetmez."""
        first_user = next((m for m in session.messages if m.role == MessageRole.USER), None)
        if first_user is None:
            return False
        if not session.title or session.title == DEFAULT_TITLE:
            session.title = self.title_from_message(first_user.content)
        sessions = [s for s in self._repo.load_sessions() if s.id != session.id]
        # Kaydedilen oturum her zaman listenin başında olmalı (saat çözünürlüğü eşitliği sıralamayı bozmasın)
        now = datetime.now()
        newest = max((s.updated_at for s in sessions), default=None)
        session.updated_at = now if newest is None or now > newest else newest + timedelta(microseconds=1)
        sessions.append(session)
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        self._repo.save_sessions(sessions[: self._max_sessions])
        self._repo.set_last_active_session_id(session.id)
        return True

    def delete_session(self, session_id: str) -> None:
        remaining = [s for s in self._repo.load_sessions() if s.id != session_id]
        self._repo.save_sessions(remaining)
        if self._repo.get_last_active_session_id() == session_id:
            self._repo.set_last_active_session_id(None)

    def set_active(self, session_id: Optional[str]) -> None:
        self._repo.set_last_active_session_id(session_id)

    @staticmethod
    def title_from_message(text: str) -> str:
        compact = " ".join((text or "").strip().split())
        if not compact:
            return DEFAULT_TITLE
        if len(compact) <= MAX_TITLE_LENGTH:
            return compact
        return compact[: MAX_TITLE_LENGTH - 1].rstrip() + "…"
