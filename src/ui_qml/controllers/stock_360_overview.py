"""Hisse 360 genel bakış ve teknik seviye alanları (saf fonksiyonlar).

`Stock360Controller` servis nesnelerini buraya verir; çıktı sözlükleri `stock_360_fallback.get_default_overview` /
`get_default_technical` ile aynı anahtarları taşır, böylece denetleyici gerçek ve varsayılan veriyi aynı yoldan uygular.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Tuple

from src.ui_qml.controllers.stock_360_fallback import guess_sector
from src.ui_qml.controllers.stock_360_formatters import format_price, format_volume

_DEFAULT_SECTOR = "BIST Şirketi"
_MISSING = "—"
_RSI_OVERBOUGHT = 70
_RSI_OVERSOLD = 30


def _find_stock(container: Any, service: Any, ticker: str) -> Any:
    if service and hasattr(service, "get_stock_by_ticker"):
        return service.get_stock_by_ticker(ticker) or service.get_stock_by_ticker(f"{ticker}.IS")
    lookup = getattr(container, "stock_lookup_service", None)
    return lookup.find_stock(ticker) if lookup is not None else None


def resolve_identity(container: Any, service: Any, ticker: str) -> Tuple[str, str]:
    """`(şirket adı, sektör)`: önce portföy (SQLite) kaydı, yoksa DuckDB katalog adı, yoksa ticker."""
    stock = _find_stock(container, service, ticker)
    if stock:
        sector = getattr(stock, "sector", None) or guess_sector(ticker)
        return stock.name or ticker, sector
    if service and hasattr(service, "get_company_name"):
        catalog_name = service.get_company_name(ticker)
        name = catalog_name if isinstance(catalog_name, str) and catalog_name else ticker
        return name, guess_sector(ticker)
    return ticker, _DEFAULT_SECTOR


def _week52_range_position(last: float, low: float, high: float) -> float:
    if high <= low:
        return 0.5
    return max(0.0, min(1.0, (last - low) / (high - low)))


def overview_fields(overview: Any) -> Dict[str, Any]:
    """Servis genel bakış nesnesinden denetleyici alanları."""
    last = float(overview.last_price)
    change = overview.daily_change_pct or 0.0
    return {
        "last_price_str": format_price(overview.last_price),
        "last_price_raw": last,
        "last_price_date_str": overview.last_price_date.strftime("%d.%m.%Y"),
        "daily_change_str": f"{'+' if change >= 0 else ''}{change:.2f}%",
        "daily_change_raw": float(change),
        "is_daily_positive": change >= 0,
        "volume_str": format_volume(overview.volume),
        "week52_low_str": format_price(overview.week52_low),
        "week52_high_str": format_price(overview.week52_high),
        "week52_range_pct": _week52_range_position(last, float(overview.week52_low), float(overview.week52_high)),
    }


def rsi_status(rsi14: float) -> str:
    if rsi14 >= _RSI_OVERBOUGHT:
        return "Aşırı Alım"
    if rsi14 <= _RSI_OVERSOLD:
        return "Aşırı Satım"
    return "Dengeli"


def trend_status(sma50: float | None, sma200: float | None) -> str:
    if sma50 is None or sma200 is None:
        return "Dengeli"
    return "Boğa / Golden Trend" if sma50 > sma200 else "Ayı / Baskılı"


def _formatted(value: float | None, formatter: Callable[[float], str]) -> str:
    return formatter(value) if value is not None else _MISSING


def technical_fields(tech: Any) -> Dict[str, Any]:
    """Servis teknik seviye nesnesinden denetleyici alanları."""
    has_rsi = tech.rsi14 is not None
    return {
        "rsi14_str": f"{tech.rsi14:.1f}" if has_rsi else _MISSING,
        "rsi_status": rsi_status(tech.rsi14) if has_rsi else "Nötr",
        "macd_line_str": _formatted(tech.macd_line, lambda v: f"{v:.2f}"),
        "macd_signal_str": _formatted(tech.macd_signal, lambda v: f"{v:.2f}"),
        "sma50_str": _formatted(tech.sma50, format_price),
        "sma200_str": _formatted(tech.sma200, format_price),
        "ema20_str": _formatted(tech.ema20, format_price),
        "support_str": _formatted(tech.support, format_price),
        "resistance_str": _formatted(tech.resistance, format_price),
        "trend_status": trend_status(tech.sma50, tech.sma200),
    }
