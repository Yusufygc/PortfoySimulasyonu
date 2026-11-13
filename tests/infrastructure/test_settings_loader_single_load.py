"""Ayar yükleme: .env ve sır deposu `load_app_settings` başına yalnızca bir kez okunur."""
from __future__ import annotations

from config import settings_loader


def test_load_app_settings_reads_env_and_secret_store_once(monkeypatch):
    calls = []
    monkeypatch.setattr(settings_loader, "_load_project_env", lambda: calls.append(1))

    settings = settings_loader.load_app_settings()

    assert len(calls) == 1
    assert settings.market.tcmb_deposit_rate_fallback is not None


def test_public_loaders_still_load_env_themselves(monkeypatch):
    calls = []
    monkeypatch.setattr(settings_loader, "_load_project_env", lambda: calls.append(1))

    settings_loader.load_ai_settings()
    settings_loader.load_market_settings()

    assert len(calls) == 2
