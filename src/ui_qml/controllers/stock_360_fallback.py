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


def get_fallback_financials(ticker: str) -> Dict[str, Any]:
    """Dış finansal bilanço servisi çevrimdışı olduğunda kullanılacak veri kümesi."""
    periods = ["2025/3", "2025/6", "2025/9", "2025/12", "2026/3", "2026/6"]
    return {
        "ratios": {
            "pe_ratio": "13.4",
            "pb_ratio": "2.46",
            "ev_ebitda": "7.6",
            "div_yield": "%2.40",
            "roe": "%28.5",
            "net_debt_ebitda": "0.80",
            "piotroski_score": "7/9",
            "current_ratio": "1.42",
            "market_cap_str": "₺499.51 Mr",
        },
        "raw_data": {
            "periods": list(reversed(periods)),
            "satis_ceyrek": {
                "2025/3": 180_000_000_000,
                "2025/6": 195_000_000_000,
                "2025/9": 210_000_000_000,
                "2025/12": 240_000_000_000,
                "2026/3": 212_862_000_000,
                "2026/6": 236_832_000_000,
            },
            "brut_kar": {
                "2025/3": 36_000_000_000,
                "2025/6": 39_000_000_000,
                "2025/9": 42_000_000_000,
                "2025/12": 48_000_000_000,
                "2026/3": 44_000_000_000,
                "2026/6": 49_500_000_000,
            },
            "favok_ceyrek": {
                "2025/3": 14_000_000_000,
                "2025/6": 16_000_000_000,
                "2025/9": 17_500_000_000,
                "2025/12": 20_000_000_000,
                "2026/3": 18_200_000_000,
                "2026/6": 21_100_000_000,
            },
            "net_kar_ceyrek": {
                "2025/3": 5_200_000_000,
                "2025/6": 6_100_000_000,
                "2025/9": 7_400_000_000,
                "2025/12": 9_800_000_000,
                "2026/3": 6_551_000_000,
                "2026/6": 8_543_000_000,
            },
            "isletme_cf": {p: 12_000_000_000 for p in periods},
            "capex": {p: 4_500_000_000 for p in periods},
            "fcf": {p: 7_500_000_000 for p in periods},
            "net_borc": {p: 18_000_000_000 for p in periods},
            "net_borc_favok_ttm": {p: 0.85 for p in periods},
            "dupont_net_margin": {p: 4.2 for p in periods},
            "dupont_asset_turnover": {p: 2.1 for p in periods},
            "dupont_leverage": {p: 3.2 for p in periods},
            "dupont_roe": {p: 28.5 for p in periods},
            "piotroski_f_score": 7,
            "_raw_sections": {
                "bilanco": {
                    "DÖNEN VARLIKLAR": {p: 98_000_000_000 for p in periods},
                    "Nakit ve Nakit Benzerleri": {p: 24_000_000_000 for p in periods},
                    "Ticari Alacaklar": {p: 18_500_000_000 for p in periods},
                    "Stoklar": {p: 42_000_000_000 for p in periods},
                    "DURAN VARLIKLAR": {p: 110_000_000_000 for p in periods},
                    "Maddi Duran Varlıklar": {p: 72_000_000_000 for p in periods},
                    "TOPLAM VARLIKLAR": {p: 208_000_000_000 for p in periods},
                    "KISA VADELİ YÜKÜMLÜLÜKLER": {p: 82_000_000_000 for p in periods},
                    "UZUN VADELİ YÜKÜMLÜLÜKLER": {p: 34_000_000_000 for p in periods},
                    "ÖZKAYNAKLAR": {p: 92_000_000_000 for p in periods},
                    "TOPLAM KAYNAKLAR": {p: 208_000_000_000 for p in periods},
                },
                "gelir": {
                    "Satış Gelirleri": {p: 236_832_000_000 for p in periods},
                    "Satışların Maliyeti (-)": {p: -187_332_000_000 for p in periods},
                    "BRÜT KÂR": {p: 49_500_000_000 for p in periods},
                    "Genel Yönetim Giderleri (-)": {p: -18_400_000_000 for p in periods},
                    "FAVÖK": {p: 21_100_000_000 for p in periods},
                    "DÖNEM KARI": {p: 8_543_000_000 for p in periods},
                },
                "nakit_akim": {
                    "İŞLETME FAALİYETLERİNDEN NAKİT AKIŞLARI": {p: 12_000_000_000 for p in periods},
                    "YATIRIM FAALİYETLERİNDEN NAKİT AKIŞLARI": {p: -4_500_000_000 for p in periods},
                    "FİNANSMAN FAALİYETLERİNDEN NAKİT AKIŞLARI": {p: -3_200_000_000 for p in periods},
                    "Serbest Nakit Akımı (FCF)": {p: 7_500_000_000 for p in periods},
                },
            },
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
