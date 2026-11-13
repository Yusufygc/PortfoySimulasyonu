from types import SimpleNamespace

from src.application.container_parts.services import build_services


def _fake_repositories():
    return SimpleNamespace(
        cash_movement_repo=object(),
        ledger_reader=object(),
        split_ledger_repo=object(),
        corporate_action_candidate_repo=object(),
        corporate_action_repo=object(),
        model_portfolio_repo=object(),
        planning_repo=object(),
        portfolio_maintenance_repo=object(),
        portfolio_repo=object(),
        price_repo=object(),
        risk_profile_repo=object(),
        stock_repo=object(),
        watchlist_repo=object(),
        latest_price_repo=object(),
        kap_shareholder_repo=object(),
        golden_cross_repo=object(),
        market_history_repo=object(),
        market_action_repo=object(),
        asset_repo=object(),
        asset_trade_repo=object(),
        asset_price_repo=object(),
        fx_rate_repo=object(),
        news_source_repo=object(),
        app_settings_repo=object(),
        fx_conversion_repo=object(),
        market_history_store=object(),
    )


def _fake_market_clients():
    return SimpleNamespace(
        evds_client=object(),
        isyatirim_provider=object(),
        market_client=object(),
        optimization_market_data_provider=object(),
        price_lookup_service=object(),
        trading_calendar=object(),
        bist_market_session_service=object(),
        evds_tufe_provider=object(),
        yfinance_valuation_provider=object(),
        kap_shareholder_provider=object(),
        asset_price_provider=object(),
    )


def test_build_services_wires_corporate_action_services():
    services = build_services(
        repositories=_fake_repositories(),
        market_clients=_fake_market_clients(),
    )

    assert services.corporate_action_service._price_adjustment_service is not None
    assert (
        services.corporate_action_candidate_review_service._corporate_action_service
        is services.corporate_action_service
    )
    assert services.live_price_refresh_service._price_data_health_service is services.price_data_health_service
    assert services.live_price_refresh_service._latest_price_repo is not None


def test_build_services_injects_configured_deposit_fallback_into_benchmarks():
    from decimal import Decimal

    from config.settings_loader import MarketSettings

    services = build_services(
        repositories=_fake_repositories(),
        market_clients=_fake_market_clients(),
        market_settings=MarketSettings(evds_api_key=None, tcmb_deposit_rate_fallback=Decimal("42.25")),
    )

    benchmark_service = services.analysis_service._benchmark_service
    assert benchmark_service._deposit_rate_fallback == Decimal("42.25")


def test_build_services_wires_split_automation():
    services = build_services(repositories=_fake_repositories(), market_clients=_fake_market_clients())
    automation = services.split_automation_service
    assert automation._d.ledger_repo is automation._d.applier._ledger
    assert automation._d.applier._market is services.market_corporate_action_service
