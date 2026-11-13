"""Her modal/pencere QML bileşeni Escape ile kapanır (D-03). 2026-11-08 QA: Hisse Detay penceresinde Escape çalışmıyordu;
pencere açık kaldığı için kenar çubuğundaki ilk tıklama arka plana gidip yalnızca pencereyi kapatıyordu."""
from __future__ import annotations

from pathlib import Path

COMPONENTS = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "qml" / "components"


def test_every_modal_and_dialog_handles_escape():
    missing = [p.name for pattern in ("*Modal*.qml", "*Dialog*.qml") for p in sorted(COMPONENTS.glob(pattern))
               if "Escape" not in p.read_text(encoding="utf-8")]
    assert not missing, f"Escape ile kapanmayan modal/pencere bileşenleri: {missing}"
