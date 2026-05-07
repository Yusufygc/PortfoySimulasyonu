"""
BIST (Borsa İstanbul) resmi tatil takvimi — 2020-2030.

Sabit milli tatiller her yıl aynı tarihte, dini bayramlar Hicri takvime
göre her yıl ~11 gün öne kayar. Arife günleri dahil edilmez (BIST o
günlerde saat 12:30'a kadar açık olup fiyat verisi mevcuttur).

Kaynaklar: BIST resmi tatil duyuruları, Diyanet İşleri Başkanlığı.
"""

from __future__ import annotations

from datetime import date
from typing import Set


# ─── Sabit Milli Tatiller ────────────────────────────────────────────────────
# (ay, gün) — yıl bağımsız; hafta sonuna denk gelenler otomatik atlanır
_FIXED = [
    (1,  1),   # Yılbaşı
    (4, 23),   # Ulusal Egemenlik ve Çocuk Bayramı
    (5,  1),   # Emek ve Dayanışma Günü
    (5, 19),   # Atatürk'ü Anma, Gençlik ve Spor Bayramı
    (7, 15),   # Demokrasi ve Milli Birlik Günü
    (8, 30),   # Zafer Bayramı
    (10, 29),  # Cumhuriyet Bayramı
]

# ─── Ramazan Bayramı (Eid al-Fitr) ───────────────────────────────────────────
# Sadece BIST'in tam kapandığı iş günleri; Arife yok.
_RAMAZAN = [
    # 2020 — Bayram 1-2: Pzt-Sal (1. gün Pazar, BIST kapalı değil)
    (2020, 5, 25), (2020, 5, 26),
    # 2021 — Bayram 1-2: Per-Cum (3. gün Cmt)
    (2021, 5, 13), (2021, 5, 14),
    # 2022 — Bayram 1-2-3: Pzt-Sal-Çar
    (2022, 5,  2), (2022, 5,  3), (2022, 5,  4),
    # 2023 — Bayram 1: Cum (2-3. gün Cmt-Paz)
    (2023, 4, 21),
    # 2024 — Bayram 1-2-3: Çar-Per-Cum
    (2024, 4, 10), (2024, 4, 11), (2024, 4, 12),
    # 2025 — Bayram 1-2: Pzt-Sal (1. gün Paz)
    (2025, 3, 31), (2025, 4,  1),
    # 2026 — Bayram 1: Cum (2-3. gün Cmt-Paz); 19 Mart Arife (yarım gün)
    (2026, 3, 20),
    # 2027 — Bayram 1-2: Sal-Çar (3. gün Per)
    (2027, 3,  9), (2027, 3, 10),
    # 2028 — Bayram 1-2-3: Paz-Pzt-Sal → Pzt-Sal iş günü
    (2028, 2, 28), (2028, 2, 29),
    # 2029 — Bayram 1-2: Per-Cum (3. gün Cmt)
    (2029, 2, 14), (2029, 2, 15),
    # 2030 — Bayram 1-2-3: Sal-Çar-Per
    (2030, 2,  4), (2030, 2,  5), (2030, 2,  6),
]

# ─── Kurban Bayramı (Eid al-Adha) ────────────────────────────────────────────
# Resmi olarak 4.5 günlük tatil; yalnızca tam kapanış olan iş günleri.
_KURBAN = [
    # 2020 — Cum-Pzt-Sal-Çar (Arife Per)
    (2020, 7, 31), (2020, 8,  1), (2020, 8,  2), (2020, 8,  3),
    # 2021 — Sal-Çar-Per-Cum (Arife Pzt)
    (2021, 7, 20), (2021, 7, 21), (2021, 7, 22), (2021, 7, 23),
    # 2022 — Bayram 1-4: 9-12 Temmuz; 9=Cmt, 10=Paz hafta sonu → Pzt-Sal iş günü
    (2022, 7, 11), (2022, 7, 12),
    # 2023 — Çar-Per-Cum-Cmt → Çar-Per-Cum iş günü
    (2023, 6, 28), (2023, 6, 29), (2023, 6, 30),
    # 2024 — Pzt-Sal-Çar-Per (Arife Paz)
    (2024, 6, 17), (2024, 6, 18), (2024, 6, 19), (2024, 6, 20),
    # 2025 — Cum-Cmt-Paz-Pzt → Cum-Pzt iş günü
    (2025, 6,  6), (2025, 6,  9),
    # 2026 — Çar-Per-Cum-Cmt → Çar-Per-Cum iş günü (Arife Sal)
    (2026, 5, 27), (2026, 5, 28), (2026, 5, 29),
    # 2027 — Pzt-Sal-Çar-Per (Arife Paz)
    (2027, 5, 17), (2027, 5, 18), (2027, 5, 19), (2027, 5, 20),
    # 2028 — Cum-Cmt-Paz-Pzt → Cum-Pzt iş günü
    (2028, 5,  5), (2028, 5,  8),
    # 2029 — Çar-Per-Cum-Cmt → Çar-Per-Cum iş günü
    (2029, 4, 24), (2029, 4, 25), (2029, 4, 26),
    # 2030 — Pzt-Sal-Çar-Per
    (2030, 4, 14), (2030, 4, 15), (2030, 4, 16), (2030, 4, 17),
]

# Önceden hesaplanmış set — sorgularda O(1)
_VARIABLE_SET: Set[tuple] = {
    (y, m, d) for y, m, d in _RAMAZAN + _KURBAN
}

_FIXED_MONTHDAY: Set[tuple] = set(_FIXED)


def get_bist_holidays(start_date: date, end_date: date) -> Set[date]:
    """Verilen aralıktaki BIST resmi tatil günlerini döner (sadece hafta içi)."""
    holidays: Set[date] = set()

    for year in range(start_date.year, end_date.year + 1):
        for month, day in _FIXED:
            try:
                d = date(year, month, day)
            except ValueError:
                continue
            if d.weekday() < 5 and start_date <= d <= end_date:
                holidays.add(d)

    for year, month, day in _RAMAZAN + _KURBAN:
        d = date(year, month, day)
        if d.weekday() < 5 and start_date <= d <= end_date:
            holidays.add(d)

    return holidays


def is_bist_trading_day(d: date) -> bool:
    """Tarihin BIST işlem günü olup olmadığını döner."""
    if d.weekday() >= 5:
        return False
    if (d.month, d.day) in _FIXED_MONTHDAY:
        return False
    if (d.year, d.month, d.day) in _VARIABLE_SET:
        return False
    return True
