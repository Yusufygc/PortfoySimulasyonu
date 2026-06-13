from datetime import date, time
from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6")
from src.qt_compat.qtwidgets import QMessageBox

from src.ui.shared.market_session_confirm import validate_market_session_open


class FakeMarketSessionService:
    def __init__(self, is_open):
        self._is_open = is_open

    def status_for(self, trade_date, trade_time=None):
        return SimpleNamespace(is_open=self._is_open, message="Kapali seans")


def test_market_session_helper_blocks_closed_session_with_warning(monkeypatch):
    warnings = []
    questions = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: warnings.append(args))
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: questions.append(args))

    result = validate_market_session_open(
        None,
        FakeMarketSessionService(is_open=False),
        date(2026, 6, 6),
        time(11, 0),
    )

    assert result is False
    assert warnings
    assert questions == []
    assert "BIST" in warnings[0][2]


def test_market_session_helper_allows_open_session_without_warning(monkeypatch):
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: warnings.append(args))

    result = validate_market_session_open(
        None,
        FakeMarketSessionService(is_open=True),
        date(2026, 6, 5),
        time(11, 0),
    )

    assert result is True
    assert warnings == []
