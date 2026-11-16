"""Test ortamı rozeti: PORTFOYSIM_ENV=test iken başlık çubuğunda görünür, diğer ortamlarda gizlidir."""
from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

from src.ui_qml.app import environment_badge

QML_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"


@pytest.mark.parametrize("env,expected", [("test", "TEST ORTAMI"), (" TEST ", "TEST ORTAMI"), ("prod", ""), ("", "")])
def test_environment_badge_text(monkeypatch, env, expected):
    monkeypatch.setenv("PORTFOYSIM_ENV", env)
    assert environment_badge() == expected


def _badge_visible(badge: str) -> bool:
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    engine.rootContext().setContextProperty("environmentBadge", badge)
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / "components/WindowHeader.qml")))
    if not component.isReady():
        pytest.fail("; ".join(e.toString() for e in component.errors()))
    header = component.create()
    stack = [header]
    while stack:
        item = stack.pop()
        if item.property("badge") is not None and item.property("badge") == badge:
            return bool(item.property("visible"))
        stack.extend(item.childItems())
    return False


def test_header_shows_badge_only_when_set(qapp):
    assert _badge_visible("TEST ORTAMI") is True
    assert _badge_visible("") is False
