from __future__ import annotations

from datetime import datetime
from src.ui.widgets.shared import Toast

LAST_UPDATE_TOAST_DURATION_MS = 4000

class LastUpdateDisplayMixin:
    """Mixin to provide last update time formatting, labeling, and toast notifications."""
    
    def _get_last_update_time(self) -> datetime | None:
        """Must be implemented by the subclass to return a datetime object or None."""
        raise NotImplementedError
        
    def _save_last_update_time(self, updated_at: datetime):
        """Must be implemented by the subclass to persist the datetime object."""
        raise NotImplementedError

    def _get_last_update_context_id(self) -> str:
        """Return a string identifying the current context (e.g., portfolio ID), or empty string."""
        return ""

    def record_last_update_time(self, updated_at=None) -> datetime | None:
        updated_at = updated_at or datetime.now()
        
        self._save_last_update_time(updated_at)
        
        self._last_update_toast_shown_for = None
        self._sync_last_update_label(updated_at)
        return updated_at

    def show_last_update_toast_once(self, force: bool = False, detail: str | None = None) -> None:
        updated_at = self._get_last_update_time()
        if updated_at is None:
            return

        context_id = self._get_last_update_context_id()
        value = f"{context_id}:{updated_at.isoformat(timespec='seconds')}"
        if not force and getattr(self, "_last_update_toast_shown_for", None) == value:
            return

        message = self._format_last_update_message(updated_at)
        if detail:
            message = f"{message} - {detail}"
        Toast.info(
            self,
            message,
            duration_ms=LAST_UPDATE_TOAST_DURATION_MS,
            position="top",
        )
        self._last_update_toast_shown_for = value

    def _sync_last_update_label(self, updated_at=None) -> None:
        updated_at = updated_at or self._get_last_update_time()
        if hasattr(self, "lbl_last_update"):
            if updated_at:
                self.lbl_last_update.setText(self._format_last_update_message(updated_at))
            else:
                self.lbl_last_update.setText("")

    @staticmethod
    def _format_last_update_message(updated_at: datetime) -> str:
        return f"Son güncelleme: {updated_at.strftime('%d.%m.%Y %H:%M')} (15dk gecikmeli)"
