"""Tema metin renkleri her yüzeyde WCAG AA kontrastını (>= 4,5:1) sağlar; soluk yazı geri gelmesin."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

THEME = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "qml" / "theme" / "Theme.qml"
TEXT_TOKENS = ("textPrimary", "textSecondary", "textMuted", "textPositive", "textNegative", "textAccent", "textWarning")
SURFACES = ("bgPrimary", "bgSecondary", "bgCard", "bgInput", "bgCardHover", "bgSidebar")
MIN_RATIO = 4.5

_TOKEN = re.compile(r'readonly property color (\w+): (?:isDark \? "(#\w{6})" : "(#\w{6})"|"(#\w{6})")')


def _palette() -> dict:
    """{ad: (koyu, açık)}"""
    palette = {}
    for name, dark, light, fixed in _TOKEN.findall(THEME.read_text(encoding="utf-8")):
        palette[name] = (dark or fixed, light or fixed)
    return palette


def _luminance(color: str) -> float:
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(foreground: str, background: str) -> float:
    high, low = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (high + 0.05) / (low + 0.05)


@pytest.mark.parametrize("mode, index", [("koyu", 0), ("açık", 1)])
@pytest.mark.parametrize("token", TEXT_TOKENS)
def test_text_token_is_readable_on_every_surface(mode, index, token):
    palette = _palette()
    assert token in palette, f"{token} Theme.qml'de tanımlı değil"
    failures = {
        surface: round(contrast(palette[token][index], palette[surface][index]), 2)
        for surface in SURFACES
        if contrast(palette[token][index], palette[surface][index]) < MIN_RATIO
    }
    assert not failures, f"{mode} temada {token} yetersiz kontrast (< {MIN_RATIO}): {failures}"


def test_smallest_font_token_is_not_tiny():
    text = THEME.read_text(encoding="utf-8")
    assert int(re.search(r"fontXs: (\d+)", text).group(1)) >= 11
