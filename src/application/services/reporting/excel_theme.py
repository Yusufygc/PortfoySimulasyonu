"""Excel raporu için kurumsal renk paleti.

Tüm rapor (sekmeler + grafikler) bu modülden renk alır. Hardcoded hex değer
yerine bu sabitleri import edin; tek bir noktadan tema güncellenir.

Palet: klasik aracı kurum estetiği — deep navy + gold aksan + slate nötrler.
"""
from __future__ import annotations

from typing import Final

# ────── Palet ───────────────────────────────────────────────────────────────
NAVY_PRIMARY:   Final[str] = "0D2B6E"   # ana başlık, header fill
NAVY_DEEP:      Final[str] = "1565C0"   # ana grafik çizgisi — canlı koyu mavi
GOLD_ACCENT:    Final[str] = "F9A825"   # toplam getiri — amber/gold
SLATE:          Final[str] = "455A64"   # ikincil çizgi, axis text
POSITIVE:       Final[str] = "00897B"   # gain — canlı teal-green
NEGATIVE:       Final[str] = "E53935"   # loss — canlı kırmızı
NEUTRAL_BG:     Final[str] = "F4F6FA"   # plot area arka plan
NEUTRAL_LINE:   Final[str] = "CFD8DC"   # gridline, border
GRID_LIGHT:     Final[str] = "ECEFF1"   # minor gridline
TEXT_DARK:      Final[str] = "1A1F2C"   # gövde metin
TEXT_MUTED:     Final[str] = "607D8B"   # dipnot
ZEBRA:          Final[str] = "F9FAFB"   # tablo zebra
WHITE:          Final[str] = "FFFFFF"

POSITIVE_FILL:  Final[str] = "C8E6C9"   # hücre içi pozitif vurgu
POSITIVE_FONT:  Final[str] = "1B5E20"
NEGATIVE_FILL:  Final[str] = "FFCDD2"   # hücre içi negatif vurgu
NEGATIVE_FONT:  Final[str] = "B71C1C"
SUMMARY_FILL:   Final[str] = "E7E6E6"   # TOPLAM satırı fill
SECTION_FILL:   Final[str] = "BBDEFB"   # section title — açık mavi

DOUGHNUT_PALETTE: Final[tuple[str, ...]] = (
    "1565C0", "F9A825", "00897B", "E53935",
    "7B1FA2", "F4511E", "0097A7", "558B2F",
    "AD1457", "1976D2",
)
