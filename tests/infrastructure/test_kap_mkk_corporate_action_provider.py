import urllib.error
from datetime import date
from decimal import Decimal

from src.domain.models.corporate_action import ActionType
from src.domain.models.corporate_action_candidate import CorporateActionCandidateStatus
from src.infrastructure.corporate_actions import (
    CorporateActionProviderUnavailable,
    KapMkkCorporateActionProvider,
    parse_kap_mkk_disclosure,
)
from src.infrastructure.corporate_actions import kap_mkk_provider


def test_parse_bedelsiz_kap_payload():
    candidate = parse_kap_mkk_disclosure(
        {
            "id": "1603760",
            "ticker": "MERKO",
            "title": "Bedelsiz Sermaye Artirimi",
            "summary": "%638,33834 bedelsiz sermaye artirimi hak kullanim tarihi 05.05.2026",
        }
    )

    assert candidate.ticker == "MERKO.IS"
    assert candidate.action_type == ActionType.BEDELSIZ
    assert candidate.ratio == Decimal("6.3833834")
    assert candidate.ex_date == date(2026, 5, 5)


def test_parse_bedelli_requires_subscription_price_for_ready_status():
    candidate = parse_kap_mkk_disclosure(
        {
            "id": "2",
            "ticker": "ABC.IS",
            "title": "Bedelli Sermaye Artirimi",
            "summary": "%50 bedelli sermaye artirimi hak kullanim tarihi 01.06.2026",
        }
    )

    assert candidate.action_type == ActionType.BEDELLI
    assert candidate.subscription_price is None
    assert candidate.status == CorporateActionCandidateStatus.NEEDS_REVIEW


def test_provider_uses_injected_fetcher_and_filters_tickers():
    payloads = [
        {"id": "1", "ticker": "MERKO", "title": "Bedelsiz", "summary": "%100 05.05.2026"},
        {"id": "2", "ticker": "OTHER", "title": "Bedelsiz", "summary": "%100 05.05.2026"},
    ]
    provider = KapMkkCorporateActionProvider(fetcher=lambda tickers, start, end: payloads)

    result = provider.fetch_candidates(["MERKO.IS"])

    assert [candidate.ticker for candidate in result] == ["MERKO.IS"]


def test_fetch_url_text_maps_http_404_to_provider_unavailable(monkeypatch):
    def fake_urlopen(*args, **kwargs):
        raise urllib.error.HTTPError(
            url="https://www.kap.org.tr/tr/api/disclosureQuery",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(kap_mkk_provider.urllib.request, "urlopen", fake_urlopen)

    try:
        kap_mkk_provider._fetch_url_text("https://www.kap.org.tr/tr/api/disclosureQuery")
    except CorporateActionProviderUnavailable as exc:
        assert "404" in str(exc)
    else:
        raise AssertionError("CorporateActionProviderUnavailable was not raised")


def test_public_listing_html_payload_is_parsed_with_detail_fallback(monkeypatch):
    listing_html = """
    <html>
      <body>
        <a href="/tr/Bildirim/1603760">MERKO Bedelsiz Sermaye Artırımı</a>
        <span>MERKO %638,33834 bedelsiz sermaye artirimi hak kullanim tarihi 05.05.2026</span>
      </body>
    </html>
    """
    detail_text = """
    MERKO GIDA SANAYI VE TICARET A.S.
    Sermaye Artırımı İşlemlerine İlişkin Bildirim
    Pay Grup Bilgileri MERKO, TRAMERKO91A5
    Toplam Bedelsiz Pay Alma Oranı (%) 638,33834
    Hak Kullanım Tarihi 05.05.2026
    """

    monkeypatch.setattr(kap_mkk_provider, "_fetch_url_text", lambda url: detail_text)

    payloads = kap_mkk_provider._payloads_from_listing_html(
        listing_html,
        {"MERKO.IS"},
        date(2026, 5, 1),
        date(2026, 6, 2),
    )
    candidate = parse_kap_mkk_disclosure(payloads[0])

    assert candidate.ticker == "MERKO.IS"
    assert candidate.action_type == ActionType.BEDELSIZ
    assert candidate.ratio == Decimal("6.3833834")
    assert candidate.ex_date == date(2026, 5, 5)
