import pytest

from src.application.services.portfolio.portfolio_maintenance_service import (
    PortfolioMaintenanceService,
    PurgeStockResult,
)


class FakeMaintenanceRepo:
    def __init__(self, result=None):
        self.calls = []
        self.result = result or PurgeStockResult(ticker="THYAO", stock_ids=())

    def purge_stock_by_ticker(self, ticker):
        self.calls.append(ticker)
        return self.result


def test_purge_stock_by_ticker_normalizes_is_suffix():
    repo = FakeMaintenanceRepo(PurgeStockResult(ticker="THYAO", stock_ids=(10,), deleted_stocks=1))
    service = PortfolioMaintenanceService(repo)

    result = service.purge_stock_by_ticker("thyao.is")

    assert repo.calls == ["THYAO"]
    assert result.deleted_stocks == 1


def test_purge_stock_by_ticker_rejects_empty_ticker():
    service = PortfolioMaintenanceService(FakeMaintenanceRepo())

    with pytest.raises(ValueError):
        service.purge_stock_by_ticker("  ")
