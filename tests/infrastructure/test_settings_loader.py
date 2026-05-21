from __future__ import annotations

import pytest

from config import settings_loader


REQUIRED_ENV = {
    "DB_HOST": "localhost",
    "DB_PORT": "3306",
    "DB_USER": "user",
    "DB_PASSWORD": "password",
    "DB_NAME": "portfoySim",
    "POOL_NAME": "portfoy_pool",
    "POOL_SIZE": "5",
}


def _disable_env_file(monkeypatch, tmp_path):
    monkeypatch.setattr(settings_loader, "_env_file_path", lambda: tmp_path / "missing.env")


def _clear_required_env(monkeypatch):
    for key in REQUIRED_ENV:
        monkeypatch.delenv(key, raising=False)


def test_load_settings_requires_db_password(monkeypatch, tmp_path):
    _disable_env_file(monkeypatch, tmp_path)
    _clear_required_env(monkeypatch)

    for key, value in REQUIRED_ENV.items():
        if key != "DB_PASSWORD":
            monkeypatch.setenv(key, value)

    with pytest.raises(settings_loader.SettingsError, match="DB_PASSWORD"):
        settings_loader.load_settings()


def test_load_settings_rejects_invalid_integer(monkeypatch, tmp_path):
    _disable_env_file(monkeypatch, tmp_path)
    _clear_required_env(monkeypatch)

    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("POOL_SIZE", "not-an-int")

    with pytest.raises(settings_loader.SettingsError, match="POOL_SIZE"):
        settings_loader.load_settings()


def test_load_settings_builds_mysql_config(monkeypatch, tmp_path):
    _disable_env_file(monkeypatch, tmp_path)
    _clear_required_env(monkeypatch)

    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)

    config = settings_loader.load_settings()

    assert config.host == "localhost"
    assert config.port == 3306
    assert config.user == "user"
    assert config.password == "password"
    assert config.database == "portfoySim"
    assert config.pool_name == "portfoy_pool"
    assert config.pool_size == 5
