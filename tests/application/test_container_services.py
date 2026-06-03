from types import SimpleNamespace

from src.application.container_parts.services import build_services


def _fake_repositories():
    return SimpleNamespace(
        cash_movement_repo=object(),
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
    )


def _fake_market_clients():
    return SimpleNamespace(
        evds_client=object(),
        market_client=object(),
        optimization_market_data_provider=object(),
        price_lookup_service=object(),
        trading_calendar=object(),
    )


def test_build_services_wires_corporate_action_services():
    services = build_services(
        repositories=_fake_repositories(),
        market_clients=_fake_market_clients(),
        event_bus=object(),
    )

    assert services.corporate_action_service._price_adjustment_service is not None
    assert (
        services.corporate_action_candidate_review_service._corporate_action_service
        is services.corporate_action_service
    )
    assert services.live_price_refresh_service._price_data_health_service is services.price_data_health_service
