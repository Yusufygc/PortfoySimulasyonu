"""
Stock 360 Fallback Data — Dış veri servisleri kapalı veya veri eksik olduğunda
kullanıcı deneyimini kesintisiz kılan varsayılan ve sentetik veri üreticileri.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict

from src.ui_qml.controllers.stock_360_formatters import DONUT_COLORS


def guess_sector(ticker: str) -> str:
    """Hisse sembolüne göre sektör eşleştirmesi yapar."""
    sec_map = {
        "THYAO": "Ulaştırma & Havacılık",
        "PGSUS": "Ulaştırma & Havacılık",
        "BIMAS": "Perakende Ticaret",
        "MGROS": "Perakende Ticaret",
        "ASELS": "Savunma & Teknoloji",
        "KCHOL": "Holding & Yatırım",
        "SAHOL": "Holding & Yatırım",
        "AKBNK": "Bankacılık",
        "GARAN": "Bankacılık",
        "ISCTR": "Bankacılık",
        "YKBNK": "Bankacılık",
        "SISE": "Cam & Sanayi",
        "EREGL": "Demir & Çelik",
        "TUPRS": "Petrol & Rafineri",
        "ADEL": "Kırtasiye & İmalat",
        "FROTO": "Otomotiv",
        "TOASO": "Otomotiv",
    }
    return sec_map.get(ticker, "Borsa İstanbul Sanayi & Hizmet")


def get_default_overview(ticker: str) -> Dict[str, Any]:
    """Varsayılan genel bakış verilerini döner."""
    return {
        "last_price_str": "₺394.00",
        "last_price_raw": 394.00,
        "last_price_date_str": date.today().strftime("%d.%m.%Y"),
        "daily_change_str": "+1.85%",
        "daily_change_raw": 1.85,
        "is_daily_positive": True,
        "volume_str": "12.4M",
        "week52_low_str": "₺240.00",
        "week52_high_str": "₺415.00",
        "week52_range_pct": 0.88,
    }


def get_default_technical() -> Dict[str, Any]:
    """Varsayılan teknik indikatör seviyelerini döner."""
    return {
        "rsi14_str": "58.4",
        "rsi_status": "Dengeli",
        "macd_line_str": "1.25",
        "macd_signal_str": "0.80",
        "sma50_str": "₺378.50",
        "sma200_str": "₺315.00",
        "ema20_str": "₺382.00",
        "support_str": "₺385.00",
        "resistance_str": "₺420.00",
        "trend_status": "Boğa / Golden Cross",
    }


_FALLBACK_PERIODS = ["2025/3", "2025/6", "2025/9", "2025/12", "2026/3", "2026/6"]


def _flat_series(value: float) -> Dict[str, float]:
    """Her örnek dönem için aynı değeri taşıyan `{dönem: değer}` serisi (her çağrıda yeni sözlük)."""
    return dict.fromkeys(_FALLBACK_PERIODS, value)


def _fallback_ratios() -> Dict[str, str]:
    return {
        "pe_ratio": "13.4",
        "pb_ratio": "2.46",
        "ev_ebitda": "7.6",
        "div_yield": "%2.40",
        "roe": "%28.5",
        "net_debt_ebitda": "0.80",
        "piotroski_score": "7/9",
        "current_ratio": "1.42",
        "market_cap_str": "₺499.51 Mr",
    }


def _fallback_quarterly_series() -> Dict[str, Dict[str, int]]:
    """Çeyreklik değişen satış, brüt kâr, FAVÖK ve net kâr serileri."""
    return {
        "satis_ceyrek": {
            "2025/3": 180_000_000_000, "2025/6": 195_000_000_000, "2025/9": 210_000_000_000,
            "2025/12": 240_000_000_000, "2026/3": 212_862_000_000, "2026/6": 236_832_000_000,
        },
        "brut_kar": {
            "2025/3": 36_000_000_000, "2025/6": 39_000_000_000, "2025/9": 42_000_000_000,
            "2025/12": 48_000_000_000, "2026/3": 44_000_000_000, "2026/6": 49_500_000_000,
        },
        "favok_ceyrek": {
            "2025/3": 14_000_000_000, "2025/6": 16_000_000_000, "2025/9": 17_500_000_000,
            "2025/12": 20_000_000_000, "2026/3": 18_200_000_000, "2026/6": 21_100_000_000,
        },
        "net_kar_ceyrek": {
            "2025/3": 5_200_000_000, "2025/6": 6_100_000_000, "2025/9": 7_400_000_000,
            "2025/12": 9_800_000_000, "2026/3": 6_551_000_000, "2026/6": 8_543_000_000,
        },
    }


def _fallback_flat_metrics() -> Dict[str, Dict[str, float]]:
    """Tüm dönemlerde sabit örnek değerli nakit akışı, borç ve DuPont serileri."""
    return {
        "isletme_cf": _flat_series(12_000_000_000),
        "capex": _flat_series(4_500_000_000),
        "fcf": _flat_series(7_500_000_000),
        "net_borc": _flat_series(18_000_000_000),
        "net_borc_favok_ttm": _flat_series(0.85),
        "dupont_net_margin": _flat_series(4.2),
        "dupont_asset_turnover": _flat_series(2.1),
        "dupont_leverage": _flat_series(3.2),
        "dupont_roe": _flat_series(28.5),
    }


def _fallback_raw_sections() -> Dict[str, Dict[str, Dict[str, int]]]:
    balance = {
        "DÖNEN VARLIKLAR": 98_000_000_000,
        "Nakit ve Nakit Benzerleri": 24_000_000_000,
        "Ticari Alacaklar": 18_500_000_000,
        "Stoklar": 42_000_000_000,
        "DURAN VARLIKLAR": 110_000_000_000,
        "Maddi Duran Varlıklar": 72_000_000_000,
        "TOPLAM VARLIKLAR": 208_000_000_000,
        "KISA VADELİ YÜKÜMLÜLÜKLER": 82_000_000_000,
        "UZUN VADELİ YÜKÜMLÜLÜKLER": 34_000_000_000,
        "ÖZKAYNAKLAR": 92_000_000_000,
        "TOPLAM KAYNAKLAR": 208_000_000_000,
    }
    income = {
        "Satış Gelirleri": 236_832_000_000,
        "Satışların Maliyeti (-)": -187_332_000_000,
        "BRÜT KÂR": 49_500_000_000,
        "Genel Yönetim Giderleri (-)": -18_400_000_000,
        "FAVÖK": 21_100_000_000,
        "DÖNEM KARI": 8_543_000_000,
    }
    cash_flow = {
        "İŞLETME FAALİYETLERİNDEN NAKİT AKIŞLARI": 12_000_000_000,
        "YATIRIM FAALİYETLERİNDEN NAKİT AKIŞLARI": -4_500_000_000,
        "FİNANSMAN FAALİYETLERİNDEN NAKİT AKIŞLARI": -3_200_000_000,
        "Serbest Nakit Akımı (FCF)": 7_500_000_000,
    }
    return {
        section: {name: _flat_series(value) for name, value in items.items()}
        for section, items in (("bilanco", balance), ("gelir", income), ("nakit_akim", cash_flow))
    }


def get_fallback_financials(ticker: str) -> Dict[str, Any]:
    """Dış finansal bilanço servisi çevrimdışı olduğunda kullanılacak veri kümesi."""
    return {
        "ratios": _fallback_ratios(),
        "raw_data": {
            "periods": list(reversed(_FALLBACK_PERIODS)),
            **_fallback_quarterly_series(),
            **_fallback_flat_metrics(),
            "piotroski_f_score": 7,
            "_raw_sections": _fallback_raw_sections(),
        },
    }


def get_fallback_shareholders(ticker: str) -> Dict[str, Any]:
    """KAP veri sağlayıcısı çevrimdışı olduğunda kullanılacak ortaklık yapısı verileri."""
    return {
        "date_str": date.today().strftime("%d.%m.%Y"),
        "free_float_ratio_str": "%43.11",
        "free_float_pct": 0.4311,
        "paid_capital_str": "₺259.86 Mn",
        "shareholders_list": [
            {
                "name": "KURUCU ORTAK / HOLDİNG",
                "ratio": 56.89,
                "ratioStr": "%56.89",
                "share": "₺147.83 Mn",
                "votingRatio": "%56.89",
                "color": DONUT_COLORS[0],
                "isFreeFloat": False,
            },
            {
                "name": "DİĞER (HALKA AÇIK)",
                "ratio": 43.11,
                "ratioStr": "%43.11",
                "share": "₺112.03 Mn",
                "votingRatio": "%43.11",
                "color": DONUT_COLORS[-1],
                "isFreeFloat": True,
            },
        ],
        "shareholder_slices": [
            {"label": "KURUCU ORTAK / HOLDİNG", "pct": 0.5689, "color": DONUT_COLORS[0], "amount": "₺147.83 Mn"},
            {"label": "DİĞER (HALKA AÇIK)", "pct": 0.4311, "color": DONUT_COLORS[-1], "amount": "₺112.03 Mn"},
        ],
        "shareholder_timeline": [
            {
                "date": "15.01.2026",
                "name": "KURUCU ORTAK / HOLDİNG",
                "newRatio": "%56.89",
                "oldRatio": "%56.40",
                "diff": 0.49,
                "diffStr": "+0.49%",
                "isIncrease": True,
                "votingRatio": "%56.89",
            },
            {
                "date": "12.11.2025",
                "name": "DİĞER (HALKA AÇIK)",
                "newRatio": "%43.11",
                "oldRatio": "%43.60",
                "diff": -0.49,
                "diffStr": "-0.49%",
                "isIncrease": False,
                "votingRatio": "%43.11",
            },
        ],
    }
