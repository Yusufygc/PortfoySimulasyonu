"""Mandal: denetleyicilerde para/yüzde aritmetiği satırı artamaz; hesap uygulama servislerinde yapılır (E4).

Sayılan desenler: `Decimal(...)` ile aritmetik, `* 100` / `/ 100` yüzde dönüşümü. Ekran rakamlarının tek kaynağı
`PositionQueryService` ve `UnifiedPortfolioService`'tir. Bir dosyada sayı düşerse tavan aynı commit'te düşürülür:
`python tests/ui_qml/test_controller_money_math_ratchet.py`.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

CONTROLLERS = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "controllers"
BASELINE = Path(__file__).with_name("controller_money_math_baseline.json")
MONEY_MATH = re.compile(r"Decimal\([^)]*\)\s*[*/+-]|[*/]\s*Decimal\(|\*\s*100(\.0)?\b|/\s*100(\.0)?\b|\)\s*/\s*\w+\s*\*")


def current_counts() -> dict:
    counts = {}
    for path in sorted(CONTROLLERS.glob("*.py")):
        lines = path.read_text(encoding="utf-8").splitlines()
        count = sum(1 for line in lines if MONEY_MATH.search(line) and not line.strip().startswith("#"))
        if count:
            counts[path.name] = count
    return counts


def test_controller_money_math_never_grows():
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    grew = {n: (baseline.get(n, 0), c) for n, c in current_counts().items() if c > baseline.get(n, 0)}
    assert not grew, (
        "Denetleyicide yeni para/yüzde aritmetiği: hesabı bir uygulama servisine (PositionQueryService vb.) taşıyın. "
        f"(dosya: (tavan, şimdi)) {grew}"
    )


def test_baseline_is_tight_so_progress_is_locked_in():
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    current = current_counts()
    loose = {n: (b, current.get(n, 0)) for n, b in baseline.items() if current.get(n, 0) < b}
    assert not loose, f"Sayı düştü; controller_money_math_baseline.json değerini düşürün (dosya: (tavan, şimdi)): {loose}"


if __name__ == "__main__":
    BASELINE.write_text(json.dumps(current_counts(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(sum(current_counts().values()), "satır kaldı")
