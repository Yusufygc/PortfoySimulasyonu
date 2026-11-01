"""Mesaj kataloğu bütünlüğü: tanımsız anahtar yok, kullanılmayan anahtar yok, parametreler yer tutucularla eşleşir."""
from __future__ import annotations

import ast
import string
from pathlib import Path

from src.ui_qml.messages import MESSAGES, msg

UI_DIR = Path(__file__).resolve().parents[2] / "src" / "ui_qml"


def _msg_calls():
    """(dosya, anahtar, parametre adları) — yalnızca sabit anahtarlı çağrılar; dinamik anahtar yasak."""
    calls = []
    for path in UI_DIR.rglob("*.py"):
        if path.name == "messages.py":
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "msg":
                first = node.args[0] if node.args else None
                key = first.value if isinstance(first, ast.Constant) and isinstance(first.value, str) else None
                calls.append((path.name, key, {kw.arg for kw in node.keywords}))
    return calls


def _placeholders(template: str) -> set:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


def test_every_used_key_is_defined_with_constant_key():
    calls = _msg_calls()
    dynamic = [name for name, key, _ in calls if key is None]
    assert not dynamic, f"msg() anahtarı sabit metin olmalı: {dynamic}"
    undefined = sorted({key for _, key, _ in calls if key not in MESSAGES})
    assert not undefined, f"Katalogda olmayan anahtarlar: {undefined}"


def test_every_defined_key_is_used():
    used = {key for _, key, _ in _msg_calls()}
    unused = sorted(set(MESSAGES) - used)
    assert not unused, f"Kullanılmayan anahtarlar (silin): {unused}"


def test_call_parameters_match_template_placeholders():
    wrong = [
        (name, key, sorted(params), sorted(_placeholders(MESSAGES[key])))
        for name, key, params in _msg_calls()
        if key in MESSAGES and params != _placeholders(MESSAGES[key])
    ]
    assert not wrong, f"Parametre/yer tutucu uyuşmazlığı (dosya, anahtar, verilen, beklenen): {wrong}"


def test_msg_formats_parameters():
    MESSAGES["_test.sample"] = "{n} adet"
    try:
        assert msg("_test.sample", n=3) == "3 adet"
    finally:
        del MESSAGES["_test.sample"]
