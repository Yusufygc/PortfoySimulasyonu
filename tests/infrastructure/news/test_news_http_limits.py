"""Haber HTTP yardımcısı: büyük yanıtlar tamamı belleğe alınmadan kesilir."""
from __future__ import annotations

from src.infrastructure.news import _http


class _FakeResponse:
    status_code = 200

    def __init__(self, chunks):
        self._chunks = chunks
        self.consumed = 0
        self.closed = False
        self.headers = {}

    def iter_content(self, chunk_size=65536):
        for chunk in self._chunks:
            self.consumed += len(chunk)
            yield chunk

    @property
    def content(self):  # akış modunda tamamını okumak yasak
        raise AssertionError("response.content tüm gövdeyi belleğe alır")

    def close(self):
        self.closed = True


def test_http_get_stops_reading_at_body_limit(monkeypatch):
    chunk = b"x" * (1024 * 1024)
    response = _FakeResponse([chunk] * 100)  # 100 MB akış
    captured = {}

    def fake_get(url, headers=None, timeout=None, stream=False):
        captured["stream"] = stream
        return response

    monkeypatch.setattr(_http.requests, "get", fake_get)

    body = _http.http_get("https://ex.com/feed.xml")

    assert captured["stream"] is True
    assert len(body) == _http.MAX_BODY_BYTES
    assert response.consumed <= _http.MAX_BODY_BYTES + len(chunk)
    assert response.closed is True


class _Plain:
    def __init__(self, status_code=200, body=b"<rss/>"):
        self.status_code = status_code
        self._body = body
        self.closed = False

    def iter_content(self, chunk_size=65536):
        if self._body:
            yield self._body

    def close(self):
        self.closed = True

    def raise_for_status(self):
        import requests

        raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


def _patch_get(monkeypatch, responses):
    queue = list(responses)
    monkeypatch.setattr(_http.requests, "get", lambda *a, **k: queue.pop(0))
    return queue


def test_http_get_returns_body_for_success(monkeypatch):
    _patch_get(monkeypatch, [_Plain(body=b"<rss>ok</rss>")])

    assert _http.http_get("https://ex.com/f") == b"<rss>ok</rss>"


def test_http_get_non_200_and_empty_body_raise_provider_unavailable(monkeypatch):
    import pytest

    from src.domain.ports.services.i_news_provider import NewsProviderUnavailable

    not_found, empty = _Plain(status_code=404), _Plain(body=b"   ")
    _patch_get(monkeypatch, [not_found])
    with pytest.raises(NewsProviderUnavailable, match="HTTP 404"):
        _http.http_get("https://ex.com/f", label="Akış")
    assert not_found.closed is True

    _patch_get(monkeypatch, [empty])
    with pytest.raises(NewsProviderUnavailable, match="boş yanıt"):
        _http.http_get("https://ex.com/f", label="Akış")


def test_http_get_retries_transient_status_then_succeeds(monkeypatch):
    first = _Plain(status_code=503)
    queue = _patch_get(monkeypatch, [first, _Plain(body=b"<rss>ok</rss>")])

    assert _http.http_get("https://ex.com/f") == b"<rss>ok</rss>"
    assert first.closed is True and queue == []


def test_http_get_gives_up_after_repeated_transient_failures(monkeypatch):
    import pytest

    from src.domain.ports.services.i_news_provider import NewsProviderUnavailable

    _patch_get(monkeypatch, [_Plain(status_code=503) for _ in range(3)])

    with pytest.raises(NewsProviderUnavailable, match="503"):
        _http.http_get("https://ex.com/f", label="Akış")
