from src.application.services.portfolio.portfolio_reset_service import PortfolioResetService


class CallRecorder:
    def __init__(self):
        self.calls = []

    def record(self, name):
        self.calls.append(name)


class FakePortfolioRepo:
    def __init__(self, recorder):
        self._recorder = recorder

    def delete_all_trades(self):
        self._recorder.record("trades")


class FakePriceRepo:
    def __init__(self, recorder):
        self._recorder = recorder

    def delete_all_prices(self):
        self._recorder.record("prices")


class FakeStockRepo:
    def __init__(self, recorder):
        self._recorder = recorder

    def delete_all_stocks(self):
        self._recorder.record("stocks")


class FakeWatchlistRepo:
    def __init__(self, recorder):
        self._recorder = recorder

    def delete_all_watchlists(self):
        self._recorder.record("watchlists")


class FakeModelPortfolioRepo:
    def __init__(self, recorder):
        self._recorder = recorder

    def delete_all_model_portfolios(self):
        self._recorder.record("model_portfolios")


def test_reset_all_deletes_stock_dependents_before_stocks():
    recorder = CallRecorder()
    service = PortfolioResetService(
        portfolio_repo=FakePortfolioRepo(recorder),
        price_repo=FakePriceRepo(recorder),
        stock_repo=FakeStockRepo(recorder),
        watchlist_repo=FakeWatchlistRepo(recorder),
        model_portfolio_repo=FakeModelPortfolioRepo(recorder),
    )

    service.reset_all()

    assert recorder.calls == [
        "model_portfolios",
        "watchlists",
        "trades",
        "prices",
        "stocks",
    ]


def test_reset_all_keeps_backward_compatible_core_reset():
    recorder = CallRecorder()
    service = PortfolioResetService(
        portfolio_repo=FakePortfolioRepo(recorder),
        price_repo=FakePriceRepo(recorder),
        stock_repo=FakeStockRepo(recorder),
    )

    service.reset_all()

    assert recorder.calls == ["trades", "prices", "stocks"]
