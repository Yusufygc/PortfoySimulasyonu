# src/ui/pages/ai_page/core/safety_guard.py
"""
Yapay zeka asistanı sohbet girdisi için güvenlik süzgeci (Prompt Injection Guard).
"""

import re
from typing import Tuple

# En yaygın İngilizce ve Türkçe jailbreak / prompt injection kalıpları
INJECTION_PATTERNS = [
    # English patterns
    r"ignore\s+(?:previous|above|all|system)\s+instructions",
    r"forget\s+(?:previous|above|all|system)\s+instructions",
    r"you\s+are\s+now\s+a",
    r"roleplay\s+as",
    r"bypass\s+restrictions",
    r"jailbreak",
    r"system\s+prompt",
    r"ignore\s+rules",
    r"override\s+rules",
    r"respond\s+as\s+a",
    
    # Turkish patterns
    r"sistem\s+talimatlar\u0131n\u0131\s+yoksay",
    r"sistem\s+talimat\u0131n\u0131\s+yoksay",
    r"talimatlar\u0131\s+unut",
    r"kurallar\u0131\s+unut",
    r"t\u00fcm\s+kurallar\u0131\s+yoksay",
    r"sen\s+art\u0131k\s+bir",
    r"rol\u00fcn\u00fc\s+de\u011fi\u015ftir",
    r"asistan\s+rol\u00fcn\u00fc\s+b\u0131rak",
    r"yat\u0131r\u0131m\s+tavsiyesi\s+ver",
    r"al\s+sat\s+sinyali\s+ver",
    r"tavsiye\s+et",
]

# Performans için regex derlemesi (büyük/küçük harf duyarsız)
_INJECTION_RE = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)

# Maksimum karakter sınırı (Faz 3 esnetilmiş hali)
MAX_CHAR_LIMIT = 750

def validate_user_input(text: str) -> Tuple[bool, str]:
    """
    Kullanıcı girdisini prompt enjeksiyonu ve karakter sınırı açısından doğrular.
    
    Returns:
        (is_safe, error_message): Girdi güvenliyse (True, ""), riskliyse (False, Hata_Mesajı).
    """
    if not text or not text.strip():
        return True, ""

    # 1. Uzunluk kontrolü (aşırı uzun jailbreak payload'larını engeller)
    if len(text) > MAX_CHAR_LIMIT:
        return False, f"Güvenlik Uyarısı: Girdiğiniz mesaj çok uzun (en fazla {MAX_CHAR_LIMIT} karakter olmalıdır)."

    # 2. Kalıp eşleşme kontrolü (Prompt injection kalıplarını arar)
    if _INJECTION_RE.search(text):
        return False, "Güvenlik Uyarısı: Girdiğiniz mesaj sistem talimatlarını değiştirme veya prompt enjeksiyonu riski taşıdığı için engellenmiştir."

    return True, ""

def wrap_user_message(text: str) -> str:
    """
    Kullanıcı girdisini yapısal sınırlar içerisine alarak Gemini'nin 
    veri ile talimat ayrımını netleştirmesini sağlar.
    """
    return f"[USER INPUT START]\n{text}\n[USER INPUT END]"
