from __future__ import annotations

from typing import Optional

from src.domain.ports.repositories.i_app_settings_repo import IAppSettingsRepository
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMAppSetting
from src.infrastructure.db.sqlalchemy.repositories._transaction import commit_or_rollback


class SQLAlchemyAppSettingsRepository(IAppSettingsRepository):
    def __init__(self, db_provider: SQLAlchemyEngineProvider) -> None:
        self._provider = db_provider

    def get(self, key: str) -> Optional[str]:
        with self._provider.get_session() as session:
            row = session.get(ORMAppSetting, key)
            return row.value if row else None

    def set(self, key: str, value: str) -> None:
        with self._provider.get_session() as session:
            row = session.get(ORMAppSetting, key)
            if row is None:
                session.add(ORMAppSetting(key=key, value=value))
            else:
                row.value = value
            commit_or_rollback(session)
