"""Ortak ölçü birimi sabitleri."""
from __future__ import annotations

from decimal import Decimal

# 1 troy ons = 31.1034768 gram (kıymetli maden fiyatları USD/ons gelir, yerel piyasa gram kullanır).
TROY_OUNCE_GRAMS = Decimal("31.1034768")


def ounce_price_to_gram_price(price_per_ounce: Decimal) -> Decimal:
    """USD/ons gibi bir ons fiyatını gram fiyatına çevirir."""
    return price_per_ounce / TROY_OUNCE_GRAMS
