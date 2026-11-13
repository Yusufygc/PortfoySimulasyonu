"""Piyasa geçmişi (DuckDB) için ticker bazlı sermaye artırımı/bölünme olayı ve fiyat düzeltme faktörü.

Ham barlar asla değiştirilmez. Her olay, `effective_date` (yeni fiyat bazındaki ilk bar) öncesindeki
barlar için çarpılacak bir `factor` taşır. Düzeltilmiş fiyat = ham fiyat x (kendinden sonraki
ONAYLI olayların faktörleri çarpımı).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Iterable, Optional


class MarketActionType(str, Enum):
    BEDELSIZ = "BEDELSIZ"  # bedelsiz sermaye artırımı / bölünme: faktör = 1 / (1 + oran)
    BEDELLI = "BEDELLI"  # bedelli sermaye artırımı: faktör = TERP / P0
    REVERSE_SPLIT = "REVERSE_SPLIT"  # birleştirme (ters bölünme): faktör > 1
    OTHER = "OTHER"  # kaynağı tam anlaşılamayan, yalnızca veriden gözlenen kırılma


class MarketActionStatus(str, Enum):
    CANDIDATE = "CANDIDATE"  # veriden tespit edildi, onay bekliyor
    CONFIRMED = "CONFIRMED"  # kullanıcı onayladı: düzeltmeye dahil
    IGNORED = "IGNORED"  # kullanıcı reddetti (ör. veri hatası, askı sonrası boşluk)
    NO_BREAK = "NO_BREAK"  # ham veride kırılma yok (kaynak zaten düzeltmiş): düzeltmeye dahil DEĞİL


class MarketActionSource(str, Enum):
    DETECTED = "DETECTED"
    KAP = "KAP"
    PORTFOLIO = "PORTFOLIO"  # portföy kurumsal aksiyon akışından aktarıldı
    MIGRATION = "MIGRATION"  # SQLite'taki düzeltilmiş geçmiş ile DuckDB ham geçmişinin farkından türetildi
    MANUAL = "MANUAL"


@dataclass(frozen=True)
class MarketCorporateAction:
    ticker: str
    effective_date: date
    factor: float
    action_type: MarketActionType = MarketActionType.OTHER
    status: MarketActionStatus = MarketActionStatus.CANDIDATE
    source: MarketActionSource = MarketActionSource.DETECTED
    ex_date: Optional[date] = None
    ratio: Optional[float] = None
    rights_price: Optional[float] = None
    observed_ratio: Optional[float] = None  # ham veride gözlenen önceki kapanış / yeni kapanış
    confidence: Optional[float] = None
    note: str = ""

    def __post_init__(self) -> None:
        if not self.ticker:
            raise ValueError("ticker zorunludur")
        if not self.factor or self.factor <= 0:
            raise ValueError("factor pozitif olmalıdır")

    @property
    def is_active(self) -> bool:
        return self.status == MarketActionStatus.CONFIRMED


@dataclass(frozen=True)
class PriceBreak:
    """Ham fiyat serisinde bir günden diğerine gözlenen büyük kırılma (olay adayı için ham girdi)."""

    ticker: str
    price_date: date  # kırılma sonrası ilk bar (yeni bazdaki ilk gün)
    prev_date: date
    prev_close: float
    close: float
    volume: Optional[int] = None
    prev_volume: Optional[int] = None
    prev2_close: Optional[float] = None  # kırılmadan iki bar önceki kapanış
    next_closes: tuple = ()  # kırılmadan sonraki en çok 3 bar kapanışı
    market_ratio: Optional[float] = None  # aynı gün tüm hisselerin medyan (önceki / yeni) kapanış oranı

    @property
    def observed_ratio(self) -> float:
        return self.prev_close / self.close


def bedelsiz_factor(ratio: float) -> float:
    """Bedelsiz oranı (0.5 = %50) için fiyat çarpanı: 1 / (1 + oran)."""
    if ratio <= 0:
        raise ValueError("bedelsiz oranı pozitif olmalıdır")
    return 1.0 / (1.0 + ratio)


def bedelli_factor(ratio: float, rights_price: float, previous_close: float) -> float:
    """Bedelli için TERP/P0 çarpanı; P0 ex-date öncesi HAM kapanıştır."""
    if ratio <= 0 or rights_price < 0 or previous_close <= 0:
        raise ValueError("bedelli faktörü için oran, kullanım fiyatı ve önceki kapanış gerekir")
    return (previous_close + ratio * rights_price) / ((1.0 + ratio) * previous_close)


def cumulative_factor(actions: Iterable[MarketCorporateAction], bar_date: date) -> float:
    """`bar_date` tarihli bara uygulanacak toplam çarpan (yalnızca onaylı, sonraki olaylar)."""
    factor = 1.0
    for action in actions:
        if action.is_active and bar_date < action.effective_date:
            factor *= action.factor
    return factor
