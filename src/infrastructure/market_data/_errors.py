from __future__ import annotations

import json
import urllib.error

try:
    from pandas.errors import ParserError
except ImportError:
    ParserError = ValueError

try:
    from yfinance.exceptions import YFException
except ImportError:
    YFException = RuntimeError

from src.domain.exceptions import MarketDataUnavailableError


MARKET_DATA_FALLBACK_ERRORS = (
    MarketDataUnavailableError,
    YFException,
    urllib.error.URLError,
    TimeoutError,
    OSError,
    json.JSONDecodeError,
    ParserError,
    TypeError,
    ValueError,
    KeyError,
    AttributeError,
    IndexError,
)
