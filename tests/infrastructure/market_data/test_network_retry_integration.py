"""Ağ istemcilerinin geçici hatada yeniden denediği ve kalıcı hatada denemediği doğrulanır (canlı ağ yok)."""
from __future__ import annotations

import io
import json
import urllib.error
from datetime import date

import pandas as pd
import pytest

from src.domain.exceptions import MarketDataUnavailableError
from src.infrastructure.market_data import evds_client as evds_module
from src.infrastructure.market_data import yfinance_client as yf_module
from src.infrastructure.market_data.evds_client import EvdsClient
from src.infrastructure.market_data.yfinance_client import YFinanceMarketDataClient


class _Response:
    def __init__(self, payload: dict):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def _evds() -> EvdsClient:
    client = EvdsClient()
    client._api_key = "test"
    return client


def test_evds_retries_transient_failure_then_succeeds(monkeypatch):
    attempts = []

    def fake_urlopen(_request, timeout):
        attempts.append(1)
        if len(attempts) < 3:
            raise urllib.error.URLError("gecici")
        return _Response({"items": [{"a": 1}]})

    monkeypatch.setattr(evds_module, "urlopen", fake_urlopen)

    assert _evds().get_series("TP.X", date(2026, 1, 1), date(2026, 1, 31)) == [{"a": 1}]
    assert len(attempts) == 3


def test_evds_does_not_retry_permanent_http_error(monkeypatch):
    attempts = []

    def fake_urlopen(_request, timeout):
        attempts.append(1)
        raise urllib.error.HTTPError("http://x", 403, "yasak", {}, io.BytesIO(b""))

    monkeypatch.setattr(evds_module, "urlopen", fake_urlopen)

    with pytest.raises(MarketDataUnavailableError):
        _evds().get_series("TP.X", date(2026, 1, 1), date(2026, 1, 31))
    assert len(attempts) == 1


def test_yfinance_client_download_retries_rate_limit(monkeypatch):
    from yfinance.exceptions import YFRateLimitError

    attempts = []

    def fake_download(**_kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            raise YFRateLimitError()
        return pd.DataFrame({"Close": [1.0]})

    monkeypatch.setattr(yf_module.yf, "download", fake_download)
    client = YFinanceMarketDataClient()

    frame = client._download_dataframe("THYAO.IS", date(2026, 1, 1), date(2026, 1, 5))

    assert len(attempts) == 2
    assert list(frame["Close"]) == [1.0]
