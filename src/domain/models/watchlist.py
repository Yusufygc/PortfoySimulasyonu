# src/domain/models/watchlist.py

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class WatchlistItem:
    """
    Bir watchlist içindeki tek bir hisse kaydını temsil eder.
    'watchlist_items' tablosunun domain karşılığı.
    """
    id: Optional[int]
    watchlist_id: int
    stock_id: int
    notes: Optional[str] = None
    added_at: Optional[datetime] = None


@dataclass(frozen=True)
class Watchlist:
    """
    Kullanıcının oluşturduğu hisse takip listesi.
    'watchlists' tablosunun domain karşılığı.
    """
    id: Optional[int]
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
