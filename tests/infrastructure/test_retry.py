"""Ağ çağrıları için üstel geri çekilmeli yeniden deneme yardımcısı."""
from __future__ import annotations

import io
import urllib.error

import pytest
import requests

import src.infrastructure.retry as retry
from src.infrastructure.retry import is_transient_error, raise_for_transient_status, retry_call


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("http://x", code, "err", {}, io.BytesIO(b""))


class _Flaky:
    def __init__(self, failures: list[Exception], result="ok"):
        self.failures = list(failures)
        self.result = result
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return self.result


@pytest.mark.parametrize(
    "exc",
    [
        urllib.error.URLError("dns"),
        TimeoutError(),
        ConnectionResetError(),
        _http_error(429),
        _http_error(503),
        requests.exceptions.ConnectionError(),
        requests.exceptions.Timeout(),
    ],
)
def test_transient_errors_are_detected(exc):
    assert is_transient_error(exc) is True


@pytest.mark.parametrize("exc", [_http_error(404), _http_error(400), ValueError("x"), KeyError("k")])
def test_permanent_errors_are_not_transient(exc):
    assert is_transient_error(exc) is False


def test_http_error_response_status_decides_for_requests():
    transient = requests.exceptions.HTTPError(response=type("R", (), {"status_code": 502})())
    permanent = requests.exceptions.HTTPError(response=type("R", (), {"status_code": 403})())

    assert is_transient_error(transient) is True
    assert is_transient_error(permanent) is False


def test_retry_succeeds_after_transient_failures():
    op = _Flaky([urllib.error.URLError("a"), TimeoutError()])

    assert retry_call(op, attempts=3) == "ok"
    assert op.calls == 3


def test_retry_raises_last_error_when_attempts_exhausted():
    op = _Flaky([TimeoutError("1"), TimeoutError("2"), TimeoutError("3")])

    with pytest.raises(TimeoutError, match="3"):
        retry_call(op, attempts=3)
    assert op.calls == 3


def test_permanent_error_is_not_retried():
    op = _Flaky([_http_error(404)])

    with pytest.raises(urllib.error.HTTPError):
        retry_call(op, attempts=3)
    assert op.calls == 1


def test_backoff_doubles_between_attempts(monkeypatch):
    delays: list[float] = []
    monkeypatch.setattr(retry, "_sleep", delays.append)
    op = _Flaky([TimeoutError(), TimeoutError(), TimeoutError(), TimeoutError()])

    with pytest.raises(TimeoutError):
        retry_call(op, attempts=4, base_delay=2.0)

    assert delays == [2.0, 4.0, 8.0]


def test_custom_retry_predicate_retries_any_error():
    op = _Flaky([ValueError("x")])

    assert retry_call(op, attempts=2, is_retryable=lambda _exc: True) == "ok"


def test_attempts_must_be_positive():
    with pytest.raises(ValueError):
        retry_call(lambda: 1, attempts=0)


def test_raise_for_transient_status_only_raises_for_429_and_5xx():
    class Response:
        def __init__(self, status_code):
            self.status_code = status_code

        def raise_for_status(self):
            raise requests.exceptions.HTTPError(response=self)

    raise_for_transient_status(Response(200))
    raise_for_transient_status(Response(404))
    with pytest.raises(requests.exceptions.HTTPError):
        raise_for_transient_status(Response(503))
