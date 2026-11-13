"""Yerel danışman motoru için sorgu niyeti tespiti (saf fonksiyonlar).

Alt dize araması (`"al" in metin`) `maliyet`, `analiz`, `altın` gibi sözcüklerde yanlış eşleşir; bu modül
sözcük sınırı ve açık sözcük kökleriyle eşleştirir. Büyük harfli Türkçe girdiler (`İ`, `I`) için ayrıca
Türkçe duyarlı küçük harfe çevirme yapılır.
"""
from __future__ import annotations

import re

from src.domain.text import tr_lower

_OPTIMIZATION_PATTERN = re.compile(
    r"\b(?:optimiz\w*|rebalance\w*|dengele\w*|öneri\w*|al|alım\w*|alm\w*|sat|satış\w*|satm\w*)\b"  # metin-muaf: sorgu niyet eşleme desenleri
)


def is_optimization_query(query: str) -> bool:
    """Sorgu yeniden dengeleme/optimizasyon veya al-sat önerisi istiyorsa True döner.

    Hem Türkçe duyarlı hem varsayılan küçük harf biçimi denenir; böylece `OPTIMIZASYON` gibi noktasız
    büyük I ile yazılmış Latin girdiler de eşleşir.
    """
    candidates = {tr_lower(query), query.lower()}
    return any(_OPTIMIZATION_PATTERN.search(candidate) for candidate in candidates)
