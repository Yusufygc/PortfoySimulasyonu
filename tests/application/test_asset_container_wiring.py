"""Varlık defteri servisi ve repository'leri uygulama container'ında kayıtlıdır (geçici veritabanıyla)."""
from __future__ import annotations

from src.application.container import AppContainer
from src.application.services.assets.asset_ledger_service import AssetLedgerService


def test_container_exposes_asset_ledger_service_and_repositories():
    container = AppContainer()

    assert isinstance(container.asset_ledger_service, AssetLedgerService)
    for name in ("asset_repo", "asset_trade_repo", "asset_price_repo", "fx_rate_repo"):
        assert getattr(container, name) is not None
    assert container.asset_ledger_service.get_ledger().open_positions() is not None
