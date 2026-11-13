"""Her Lightweight Charts örneği Türkçe sayı biçimi kullanır (ondalık virgül); 2026-11-08 QA: Karşılaştırma ekseni '110.00' gösteriyordu."""
from __future__ import annotations

from pathlib import Path

UI = Path(__file__).resolve().parents[2] / "src" / "ui_qml"


def test_every_chart_is_created_with_turkish_locale():
    missing = []
    for path in list((UI / "controllers").glob("*.py")) + list((UI / "assets" / "templates").glob("*.html")):
        text = path.read_text(encoding="utf-8")
        if "createChart(" in text and not ("locale: 'tr-TR'" in text and ("priceFormatter" in text or "formatter:" in text)):
            missing.append(path.name)
    assert not missing, f"createChart çağıran ama locale: 'tr-TR' ve priceFormatter (ondalık virgül) vermeyen dosyalar: {missing}"
