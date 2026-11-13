"""KAP ortaklık yapısı domain modelleri."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class ShareholderRow:
    """Tek pay sahibi satırı (snapshot içinde)."""
    shareholder_name: str
    share_in_capital: Optional[Decimal]   # TL (mn değil — ham)
    ratio_in_capital: Optional[Decimal]   # %
    voting_right_ratio: Optional[Decimal] # %
    is_total: bool = False


@dataclass(frozen=True)
class ShareholderSnapshot:
    """Belirli bir tarihteki ortaklık yapısı snapshot'ı."""
    creation_date: date
    rows: tuple[ShareholderRow, ...] = field(default_factory=tuple)
