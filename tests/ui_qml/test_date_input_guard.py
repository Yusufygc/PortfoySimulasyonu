"""Kullanıcının yazdığı tarih yalnızca `controllers/date_input.py` ile ayrıştırılır; yeni alan kendi ayrıştırıcısını yazamaz.

2026-11-14: tarihi 12 ayrı yer kendi biçim listesiyle okuyordu ve Hisse Detay emir formu YYYY-AA-GG isterken uygulamanın
geri kalanı GG.AA.YYYY kullanıyordu.
"""
from __future__ import annotations

import ast
from pathlib import Path

UI = Path(__file__).resolve().parents[2] / "src" / "ui_qml"
DATE_FORMATS = ("%d.%m.%Y", "%Y-%m-%d")
# Kullanıcı girişi olmayan iç ISO okumaları: kendi ürettiği damga/aralık metni.
INTERNAL_ISO_READERS = {"dashboard_controller.py", "startup_jobs_controller.py", "system_controller.py"}


def _calls(path: Path):
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call):
            yield node


def _call_name(call: ast.Call) -> str:
    return getattr(call.func, "attr", getattr(call.func, "id", ""))


def _date_format_literal(call: ast.Call) -> bool:
    literals = [a.value for a in call.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
    return any(fmt in text for text in literals for fmt in DATE_FORMATS)


def _offence(path: Path, call: ast.Call) -> str:
    name = _call_name(call)
    if name == "strptime" and _date_format_literal(call):
        return f"{path.name}:{call.lineno} strptime"
    if name == "fromisoformat" and path.name not in INTERNAL_ISO_READERS:
        return f"{path.name}:{call.lineno} fromisoformat"
    return ""


def test_no_controller_parses_a_typed_date_on_its_own():
    paths = [p for p in (UI / "controllers").glob("*.py") if p.name != "date_input.py"]
    offenders = [text for path in paths for call in _calls(path) if (text := _offence(path, call))]
    assert not offenders, f"Tarih ayrıştırmak için date_input.parse_date_text kullanın: {offenders}"


def test_qml_never_builds_an_iso_date_by_hand():
    """Alan başlangıç değerleri `Dates.today()` / `Dates.format()` ile üretilir (GG.AA.YYYY)."""
    offenders = []
    for path in (UI / "qml").rglob("*.qml"):
        if path.name == "Dates.qml":
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "getFullYear()" in line and '"-"' in line:
                offenders.append(f"{path.name}:{number}")
            if "YYYY-AA-GG" in line:
                offenders.append(f"{path.name}:{number} etiket")
    assert not offenders, f"Elle ISO tarih üretimi/etiketi: {offenders}"
