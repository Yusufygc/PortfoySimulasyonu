from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ui.main_window import MainWindow


def test_main_window_title_with_portfoysim_env_unset(monkeypatch, qapp):
    monkeypatch.delenv("PORTFOYSIM_ENV", raising=False)
    
    # Mock complex parts
    monkeypatch.setattr("src.ui.main_window.PageFactory", lambda **kwargs: None)
    monkeypatch.setattr("src.ui.main_window.LivePriceRefreshController", lambda **kwargs: SimpleNamespace(start=lambda: None))
    monkeypatch.setattr(MainWindow, "_init_ui", lambda self: None)
    monkeypatch.setattr(MainWindow, "_goto_page", lambda self, idx: None)
    monkeypatch.setattr(MainWindow, "_connect_model_portfolio_price_persister", lambda self: None)
    monkeypatch.setattr(MainWindow, "_start_auto_price_backfill_once", lambda self: None)
    monkeypatch.setattr(MainWindow, "_start_auto_corporate_action_discovery_once", lambda self: None)
    
    container = SimpleNamespace(
        price_lookup_service=SimpleNamespace(lookup_price_for_ticker=lambda *args: None),
    )
    
    window = MainWindow(container)
    assert window.windowTitle() == "Portföy Simülasyonu"
    window.close()


def test_main_window_title_with_portfoysim_env_set(monkeypatch, qapp):
    monkeypatch.setenv("PORTFOYSIM_ENV", "test")
    
    # Mock complex parts
    monkeypatch.setattr("src.ui.main_window.PageFactory", lambda **kwargs: None)
    monkeypatch.setattr("src.ui.main_window.LivePriceRefreshController", lambda **kwargs: SimpleNamespace(start=lambda: None))
    monkeypatch.setattr(MainWindow, "_init_ui", lambda self: None)
    monkeypatch.setattr(MainWindow, "_goto_page", lambda self, idx: None)
    monkeypatch.setattr(MainWindow, "_connect_model_portfolio_price_persister", lambda self: None)
    monkeypatch.setattr(MainWindow, "_start_auto_price_backfill_once", lambda self: None)
    monkeypatch.setattr(MainWindow, "_start_auto_corporate_action_discovery_once", lambda self: None)
    
    container = SimpleNamespace(
        price_lookup_service=SimpleNamespace(lookup_price_for_ticker=lambda *args: None),
    )
    
    window = MainWindow(container)
    assert window.windowTitle() == "Portföy Simülasyonu [TEST ORTAMI]"
    window.close()
