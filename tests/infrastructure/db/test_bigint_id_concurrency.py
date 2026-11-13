"""SQLite BIGINT kimlik ataması: iki bağlantı aynı anda kayıt eklerken kimlikler çakışmamalı (gerçek geçici veritabanı)."""
from __future__ import annotations

import threading
import time

from src.infrastructure.db.db_config import SQLiteConfig
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMStock


def test_concurrent_writers_get_distinct_ids(tmp_path):
    provider = SQLAlchemyEngineProvider(SQLiteConfig(db_path=str(tmp_path / "race.db")))
    session_a = provider._session_factory()
    session_b = provider._session_factory()
    errors: list[Exception] = []
    second_writer_started = threading.Event()

    session_a.add(ORMStock(ticker="AAA", name="A"))
    session_a.flush()  # A yazma kilidini tutar ve henüz commit etmemiştir

    def second_writer() -> None:
        try:
            second_writer_started.set()
            session_b.add(ORMStock(ticker="BBB", name="B"))
            session_b.flush()
            session_b.commit()
        except Exception as exc:  # noqa: BLE001 - testte hata nesnesi toplanır
            errors.append(exc)
            session_b.rollback()

    thread = threading.Thread(target=second_writer)
    thread.start()
    second_writer_started.wait(timeout=5)
    time.sleep(0.3)  # B'nin kimlik hesaplamasına (ve kilit beklemesine) ulaşması için kısa bekleme
    session_a.commit()
    thread.join(timeout=10)

    assert not errors, errors
    ids = sorted(row.id for row in provider._session_factory().query(ORMStock).all())
    assert ids == [1, 2]
    session_a.close()
    session_b.close()
    provider.dispose()
