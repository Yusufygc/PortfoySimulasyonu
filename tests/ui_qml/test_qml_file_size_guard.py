"""QML dosyaları tek parça devleşmesin: büyük görünümler bileşenlere bölünür (docs/wiki/code_quality_guardrails.md)."""
from __future__ import annotations

from pathlib import Path

QML_DIR = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "qml"
MAX_QML_LINES = 900
EXEMPT = {"theme/Strings.qml"}  # metin kataloğu: tek tek tanımlardan oluşur


def test_no_qml_file_exceeds_the_line_ceiling():
    oversized = []
    for path in QML_DIR.rglob("*.qml"):
        relative = path.relative_to(QML_DIR).as_posix()
        if relative in EXEMPT:
            continue
        lines = len(path.read_text(encoding="utf-8").splitlines())
        if lines > MAX_QML_LINES:
            oversized.append(f"{relative}: {lines} satır")

    assert not oversized, f"{MAX_QML_LINES} satırı aşan QML dosyaları bileşenlere bölünmeli: {oversized}"
