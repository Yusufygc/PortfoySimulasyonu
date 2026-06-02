import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


SENSITIVE_ENV_NAMES = {
    "DB_PASSWORD",
    "GEMINI_API_KEY",
    "EVDS_API_KEY",
    "AI_CORE_API_KEY",
    "TOKEN",
    "SECRET",
    "PASSWORD",
}


def _level_from_env(name: str, default: str) -> int:
    raw_value = os.getenv(name, default).strip().upper()
    level = logging.getLevelName(raw_value)
    return level if isinstance(level, int) else logging.getLevelName(default)


def _default_log_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "logs"
    return Path.cwd() / "logs"


def _log_dir() -> Path:
    override = os.getenv("LOG_DIR")
    if override and override.strip():
        return Path(override.strip())
    return _default_log_dir()


def _sensitive_values() -> list[str]:
    values = []
    for name, value in os.environ.items():
        if not value or len(value) < 4:
            continue
        upper_name = name.upper()
        if upper_name in SENSITIVE_ENV_NAMES or any(token in upper_name for token in SENSITIVE_ENV_NAMES):
            values.append(value)
    return sorted(set(values), key=len, reverse=True)


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        for value in _sensitive_values():
            message = message.replace(value, "***")
        return message


def setup_logger():
    """
    Configure root logging for both console and rotating app.log output.
    Environment overrides:
    LOG_DIR, LOG_LEVEL, LOG_CONSOLE_LEVEL, LOG_FILE_LEVEL.
    """
    logger = logging.getLogger()
    logger.setLevel(_level_from_env("LOG_LEVEL", "INFO"))

    formatter = RedactingFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - thread=%(threadName)s - %(message)s"
    )

    log_dir = _log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(_level_from_env("LOG_FILE_LEVEL", "INFO"))
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(_level_from_env("LOG_CONSOLE_LEVEL", "DEBUG"))
    console_handler.setFormatter(formatter)

    if logger.hasHandlers():
        logger.handlers.clear()

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logging.getLogger("yfinance").setLevel(logging.CRITICAL)

    return logger


def handle_exception(exc_type, exc_value, exc_traceback):
    """
    Log unhandled exceptions through the configured root logger.
    KeyboardInterrupt keeps Python's default interrupt behavior.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger = logging.getLogger("UnhandledException")
    logger.critical(
        "Kritik Hata (Unhandled exception)",
        exc_info=(exc_type, exc_value, exc_traceback),
    )


def setup_global_exception_handler():
    sys.excepthook = handle_exception
