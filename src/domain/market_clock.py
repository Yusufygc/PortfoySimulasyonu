"""Piyasa saati: BIST'in bulunduğu saat dilimine (Europe/Istanbul) göre "şimdi" ve "bugün".

Seans koruması, "bugünkü fiyat" kontrolleri, işlem tarihi/saati varsayılanları ve zamanlanmış senkronlar piyasa
takvimine bağlıdır; bilgisayarın saat dilimi farklıysa `datetime.now()` / `date.today()` yanlış güne veya saate
kayar. Bu modül **saat dilimi bilgisi taşımayan** (naive) Istanbul duvar saati döner; böylece mevcut `datetime.now()`
ve `date.today()` çağrılarının doğrudan yerine geçer ve veritabanındaki naive değerlerle karşılaştırılabilir.

Yalnızca kullanıcıya yerel zaman gösteren yerler (sohbet saati, dosya adı damgaları) bilinçli olarak yerel saatte kalır.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone, tzinfo

MARKET_TIMEZONE_NAME = "Europe/Istanbul"


def _resolve_market_timezone() -> tzinfo:
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(MARKET_TIMEZONE_NAME)
    except Exception:  # tzdata yok (ör. derlenmiş paket): Türkiye 2016'dan beri sabit UTC+3, yaz saati yok
        return timezone(timedelta(hours=3), MARKET_TIMEZONE_NAME)


MARKET_TIMEZONE: tzinfo = _resolve_market_timezone()


def _utc_now() -> datetime:
    """Testlerde yamalanabilen tek zaman kaynağı."""
    return datetime.now(timezone.utc)


def market_now() -> datetime:
    """Istanbul duvar saati (naive)."""
    return _utc_now().astimezone(MARKET_TIMEZONE).replace(tzinfo=None)


def market_today() -> date:
    return market_now().date()


def market_time() -> time:
    """Saniye hassasiyetinde Istanbul saati (mikrosaniyesiz)."""
    return market_now().time().replace(microsecond=0)


def to_market_date(value: datetime) -> date:
    """Zaman damgasının Istanbul takvim günü; saat dilimsiz (naive) değerler UTC kabul edilir."""
    aware = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return aware.astimezone(MARKET_TIMEZONE).date()
