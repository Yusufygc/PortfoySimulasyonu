"""Kullanıcının yazdığı tarih ve saat metni: tek ayrıştırıcı ve tek görünen biçim (GG.AA.YYYY, SS:DD).

Denetleyiciler tarihi kendi biçim listesiyle ayrıştırmaz; `parse_date_text` kullanır (`tests/ui_qml/test_date_input_guard.py`
yenisini yazmayı engeller). QML eşi `qml/theme/Dates.qml`'dir (alan başlangıç değerleri). Eski `YYYY-AA-GG` girişi yapıştırma
ve betik uyumu için sessizce kabul edilir ama arayüz hiçbir yerde o biçimi göstermez.
"""
from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional

DATE_HINT = "GG.AA.YYYY"
TIME_HINT = "SS:DD"
_ACCEPTED_FORMATS = ("%d.%m.%Y", "%Y-%m-%d")
_ACCEPTED_TIME_FORMATS = ("%H:%M", "%H:%M:%S")


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


def parse_time_text(text: Optional[str]) -> Optional[time]:
    """'14:30' veya '14:30:15' -> time; boş veya geçersiz metin için None."""
    raw = (text or "").strip()
    if not raw:
        return None
    for fmt in _ACCEPTED_TIME_FORMATS:
        try:
            return datetime.strptime(raw, fmt).time()
        except ValueError:
            continue
    return None


def format_time_text(moment: time) -> str:
    """time -> 'SS:DD' (saniye gösterilmez)."""
    return moment.strftime("%H:%M")
