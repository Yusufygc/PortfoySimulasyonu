from __future__ import annotations

import json
from typing import List

from src.domain.models.news_item import NewsScope, NewsSourceConfig, NewsSourceKind
from src.domain.ports.repositories.i_news_source_repo import INewsSourceRepository
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMNewsSource
from src.infrastructure.db.sqlalchemy.repositories._transaction import commit_or_rollback


def _to_domain(orm: ORMNewsSource) -> NewsSourceConfig:
    try:
        options = json.loads(orm.options_json or "{}")
    except ValueError:
        options = {}
    return NewsSourceConfig(
        source_id=orm.source_id,
        kind=NewsSourceKind(orm.kind),
        name=orm.name,
        enabled=bool(orm.enabled),
        language=orm.language,
        scope=NewsScope(orm.scope),
        url=orm.url or "",
        description=orm.description or "",
        is_custom=bool(orm.is_custom),
        options={str(k): str(v) for k, v in options.items()},
    )


def _apply(orm: ORMNewsSource, config: NewsSourceConfig) -> None:
    orm.kind = config.kind.value
    orm.name = config.name
    orm.enabled = config.enabled
    orm.language = config.language
    orm.scope = config.scope.value
    orm.url = config.url
    orm.description = config.description
    orm.is_custom = config.is_custom
    orm.options_json = json.dumps(dict(config.options), ensure_ascii=False)


class SQLAlchemyNewsSourceRepository(INewsSourceRepository):
    def __init__(self, db_provider: SQLAlchemyEngineProvider) -> None:
        self._provider = db_provider

    def list_sources(self) -> List[NewsSourceConfig]:
        with self._provider.get_session() as session:
            rows = session.query(ORMNewsSource).order_by(ORMNewsSource.sort_order, ORMNewsSource.source_id).all()
            return [_to_domain(row) for row in rows]

    def save_source(self, config: NewsSourceConfig) -> None:
        with self._provider.get_session() as session:
            row = session.get(ORMNewsSource, config.source_id)
            if row is None:
                next_order = session.query(ORMNewsSource).count()
                row = ORMNewsSource(source_id=config.source_id, sort_order=next_order)
                session.add(row)
            _apply(row, config)
            commit_or_rollback(session)

    def delete_source(self, source_id: str) -> None:
        with self._provider.get_session() as session:
            row = session.get(ORMNewsSource, source_id)
            if row is not None:
                session.delete(row)
                commit_or_rollback(session)
