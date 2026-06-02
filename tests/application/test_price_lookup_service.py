from datetime import datetime, timezone
from decimal import Decimal

from src.application.services.market.price_lookup_service import PriceLookupService, PriceLookupSnapshot


class FakePriceLookupProvider:
    def __init__(self, snapshot: PriceLookupSnapshot | None) -> None:
        self.snapshot = snapshot
        self.requests: list[str] = []

    def lookup(self, normalized_ticker: str) -> PriceLookupSnapshot | None:
        self.requests.append(normalized_ticker)
        return self.snapshot


def test_price_lookup_normalizes_ticker_and_returns_company_name_for_intraday():
    provider = FakePriceLookupProvider(
        PriceLookupSnapshot(
            intraday_price=Decimal("401.75"),
            company_name="Aselsan Elektronik Sanayi ve Ticaret A.S.",
        )
    )

    result = PriceLookupService(provider=provider).lookup_price_for_ticker("asels")

    assert provider.requests == ["ASELS.IS"]
    assert result.price == Decimal("401.75")
    assert result.source == "intraday"
    assert result.company_name == "Aselsan Elektronik Sanayi ve Ticaret A.S."
    assert result.normalized_ticker == "ASELS.IS"


def test_price_lookup_uses_last_close_with_latest_returned_history_date():
    provider = FakePriceLookupProvider(
        PriceLookupSnapshot(
            last_close_price=Decimal("401.75"),
            last_close_as_of=datetime(2026, 5, 26, tzinfo=timezone.utc),
            company_name="ASELSAN",
        )
    )

    result = PriceLookupService(provider=provider).lookup_price_for_ticker("ASELS.IS")

    assert result.price == Decimal("401.75")
    assert result.source == "last_close"
    assert result.company_name == "ASELSAN"
    assert result.normalized_ticker == "ASELS.IS"
    assert result.as_of == datetime(2026, 5, 26, tzinfo=timezone.utc)
    assert provider.requests == ["ASELS.IS"]
