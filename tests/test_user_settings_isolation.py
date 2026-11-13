"""Kullanıcı ayarları tek fabrikadan açılır; testler ve QA gerçek Windows kayıt defterine yazmaz.

2026-11-08 QA: `QSettings("PortfoySimulasyonu", "PortfoySimulasyonu")` her zaman kayıt defterine gider
(`setDefaultFormat` yalnızca argümansız kurucuyu etkiler). e2e koşuları gerçek sohbet geçmişine ve açılış işi
damgalarına yazıyordu.
"""
from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
FACTORY = "src/qt_compat/user_settings.py"


def test_no_direct_application_qsettings_outside_the_factory():
    offenders = []
    for path in SRC.rglob("*.py"):
        rel = path.relative_to(SRC.parent).as_posix()
        if rel == FACTORY:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "QSettings"
                    and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)
                    and not str(node.args[0].value).endswith(".ini")):
                offenders.append(f"{rel}:{node.lineno}")
    assert not offenders, f"QSettings(org, app) kayıt defterine yazar; user_settings() kullanın: {offenders}"


def test_tests_never_use_the_registry():
    from src.qt_compat.user_settings import user_settings

    settings = user_settings()
    assert "HKEY" not in settings.fileName(), f"Test ayarı kayıt defterine gidiyor: {settings.fileName()}"


def test_override_returns_ini_backed_settings(tmp_path):
    from src.qt_compat.user_settings import use_ini_file, user_settings

    ini = tmp_path / "x.ini"
    previous = use_ini_file(str(ini))
    try:
        settings = user_settings()
        settings.setValue("a/b", 1)
        settings.sync()
        assert Path(settings.fileName()) == ini and ini.exists()
    finally:
        use_ini_file(previous)
