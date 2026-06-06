from __future__ import annotations

from dataclasses import fields

from config.settings_loader import AppSettings, load_app_settings
from src.application.container_parts import build_ai, build_market_clients, build_repositories, build_services
from src.application.events import GlobalEventBus
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider


class AppContainer:
    """
    Uygulama dependency facade'i.
    Mevcut container attribute API'sini korurken wiring sorumluluğunu küçük factory'lere böler.
    """

    def __init__(self, settings: AppSettings | None = None, event_bus=None):
        self.settings = settings or load_app_settings()
        self.db_config = self.settings.db
        self.event_bus = event_bus or GlobalEventBus()

        self.conn_provider = SQLAlchemyEngineProvider(self.db_config)

        self.repositories = build_repositories(self.conn_provider)
        self._expose_dataclass_fields(self.repositories)

        self.market_clients = build_market_clients(self.conn_provider)
        self._expose_dataclass_fields(self.market_clients)

        self.services = build_services(
            repositories=self.repositories,
            market_clients=self.market_clients,
            event_bus=self.event_bus,
        )
        self._expose_dataclass_fields(self.services)

        self.ai = build_ai(self.settings.ai)
        self._expose_dataclass_fields(self.ai)

    def _expose_dataclass_fields(self, group) -> None:
        for field in fields(group):
            setattr(self, field.name, getattr(group, field.name))
