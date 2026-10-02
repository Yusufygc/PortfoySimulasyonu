"""QML denetleyicileri katman kurallarına uyar: UI -> Application (repository ve altyapıya doğrudan erişim yok)."""
from __future__ import annotations

import ast
import re
from pathlib import Path

UI_QML_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml"
FORBIDDEN_IMPORT_PREFIXES = ("src.ui.", "src.infrastructure", "sqlite3", "duckdb", "sqlalchemy")
REPO_ACCESS = re.compile(r"[a-z_]+_repo\b|_repository\b|\.repositories\b|conn_provider")


def _python_files():
    return sorted(path for path in UI_QML_DIR.rglob("*.py") if "__pycache__" not in path.parts)


def _imported_modules(path: Path):
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def test_ui_qml_does_not_import_legacy_ui_or_infrastructure():
    violations = [
        f"{path.relative_to(UI_QML_DIR)}: {module}"
        for path in _python_files()
        for module in _imported_modules(path)
        if module == "src.ui" or module.startswith(FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == [], "UI katmanı yalnızca application/domain'e bağlanabilir:\n" + "\n".join(violations)


def test_ui_qml_controllers_do_not_touch_repositories_directly():
    violations = []
    for path in _python_files():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            code = line.split("#", 1)[0]
            if REPO_ACCESS.search(code):
                violations.append(f"{path.relative_to(UI_QML_DIR)}:{number}: {line.strip()}")

    assert violations == [], "Repository erişimi servis katmanından geçmeli (StockLookupService vb.):\n" + "\n".join(violations)
