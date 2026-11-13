"""Uygulama servislerinin kurulumu: özellik modüllerini (`features/`) sırayla kurar.

Servisler özellik başına `features/<özellik>.py` içinde tanımlıdır; bu dosya yalnızca sırayı yürütür ve yeni servis
eklerken değişmez.
"""
from __future__ import annotations

from config.settings_loader import MarketSettings

from src.application.container_parts.features import FEATURES, BuildContext, ServiceRegistry, build_features
from src.application.container_parts.market_clients import MarketClientSet
from src.application.container_parts.repositories import RepositorySet


def build_services(
    repositories: RepositorySet,
    market_clients: MarketClientSet,
    market_settings: MarketSettings | None = None,
) -> ServiceRegistry:
    ctx = BuildContext(repositories=repositories, market_clients=market_clients, market_settings=market_settings)
    return build_features(ctx, FEATURES)
