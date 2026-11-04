"""Türkçe duyarlı küçük harf ve karşılaştırma yardımcıları."""
from __future__ import annotations

import pytest

from src.domain.text import tr_fold, tr_lower


@pytest.mark.parametrize("raw, expected", [
    ("İŞ BANKASI", "iş bankası"),
    ("ISPARTA", "ısparta"),
    ("RİSK", "risk"),
    ("Çalışma Ğ", "çalışma ğ"),
    ("", ""),
])
def test_tr_lower_maps_dotted_and_dotless_i(raw, expected):
    assert tr_lower(raw) == expected


def test_python_default_lower_is_wrong_for_turkish_capital_i():
    """Yardımcının gerekçesi: varsayılan lower() İ için birleştirici nokta üretir."""
    assert "iş" not in "İŞ BANKASI".lower()
    assert "iş" in tr_lower("İŞ BANKASI")


@pytest.mark.parametrize("a, b", [
    ("İş", "iş"),
    ("IŞIK", "ışık"),
    ("Isı", "isi"),
    ("  İştirakler ", "iştirakler"),
])
def test_tr_fold_makes_case_and_dotted_i_variants_equal(a, b):
    assert tr_fold(a.strip()) == tr_fold(b)


def test_tr_fold_keeps_other_diacritics_distinct():
    assert tr_fold("kış") != tr_fold("kis")
