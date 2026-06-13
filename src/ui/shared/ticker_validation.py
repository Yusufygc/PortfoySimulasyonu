from __future__ import annotations

import re


_TICKER_RE = re.compile(r"^[A-Z0-9]+(?:\.IS)?$")


def normalize_ticker_input(value: str) -> str:
    ticker = (value or "").strip().upper()
    if ticker and "." not in ticker:
        ticker += ".IS"
    return ticker


def is_valid_ticker_input(value: str) -> bool:
    ticker = (value or "").strip().upper()
    if not ticker:
        return False
    if not _TICKER_RE.fullmatch(ticker):
        return False
    base = ticker.removesuffix(".IS")
    return any(char.isalpha() for char in base)
