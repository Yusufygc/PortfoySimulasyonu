"""Kurumsal aksiyon taramasının hedef hisseleri: herhangi bir defterde işlem görmüş hisseler + izleme listeleri.

Defterler (ana portföy, model portföyler) tek okuma noktasından (`ILedgerReader`) okunur.
"""
from __future__ import annotations

from typing import Optional, Set

from src.domain.ports.repositories.i_ledger_reader import ILedgerReader
from src.domain.ports.repositories.i_watchlist_repo import IWatchlistRepository


def watchlist_stock_ids(watchlist_repo: Optional[IWatchlistRepository]) -> Set[int]:
    if watchlist_repo is None:
        return set()
    ids: Set[int] = set()
    for watchlist in watchlist_repo.get_all_watchlists():
        if watchlist.id is not None:
            ids.update(item.stock_id for item in watchlist_repo.get_items_by_watchlist_id(watchlist.id))
    return ids


def tracked_stock_ids(ledger_reader: Optional[ILedgerReader], watchlist_repo: Optional[IWatchlistRepository]) -> Set[int]:
    traded = ledger_reader.snapshot().instruments() if ledger_reader is not None else set()
    return traded | watchlist_stock_ids(watchlist_repo)
