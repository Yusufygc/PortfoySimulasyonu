from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict, Iterable


def build_previous_close_map(price_repo, stock_ids: Iterable[int], reference_date: date) -> Dict[int, Decimal]:
    """
    Belirtilen referans tarihinden önceki en son kapanış fiyatlarını getirir.
    Genellikle günlük K/Z hesaplamalarında referans olarak kullanılır.
    
    Args:
        price_repo: DailyPriceRepository instance
        stock_ids: Hisse id'lerinin listesi veya seti
        reference_date: Hangi tarihten önceki fiyatın aranacağı (genellikle bugün)
        
    Returns:
        Hisse ID'si ile son kapanış fiyatını eşleyen sözlük (Dict[int, Decimal])
    """
    if not stock_ids:
        return {}

    previous_close_map = {}
    for stock_id in stock_ids:
        daily_price = price_repo.get_last_price_before(stock_id, reference_date)
        if daily_price:
            previous_close_map[stock_id] = daily_price.close_price

    return previous_close_map
