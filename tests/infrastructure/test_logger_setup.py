import logging
import sys

import pytest

from src.infrastructure.logging import logger_setup


@pytest.fixture(autouse=True)
def clean_root_logger():
    root = logging.getLogger()
    old_handlers = list(root.handlers)
    old_level = root.level
    root.handlers.clear()
    yield
    for handler in root.handlers:
        handler.close()
    root.handlers.clear()
    root.handlers.extend(old_handlers)
    root.setLevel(old_level)


def test_setup_logger_uses_env_levels_and_does_not_duplicate_handlers(monkeypatch, tmp_path):
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("LOG_CONSOLE_LEVEL", "ERROR")
    monkeypatch.setenv("LOG_FILE_LEVEL", "INFO")

    logger_setup.setup_logger()
    logger_setup.setup_logger()

    assert logging.getLogger().level == logging.WARNING
    assert len(logging.getLogger().handlers) == 2
    assert (tmp_path / "app.log").exists()


def test_setup_logger_redacts_sensitive_env_values(monkeypatch, tmp_path):
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    monkeypatch.setenv("DB_PASSWORD", "very-secret-password")

    logger = logger_setup.setup_logger()
    logger.error("database password=%s", "very-secret-password")
    for handler in logger.handlers:
        handler.flush()

    log_text = (tmp_path / "app.log").read_text(encoding="utf-8")
    assert "very-secret-password" not in log_text
    assert "database password=***" in log_text


def test_global_exception_handler_logs_unhandled_exception(caplog):
    with caplog.at_level(logging.CRITICAL):
        logger_setup.handle_exception(RuntimeError, RuntimeError("boom"), None)

    assert "Kritik Hata" in caplog.text
    assert "boom" in caplog.text


def test_global_exception_handler_keeps_keyboard_interrupt(monkeypatch):
    calls = []
    monkeypatch.setattr(sys, "__excepthook__", lambda *args: calls.append(args))

    logger_setup.handle_exception(KeyboardInterrupt, KeyboardInterrupt(), None)

    assert calls
    assert calls[0][0] is KeyboardInterrupt
