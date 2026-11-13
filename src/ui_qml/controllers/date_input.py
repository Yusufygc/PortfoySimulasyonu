"""Kullanıcının yazdığı tarih metni: tek ayrıştırıcı ve tek görünen biçim (GG.AA.YYYY).

Denetleyiciler tarihi kendi biçim listesiyle ayrıştırmaz; `parse_date_text` kullanır (`tests/ui_qml/test_date_input_guard.py`
yenisini yazmayı engeller). QML eşi `qml/theme/Dates.qml`'dir (alan başlangıç değerleri). Eski `YYYY-AA-GG` girişi yapıştırma
ve betik uyumu için sessizce kabul edilir ama arayüz hiçbir yerde o biçimi göstermez.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

DATE_HINT = "GG.AA.YYYY"
_ACCEPTED_FORMATS = ("%d.%m.%Y", "%Y-%m-%d")


def parse_date_text(text: Optional[str]) -> Optional[date]:
    """'14.11.2026' veya eski '2026-11-14' -> date; boş veya geçersiz metin için None."""
    raw = (text or "").strip()
    if not raw:
        return None
    for fmt in _ACCEPTED_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def format_date_text(day: date) -> str:
    """date -> 'GG.AA.YYYY' (denetleyiciden QML'e giden tarihler)."""
    return day.strftime("%d.%m.%Y")
