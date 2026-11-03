"""Haber konu süzgeci: ekonomi, finans, yatırım, borsa, siyaset ve diplomasi kalır; magazin ve benzeri elenir.

Saf fonksiyonlar (ağ ve veritabanı yok). Eşleşme başlık + özet üzerinde, Türkçe harf farkları katlanarak yapılır.
Terim sonunda `$` varsa tam kelime, yoksa kelime başı (önek) eşleşir: `borsa` -> "borsası", `fed$` -> "Fed" ama "federal" değil.
"""
from __future__ import annotations

import re
from typing import Iterable

from src.domain.models.news_item import NewsItem

_FOLD = str.maketrans({"İ": "i", "I": "i", "ı": "i"})

# Konu terimleri (ekonomi, finans, yatırım, borsa, siyaset, diplomasi). Türkçe ve İngilizce.
_TOPIC_TERMS = (
    # ekonomi, para ve piyasa
    "ekonomi", "ekonomik", "finans", "yatırım", "yatirim", "piyasa", "borsa", "bist", "endeks", "hisse", "pay senedi",
    "dolar", "euro$", "sterlin", "döviz", "kur$", "kurlar$", "altın", "gümüş", "platin", "paladyum", "petrol", "brent",
    "doğal gaz", "emtia", "kripto", "bitcoin", "ethereum", "faiz", "enflasyon", "merkez bankası", "tcmb", "fed$", "ecb$",
    "para politikası", "tahvil", "bono$", "eurobond", "cds$", "risk primi", "büyüme", "gsyh", "işsizlik", "istihdam",
    "ihracat", "ithalat", "cari açık", "bütçe", "vergi", "maliye", "hazine", "banka", "kredi", "bilanço", "kâr", "kar$",
    "temettü", "halka arz", "sermaye", "ihale", "sözleşme", "satın alma", "birleşme", "kap$", "spk$", "sanayi", "üretim",
    "ticaret", "gümrük", "tarife", "tüik", "rekabet", "asgari ücret", "emekli", "zam$", "fiyat", "otomotiv", "enerji", "turizm",
    "stock", "share$", "shares$", "market", "wall street", "nasdaq", "dow jones", "s&p", "index", "dollar", "oil$",
    "crude", "gold$", "silver$", "crypto", "central bank", "interest rate", "rate cut", "rate hike", "inflation",
    "economy", "economic", "gdp$", "jobs report", "unemployment", "trade", "tariff", "bank", "earnings", "profit",
    "revenue", "ipo$", "merger", "acquisition", "invest", "bond", "yield", "treasury", "budget", "tax", "finance",
    "financial", "business", "company", "companies", "currency", "recession", "supply chain", "commodit",
    # siyaset
    "cumhurbaşkan", "başbakan", "bakan", "meclis", "tbmm", "hükümet", "seçim", "siyaset", "anayasa", "kabine",
    "milletvekili", "genel başkan", "parti", "kanun", "yasa teklifi", "president", "prime minister", "minister",
    "election", "parliament", "congress", "senate", "government", "white house", "kremlin", "policy",
    # diplomasi ve jeopolitik
    "diplomasi", "diplomat", "büyükelçi", "dışişleri", "zirve", "nato$", "birleşmiş milletler", "avrupa birliği",
    "anlaşma", "ateşkes", "yaptırım", "müzakere", "görüşme", "ziyaret", "bae$", "abd$", "çin$", "rusya", "ukrayna", "israil", "gazze",
    "iran$", "suriye", "treaty", "ceasefire", "sanction", "summit", "talks$", "diplomac", "war$", "wars$", "nato$",
    "china$", "russia", "ukraine", "israel", "gaza$", "iran$", "geopolitic",
)

# Kesin magazin/eğlence terimleri: konu terimi eşleşse bile eler.
_BLOCK_TERMS = (
    "magazin", "şarkıcı", "ünlü oyuncu", "ünlü isim", "manken", "fenomen", "flört", "sevgilisi", "boşanma", "hamile",
    "düğün", "astroloji", "burç", "günlük burç", "kızıl halı", "gelin ", "dizi oyuncu", "evlendi", "aşk yaşa",
    "celebrity", "celebrities", "gossip", "kardashian", "hollywood", "horoscope", "reality tv", "red carpet",
    "royal family", "grammy", "oscars$", "box office",
)


def _fold(text: str) -> str:
    return text.translate(_FOLD).lower()


def _compile(terms: Iterable[str]) -> re.Pattern:
    parts = []
    for term in terms:
        exact = term.endswith("$")
        body = re.escape(_fold(term[:-1] if exact else term))
        parts.append(body + (r"(?!\w)" if exact else ""))
    return re.compile(r"(?<!\w)(?:" + "|".join(parts) + ")")


_TOPIC = _compile(_TOPIC_TERMS)
_BLOCK = _compile(_BLOCK_TERMS)


def _text(item: NewsItem) -> str:
    return _fold(f"{item.title} {item.summary}")


def is_blocked(item: NewsItem) -> bool:
    """Başlık veya özet kesin magazin/eğlence terimi içerir."""
    return _BLOCK.search(_text(item)) is not None


def is_on_topic(item: NewsItem) -> bool:
    """Konu terimlerinden en az biri geçer ve magazin terimi geçmez."""
    text = _text(item)
    return _BLOCK.search(text) is None and _TOPIC.search(text) is not None
