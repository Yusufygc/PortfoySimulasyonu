# -*- coding: utf-8 -*-
"""Yapay zeka asistanı sohbet girdisi için güvenlik süzgeci.

Prompt injection ve kapsam dışı (kod/yazılım) talepleri ile karakter sınırını
denetler. UI'a bağımlı değildir; hata metinleri sade Türkçedir.
"""

from __future__ import annotations

import os
import re
from typing import Tuple

# Gömülü varsayılan süzgeç listesi (harici dosya bulunamazsa devreye girer)
FALLBACK_PATTERNS = [
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
    r"sistem\s+talimatlarını\s+yoksay",
    r"sistem\s+talimatını\s+yoksay",
    r"talimatları\s+unut",
    r"kuralları\s+unut",
    r"tüm\s+kuralları\s+yoksay",
    r"sen\s+artık\s+bir",
    r"rolünü\s+değiştir",
    r"asistan\s+rolünü\s+bırak",
    r"yatırım\s+tavsiyesi\s+ver",
    r"al\s+sat\s+sinyali\s+ver",
    r"tavsiye\s+et",

    # Programming fallback patterns
    r"kod\s+yaz",
    r"script\s+oluştur",
    r"script\s+yaz",
    r"python\s+kodu",
    r"javascript\s+kodu",
    r"create\s+a\s+class",
    r"define\s+a\s+function",
    r"def\s+\w+\(",
    r"class\s+\w+",
]


def load_safety_patterns() -> list[str]:
    """config/safety_patterns.txt dosyasını okuyup kalıpları döndürür.

    Bulamazsa veya hata oluşursa gömülü FALLBACK_PATTERNS listesini döner.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Bu dosya: src/application/services/ai/safety_guard.py
    # Hedef:     config/safety_patterns.txt
    patterns_path = os.path.abspath(
        os.path.join(current_dir, "../../../../config/safety_patterns.txt")
    )

    if not os.path.exists(patterns_path):
        # İkincil arama (test ortamı vb.)
        patterns_path = os.path.join(current_dir, "safety_patterns.txt")

    if not os.path.exists(patterns_path):
        proj_root = os.path.abspath(os.path.join(current_dir, "../../../../"))
        patterns_path = os.path.join(proj_root, "config", "safety_patterns.txt")

    patterns = []
    if os.path.exists(patterns_path):
        try:
            with open(patterns_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        patterns.append(line)
        except Exception:
            pass

    if not patterns:
        return FALLBACK_PATTERNS
    return patterns


# Güvenlik kalıplarını yükle ve derle (büyük/küçük harf duyarsız)
INJECTION_PATTERNS = load_safety_patterns()
_INJECTION_RE = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)

# Maksimum karakter sınırı
MAX_CHAR_LIMIT = 750


def validate_user_input(text: str) -> Tuple[bool, str]:
    """Kullanıcı girdisini enjeksiyon, kapsam dışı kod talebi ve uzunluk için doğrular.

    Returns:
        (is_safe, error_message): Güvenliyse (True, ""), riskliyse (False, mesaj).
    """
    if not text or not text.strip():
        return True, ""

    if len(text) > MAX_CHAR_LIMIT:
        return False, f"Güvenlik Uyarısı: Girdiğiniz mesaj çok uzun (en fazla {MAX_CHAR_LIMIT} karakter olmalıdır)."

    if _INJECTION_RE.search(text):
        return False, "Güvenlik Uyarısı: Girdiğiniz mesaj sistem talimatlarını değiştirme, enjeksiyon veya kapsam dışı konu (yazılım/kod talebi vb.) riski taşıdığı için engellenmiştir."

    return True, ""


def wrap_user_message(text: str) -> str:
    """Kullanıcı girdisini yapısal sınırlar içine alır (veri/talimat ayrımı)."""
    return f"[USER INPUT START]\n{text}\n[USER INPUT END]"
