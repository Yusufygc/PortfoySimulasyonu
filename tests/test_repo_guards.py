"""Depo geneli korumalar: otomatik testler canlı ağ çağırmaz, eski widget arayüzü geri gelmez, uygulama QML açar."""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_automated_tests_do_not_call_live_network_helpers_directly():
    allowed_manual = {
        Path("tests/infrastructure/market_data/test_benchmark_fetch_manual.py"),
    }
    live_network_patterns = (
        re.compile(r"\brequests\.(get|post|put|delete)\("),
        re.compile(r"\burllib\.request\.urlopen\("),
    )
    offenders = []

    for path in (ROOT / "tests").rglob("test_*.py"):
        rel_path = path.relative_to(ROOT)
        if rel_path in allowed_manual:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in live_network_patterns:
            if pattern.search(text):
                offenders.append(rel_path.as_posix())
                break

    assert not offenders, f"Automated tests must fake live network calls: {offenders}"


def test_legacy_widget_ui_package_stays_removed():
    assert not (ROOT / "src" / "ui").exists(), "Eski Qt Widgets arayüzü (src/ui) kaldırıldı; arayüz src/ui_qml içindedir."

    offenders = []
    for base in ("src", "tests", "scripts", "config"):
        for path in (ROOT / base).rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                modules = []
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    modules = [node.module]
                if any(module == "src.ui" or module.startswith("src.ui.") for module in modules):
                    offenders.append(path.relative_to(ROOT).as_posix())
                    break

    assert not offenders, f"Kaldırılan src.ui paketine bağımlılık: {offenders}"


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} function not found")


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        parts = [func.attr]
        value = func.value
        while isinstance(value, ast.Attribute):
            parts.append(value.attr)
            value = value.value
        if isinstance(value, ast.Name):
            parts.append(value.id)
        return ".".join(reversed(parts))
    return ""


def test_app_entry_point_starts_qml_after_setting_shared_opengl_attribute():
    tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
    main_func = _function(tree, "main")
    calls = sorted((node.lineno, _call_name(node)) for node in ast.walk(main_func) if isinstance(node, ast.Call))

    configure_line = next(line for line, name in calls if name == "configure_qt_application_attributes")
    run_line = next(line for line, name in calls if name == "run_qml_app")
    assert configure_line < run_line


def test_qt_attribute_helper_enables_shared_opengl_contexts():
    tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
    helper = _function(tree, "configure_qt_application_attributes")

    calls = [
        node
        for node in ast.walk(helper)
        if isinstance(node, ast.Call) and _call_name(node) == "QCoreApplication.setAttribute"
    ]

    assert calls, "Qt application attribute setup call is missing"
    assert any(
        isinstance(call.args[0], ast.Attribute) and call.args[0].attr == "AA_ShareOpenGLContexts"
        for call in calls
        if call.args
    )
