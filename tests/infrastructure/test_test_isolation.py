"""Testlerin gerçek veritabanlarına yazmadığını ve .env'nin yol değişkenlerini ezmediğini doğrular."""
from __future__ import annotations

import os
from pathlib import Path

from config import settings_loader
from src.infrastructure.db import paths


def test_session_redirects_database_paths_away_from_real_data(_isolated_databases):
    sqlite = Path(os.environ["DB_SQLITE_PATH"])
    duck = Path(os.environ["DUCKDB_PATH"])

    assert sqlite.parent == _isolated_databases and duck.parent == _isolated_databases
    assert sqlite != paths.app_root() / "data" / "portfolio.db"
    assert Path(settings_loader.load_settings().db_path) == sqlite


def test_env_file_does_not_override_explicit_database_paths(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("DB_SQLITE_PATH=from_env_file.db\nDUCKDB_PATH=from_env_file.duckdb\nGEMINI_API_KEY=abc\n", encoding="utf-8")
    monkeypatch.setattr(settings_loader, "_env_file_path", lambda: env_file)
    monkeypatch.setenv("DB_SQLITE_PATH", str(tmp_path / "explicit.db"))
    monkeypatch.delenv("DUCKDB_PATH", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    config = settings_loader.load_settings()
    ai = settings_loader.load_ai_settings()

    assert Path(config.db_path) == tmp_path / "explicit.db"  # açık değer .env'yi yener
    assert ai.gemini_api_key == "abc"  # diğer anahtarlar .env'den okunmaya devam eder
    assert os.environ["DUCKDB_PATH"] == "from_env_file.duckdb"  # açık değer yoksa .env geçerli
    monkeypatch.delenv("DUCKDB_PATH", raising=False)
