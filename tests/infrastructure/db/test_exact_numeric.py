"""SQLite `REAL` depolaması: float'a çevrilince değer değişecekse yazma sessizce bozulmak yerine reddedilir."""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import Column, Integer, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.infrastructure.db.sqlalchemy.exact_numeric import ExactNumeric

Base = declarative_base()


class Row(Base):
    __tablename__ = "exact_numeric_rows"
    id = Column(Integer, primary_key=True)
    quantity = Column(ExactNumeric(28, 10))
    price = Column(ExactNumeric(18, 4))


@pytest.fixture()
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        yield db


@pytest.mark.parametrize("quantity, price", [
    (Decimal("0.1234567891"), Decimal("123.4567")),
    (Decimal("1000000"), Decimal("99999999.9999")),
    (Decimal("0"), Decimal("0.0001")),
    (Decimal("123456.1234567891"), Decimal("250.1")),
    (None, None),
])
def test_values_that_survive_float_storage_round_trip_exactly(session, quantity, price):
    session.add(Row(id=1, quantity=quantity, price=price))
    session.commit()
    session.expire_all()

    row = session.get(Row, 1)
    assert row.quantity == quantity and row.price == price


def test_value_that_float_storage_would_corrupt_is_rejected(session):
    session.add(Row(id=1, quantity=Decimal("12345678901234.1234567891")))

    with pytest.raises(Exception, match="kesinlik|float"):
        session.commit()


def test_extra_digits_beyond_scale_are_allowed_because_the_column_rounds_them_anyway(session):
    session.add(Row(id=1, price=Decimal("10.123456789")))
    session.commit()
    session.expire_all()

    assert session.get(Row, 1).price == Decimal("10.1235")


def test_integers_and_floats_are_accepted(session):
    session.add(Row(id=1, quantity=5, price=2.5))
    session.commit()
    session.expire_all()

    row = session.get(Row, 1)
    assert row.quantity == Decimal("5") and row.price == Decimal("2.5")
