"""Katman sınırları: domain ve application dış çerçeveleri/altyapıyı import etmez (bileşim kökü hariç)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_IMPORT = re.compile(r"^\s*(?:from|import)\s+([\w.]+)", re.MULTILINE)

_FORBIDDEN_FOR_APPLICATION = ("src.infrastructure", "src.ui_qml", "src.qt_compat", "PySide6", "duckdb", "sqlite3",
                              "sqlalchemy", "yfinance", "requests")
_FORBIDDEN_FOR_DOMAIN = _FORBIDDEN_FOR_APPLICATION + ("src.application", "pandas")
# Bileşim kökü (composition root): altyapı nesnelerini kurup portlara bağlar
_COMPOSITION_ROOT = ("src/application/container.py", "src/application/container_parts/")


def _offenders(folder: str, forbidden: tuple, allowed: tuple = ()) -> list:
    found = []
    for path in (ROOT / folder).rglob("*.py"):
        relative = path.relative_to(ROOT).as_posix()
        if any(relative.startswith(prefix) for prefix in allowed):
            continue
        for module in _IMPORT.findall(path.read_text(encoding="utf-8")):
            if any(module == name or module.startswith(name + ".") for name in forbidden):
                found.append(f"{relative}: {module}")
    return found


def test_application_does_not_import_infrastructure_or_frameworks():
    assert _offenders("src/application", _FORBIDDEN_FOR_APPLICATION, _COMPOSITION_ROOT) == []


def test_domain_is_pure():
    assert _offenders("src/domain", _FORBIDDEN_FOR_DOMAIN) == []
