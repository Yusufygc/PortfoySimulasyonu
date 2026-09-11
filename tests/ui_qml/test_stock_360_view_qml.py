"""Stock360View.qml — gerçek Stock360Controller ile uçtan uca yükleme testi (bkz. §7.3).

Kök nesne bir `Item` (Window değil) olduğundan pencere AÇILMAZ — headless güvenlidir
(bkz. d0'daki `LineChartPoc.qml` testiyle aynı desen). Doğrulanan: `TabBar` +
`CandlestickChartItem`/`LineChartItem` + arama kutusu + context property binding'leri
hatasız çalışıyor.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.application.services.analysis.stock_360_service import StockOverview, TechnicalLevels
from src.domain.models.daily_price import DailyPrice
from src.domain.models.shareholder import ShareholderRow, ShareholderSnapshot
from src.domain.models.stock import Stock
from src.qt_compat.qtcore import QObject
from src.qt_compat.qtqml import QQmlApplicationEngine, qmlRegisterType
from src.ui_qml.charts.candlestick_chart_item import CandlestickChartItem
from src.ui_qml.charts.line_chart_item import LineChartItem
from src.ui_qml.controllers.stock_360_controller import Stock360Controller

_QML_FILE = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "qml" / "views" / "Stock360View.qml"

_types_registered = False


def _ensure_types_registered() -> None:
    global _types_registered
    if not _types_registered:
        qmlRegisterType(LineChartItem, "PortfoyCharts", 1, 0, "LineChartItem")
        qmlRegisterType(CandlestickChartItem, "PortfoyCharts", 1, 0, "CandlestickChartItem")
        _types_registered = True


def _rows(n: int, start: date):
    rows = []
    for i in range(n):
        close = 100.0 + i * 0.1
        rows.append(DailyPrice(
            id=None, stock_id=1, price_date=start + timedelta(days=i),
            close_price=Decimal(str(round(close, 2))),
            open_price=Decimal(str(round(close - 1, 2))),
            high_price=Decimal(str(round(close + 2, 2))),
            low_price=Decimal(str(round(close - 2, 2))),
            volume=1000 + i,
        ))
    return rows


def _make_container() -> MagicMock:
    container = MagicMock()
    container.stock_repo.get_stock_by_ticker.return_value = Stock(id=1, ticker="AKBNK", name="AKBNK", currency_code="TRY")
    container.price_repo.get_price_series.return_value = _rows(400, date.today() - timedelta(days=400))

    container.stock_360_service.get_overview.return_value = StockOverview(
        ticker="AKBNK", last_price=Decimal("120"), last_price_date=date.today(),
        daily_change_pct=1.5, volume=1000, week52_low=Decimal("90"), week52_high=Decimal("150"),
    )
    container.stock_360_service.get_technical_levels.return_value = TechnicalLevels(
        ticker="AKBNK", rsi14=55.0, macd_line=0.5, macd_signal=0.3,
        sma50=110.0, sma200=100.0, ema20=115.0, support=105.0, resistance=125.0,
    )
    container.stock_360_service.get_financials.return_value = {
        "periods": ["2026/6"],
        "_market_val": {"fk": 5.2, "pddd": 1.1, "ev_favok": 3.9},
        "roe": {"2026/6": 32.0},
    }
    container.stock_360_service.get_shareholders.return_value = [
        ShareholderSnapshot(
            creation_date=date.today(),
            rows=(ShareholderRow("Kurucu Aile", Decimal("4000"), Decimal("40"), Decimal("40")),),
        )
    ]
    return container


@pytest.fixture
def loaded_engine(qapp):
    _ensure_types_registered()
    controller = Stock360Controller(_make_container())
    controller.loadTicker("AKBNK")

    engine = QQmlApplicationEngine()
    warnings_seen = []
    engine.warnings.connect(lambda warns: warnings_seen.extend(warns))
    engine.rootContext().setContextProperty("stock360Controller", controller)

    engine.load(str(_QML_FILE))

    yield engine, controller, warnings_seen
    engine.deleteLater()


def test_qml_file_exists():
    assert _QML_FILE.exists(), f"Stock360View.qml bulunamadı: {_QML_FILE}"


def test_loads_without_warnings_and_creates_root_object(loaded_engine):
    engine, _controller, warnings_seen = loaded_engine

    assert engine.rootObjects(), "QML kök nesnesi oluşturulamadı"
    assert not warnings_seen, f"QML uyarı/hata verdi: {warnings_seen}"


def test_tab_content_area_has_real_positive_geometry(loaded_engine):
    """Regresyon testi: `tabContent`'in yüksekliği NaN/0'a düşerse (bkz. var olmayan
    bir property'ye referans veren bir binding — QML bunu her zaman `warnings`
    sinyaliyle bildirmez, sessizce NaN yükseklik üretebilir) sekme içeriği görünmez
    olur ama önceki test hâlâ 'yeşil' kalırdı. Bu test gerçek geometriyi kontrol eder."""
    engine, _controller, _warnings = loaded_engine
    root = engine.rootObjects()[0]
    # `root`'un `anchors.fill: parent`'i gerçek uygulamada bir Window/Loader'a bağlanır;
    # burada (bağımsız yükleme, hiçbir üst öğe yok) root'a elle boyut vermek gerekir —
    # aksi halde root.width/height 0 kalır ve tüm iç anchor'lar yanlış (negatif) geometri üretir.
    root.setProperty("width", 1280)
    root.setProperty("height", 800)

    tab_content = root.findChild(QObject, "tabContent")
    assert tab_content is not None, "tabContent nesnesi bulunamadı"
    height = tab_content.property("height")
    assert height == height  # NaN != NaN -> bu satır NaN'ı yakalar
    assert height > 0
