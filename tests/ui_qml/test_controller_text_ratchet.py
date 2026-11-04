"""Mandal: denetleyicilerdeki Türkçe kullanıcı metni literali sayısı artamaz, hedef 0.

Kullanıcıya görünen metin `src/ui_qml/messages.py` kataloğundadır (QML'in kendi metni `Strings.qml`'de). Sayım: log çağrıları
ve docstring hariç (satır sonunda ya da hemen üstünde `# metin-muaf: neden` yorumu olanlar da hariç), Türkçe harf içeren her metin sabiti. Bir dosyada sayı düşerse `controller_text_baseline.json` aynı
commit'te düşürülür (test bunu zorlar); yeni dosyanın tavanı 0'dır.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

CONTROLLERS = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "controllers"
BASELINE = Path(__file__).with_name("controller_text_baseline.json")
TURKISH_LETTER = re.compile(r"[çğıöşüÇĞİÖŞÜ]")
EXEMPT_MARK = "metin-muaf"  # kullanıcıya gösterilmeyen veri/anahtar sabitleri satır sonu yorumuyla muaf tutulur
LOG_METHODS = {"debug", "info", "warning", "error", "exception", "critical", "log"}


def _skipped_nodes(tree: ast.AST) -> set:
    skipped = set()
    for node in ast.walk(tree):
        is_scope = isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        if is_scope and node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
            skipped.add(id(node.body[0].value))  # docstring
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in LOG_METHODS:
            skipped.update(id(sub) for sub in ast.walk(node))  # log mesajı kullanıcıya gösterilmez
    return skipped


def _is_exempt(lines: list, lineno: int) -> bool:
    """Sabitin satırında ya da hemen üstündeki yorum satırında muaf işareti var mı (çok satırlı şablonlar için)."""
    here = lines[lineno - 1]
    above = lines[lineno - 2].strip() if lineno > 1 else ""
    return EXEMPT_MARK in here or (above.startswith("#") and EXEMPT_MARK in above)


def _fstring_start_lines(tree: ast.AST) -> dict:
    """f-string içindeki sabit parçaların satırı, f-string'in ilk satırı sayılır.

    Python 3.12 parçalara kendi konumunu verir (çok satırlı f-string'in ortasındaki satır); 3.11 ve öncesi tüm
    parçalara f-string'in başlangıç satırını verir. Muaf işareti her sürümde aynı satırda aranır.
    """
    starts: dict = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            for sub in ast.walk(node):
                starts.setdefault(id(sub), node.lineno)
    return starts


def count_turkish_literals(path: Path) -> int:
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    tree = ast.parse(source)
    skipped = _skipped_nodes(tree)
    fstring_start = _fstring_start_lines(tree)
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        and id(node) not in skipped and TURKISH_LETTER.search(node.value)
        and not _is_exempt(lines, fstring_start.get(id(node), node.lineno))
    )


def current_counts() -> dict:
    counts = {path.name: count_turkish_literals(path) for path in sorted(CONTROLLERS.glob("*.py"))}
    return {name: count for name, count in counts.items() if count}


def test_controller_user_text_never_grows():
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    current = current_counts()
    grew = {n: (baseline.get(n, 0), c) for n, c in current.items() if c > baseline.get(n, 0)}
    assert not grew, (
        "Denetleyicide yeni Türkçe metin literali: metni src/ui_qml/messages.py kataloğuna taşıyıp msg() çağırın. "
        f"(dosya: (tavan, şimdi)) {grew}"
    )


def test_baseline_is_tight_so_progress_is_locked_in():
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    current = current_counts()
    loose = {n: (b, current.get(n, 0)) for n, b in baseline.items() if current.get(n, 0) < b}
    assert not loose, (
        f"Metin sayısı düştü; tests/ui_qml/controller_text_baseline.json değerini düşürün (dosya: (tavan, şimdi)): {loose}"
    )


if __name__ == "__main__":  # tavanı güncel sayıya indirir: python tests/ui_qml/test_controller_text_ratchet.py
    BASELINE.write_text(json.dumps(current_counts(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(sum(current_counts().values()), "literal kaldı")
