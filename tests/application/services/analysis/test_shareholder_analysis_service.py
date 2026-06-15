"""ShareholderAnalysisService birim testleri (mock provider + repo)."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

from src.domain.models.shareholder import ShareholderRow, ShareholderSnapshot
from src.application.services.analysis.shareholder_analysis_service import (
    ShareholderAnalysisService,
)


def _snapshot(d: date, name="A", ratio=50) -> ShareholderSnapshot:
    return ShareholderSnapshot(
        creation_date=d,
        rows=(ShareholderRow(
            shareholder_name=name,
            share_in_capital=Decimal("100"),
            ratio_in_capital=Decimal(str(ratio)),
            voting_right_ratio=Decimal(str(ratio)),
        ),),
    )


class TestGetHistory:
    def test_cache_fresh_returns_repo(self):
        provider = MagicMock()
        repo     = MagicMock()
        repo.get_last_fetched_at.return_value = datetime.utcnow() - timedelta(hours=2)
        repo.get_shareholder_history.return_value = [_snapshot(date(2025, 1, 1))]
        svc = ShareholderAnalysisService(provider=provider, repository=repo)

        out = svc.get_history("FROTO")

        assert len(out) == 1
        provider.get_shareholder_history.assert_not_called()

    def test_cache_stale_refreshes(self):
        provider = MagicMock()
        provider.resolve_member_oid.return_value = ("OID123", "FORD")
        provider.get_shareholder_history.return_value = [_snapshot(date(2026, 1, 1))]
        repo = MagicMock()
        repo.get_last_fetched_at.return_value = datetime.utcnow() - timedelta(days=2)
        svc = ShareholderAnalysisService(provider=provider, repository=repo)

        out = svc.get_history("FROTO")

        assert len(out) == 1
        provider.get_shareholder_history.assert_called_once_with("FROTO")
        repo.upsert_company.assert_called_once_with("FROTO", "OID123", "FORD")
        repo.replace_shareholder_history.assert_called_once()

    def test_no_cache_triggers_refresh(self):
        provider = MagicMock()
        provider.resolve_member_oid.return_value = ("OID999", None)
        provider.get_shareholder_history.return_value = []
        repo = MagicMock()
        repo.get_last_fetched_at.return_value = None
        svc = ShareholderAnalysisService(provider=provider, repository=repo)

        svc.get_history("ASELS")

        provider.get_shareholder_history.assert_called_once()

    def test_force_refresh_bypasses_cache(self):
        provider = MagicMock()
        provider.resolve_member_oid.return_value = ("OID", "T")
        provider.get_shareholder_history.return_value = []
        repo = MagicMock()
        repo.get_last_fetched_at.return_value = datetime.utcnow()  # fresh
        svc = ShareholderAnalysisService(provider=provider, repository=repo)

        svc.get_history("THYAO", force_refresh=True)

        provider.get_shareholder_history.assert_called_once()

    def test_ticker_normalized_to_upper(self):
        provider = MagicMock()
        provider.resolve_member_oid.return_value = ("OID", "T")
        provider.get_shareholder_history.return_value = []
        repo = MagicMock()
        repo.get_last_fetched_at.return_value = None
        svc = ShareholderAnalysisService(provider=provider, repository=repo)

        svc.get_history("froto")

        repo.upsert_company.assert_called_once_with("FROTO", "OID", "T")
