"""AI_Core HTTP istemcisi: bağlantı, zaman aşımı, HTTP hata ve bozuk JSON aileleri."""
from __future__ import annotations

import pytest
import requests

from src.infrastructure.ai.ai_core_fastapi_client import (
    AICoreFastAPIClient,
    APIConnectionError,
    APIResponseError,
)


class _Response:
    def __init__(self, status_code=200, payload=None, text="", json_error=False):
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self._json_error = json_error

    def json(self):
        if self._json_error:
            raise ValueError("bozuk")
        return self._payload


def _client(monkeypatch, outcome):
    client = AICoreFastAPIClient(base_url="http://core.test/", log_connection_errors=False)

    def fake_get(url, params=None, timeout=None):
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(client._session, "get", fake_get)
    return client


def test_base_url_trailing_slash_is_trimmed():
    assert AICoreFastAPIClient(base_url="http://core.test/").base_url == "http://core.test"


def test_success_returns_json_payload(monkeypatch):
    client = _client(monkeypatch, _Response(payload={"symbols": ["THYAO", "ASELS"]}))

    assert client.get_symbols() == ["THYAO", "ASELS"]


def test_connection_error_becomes_api_connection_error(monkeypatch):
    client = _client(monkeypatch, requests.ConnectionError("reddedildi"))

    with pytest.raises(APIConnectionError, match="bağlanılamadı"):
        client.get_analysis("thyao")


def test_timeout_becomes_api_connection_error(monkeypatch):
    client = _client(monkeypatch, requests.Timeout("yavaş"))

    with pytest.raises(APIConnectionError, match="zaman aşımına"):
        client.get_best_model("THYAO")


def test_http_error_uses_json_detail(monkeypatch):
    client = _client(monkeypatch, _Response(status_code=404, payload={"detail": "sembol yok"}))

    with pytest.raises(APIResponseError) as info:
        client.get_analysis("YOKTUR")

    assert info.value.status_code == 404 and info.value.detail == "sembol yok"


def test_http_error_with_non_json_body_keeps_truncated_text(monkeypatch):
    client = _client(monkeypatch, _Response(status_code=502, text="x" * 500, json_error=True))

    with pytest.raises(APIResponseError) as info:
        client.get_leaderboard()

    assert info.value.status_code == 502 and len(info.value.detail) == 200


def test_invalid_json_on_success_raises_response_error(monkeypatch):
    client = _client(monkeypatch, _Response(status_code=200, json_error=True))

    with pytest.raises(APIResponseError, match="Geçersiz JSON"):
        client.get_symbols()


@pytest.mark.parametrize("payload, expected", [
    ({"status": "ok"}, True),
    ({"status": "degraded"}, True),
    ({"status": "down"}, False),
])
def test_health_check_reads_status(monkeypatch, payload, expected):
    assert _client(monkeypatch, _Response(payload=payload)).health_check() is expected


def test_health_check_returns_false_on_any_failure(monkeypatch):
    assert _client(monkeypatch, requests.ConnectionError("kapalı")).health_check() is False
