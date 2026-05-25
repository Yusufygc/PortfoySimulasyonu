from __future__ import annotations


def display_ticker(ticker: str | None) -> str:
    """Return a UI-facing ticker without the BIST Yahoo suffix."""
    value = (ticker or "").strip()
    if value.upper().endswith(".IS"):
        return value[:-3]
    return value
