"""WatchlistView.qml — gerçek WatchlistController ile uçtan uca yükleme testi (bkz. §9.5).

Kök nesne bir `Item` olduğundan pencere AÇILMAZ — headless güvenlidir.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.qt_compat.qtcore import QObject
from src.qt_compat.qtqml import QQmlApplicationEngine
from src.ui_qml.controllers.watchlist_controller import WatchlistController

_QML_FILE = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "qml" / "views" / "WatchlistView.qml"


def _make_empty_container() -> MagicMock:
    container = MagicMock()
    container.watchlist_service.get_all_watchlists.return_value = []
    container.watchlist_service.get_watchlist_stocks.return_value = []
    return container


@pytest.fixture
def loaded_engine(qapp):
    controller = WatchlistController(_make_empty_container())

    engine = QQmlApplicationEngine()
    warnings_seen = []
    engine.warnings.connect(lambda warns: warnings_seen.extend(warns))
    engine.rootContext().setContextProperty("watchlistController", controller)

    engine.load(str(_QML_FILE))

    yield engine, controller, warnings_seen
    engine.deleteLater()


def test_qml_file_exists():
    assert _QML_FILE.exists(), f"WatchlistView.qml bulunamadı: {_QML_FILE}"


def test_loads_without_warnings_and_creates_root_object(loaded_engine):
    engine, _controller, warnings_seen = loaded_engine

    assert engine.rootObjects(), "QML kök nesnesi oluşturulamadı"
    assert not warnings_seen, f"QML uyarı/hata verdi: {warnings_seen}"


def test_items_area_has_real_positive_geometry(loaded_engine):
    engine, _controller, _warnings = loaded_engine
    root = engine.rootObjects()[0]
    root.setProperty("width", 1280)
    root.setProperty("height", 800)

    items_area = root.findChild(QObject, "itemsArea")
    assert items_area is not None
    height = items_area.property("height")
    assert height == height  # NaN != NaN
    assert height > 0


def test_loads_with_populated_watchlist_too(qapp):
    """Boş değil, gerçek bir liste + hisse ile de hatasız yüklenmeli (Repeater'lar dolu)."""
    from datetime import date
    from decimal import Decimal
    from src.application.services.analysis.stock_360_service import StockOverview
    from src.domain.models.watchlist import Watchlist

    container = MagicMock()
    container.watchlist_service.get_all_watchlists.return_value = [Watchlist(id=1, name="Favoriler")]
    container.watchlist_service.get_watchlist_stocks.return_value = [
        {"item": None, "stock": None, "ticker": "AKBNK", "name": "Akbank"},
    ]
    container.stock_360_service.get_overview.return_value = StockOverview(
        ticker="AKBNK", last_price=Decimal("50"), last_price_date=date.today(),
        daily_change_pct=2.1, volume=1000, week52_low=Decimal("40"), week52_high=Decimal("60"),
    )
    controller = WatchlistController(container)

    engine = QQmlApplicationEngine()
    warnings_seen = []
    engine.warnings.connect(lambda warns: warnings_seen.extend(warns))
    engine.rootContext().setContextProperty("watchlistController", controller)
    engine.load(str(_QML_FILE))

    assert engine.rootObjects()
    assert not warnings_seen, f"QML uyarı/hata verdi: {warnings_seen}"
