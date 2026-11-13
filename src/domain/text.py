"""Türkçe duyarlı metin karşılaştırma yardımcıları (saf fonksiyonlar).

Python'un varsayılan `str.lower()` işlevi `İ` harfini `i` + birleştirici nokta (U+0307) yapar ve `I` harfini `i`
yapar; bu yüzden `"İş".lower() != "iş"`. Ad eşleştirme, arama ve yinelenen kayıt denetimi bu modülü kullanır.
"""
from __future__ import annotations


def tr_lower(text: str) -> str:
    """`İ -> i`, `I -> ı` eşlemesiyle küçük harfe çevirir; görüntüleme ve desen eşleme için."""
    return text.replace("İ", "i").replace("I", "ı").lower()


def tr_fold(text: str) -> str:
    """Büyük/küçük harf ve noktalı/noktasız i farkını yok sayan karşılaştırma anahtarı.

    `ı` da `i`ye indirilir; böylece `ISPARTA`, `ısparta` ve `isparta` aynı anahtarı üretir. Diğer aksanlı harfler
    (ş, ğ, ü, ö, ç) korunur.
    """
    return tr_lower(text).replace("ı", "i").casefold()
