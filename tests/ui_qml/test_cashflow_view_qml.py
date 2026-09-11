"""CashflowView.qml — gerçek CashflowController ile uçtan uca yükleme testi
(bkz. §7.3 madde 8, d6).

Kök nesne bir `Item` olduğundan pencere AÇILMAZ — headless güvenlidir. Doğrulanan:
3 sekme (Bütçe/Hedefler/Nakit Hareketleri) + form girdileri + context property
(`cashflowController`) binding'leri hatasız çalışıyor; `tabContent` gerçek
(NaN/negatif olmayan) geometriye sahip (bkz. Stock360View'daki NaN-yükseklik
regresyonu, aynı sınıf hatayı burada da önceden yakalamak için). Boş durum
(hiç bütçe/hedef/hareket yok) ve doldurulmuş durum ayrı test edilir.
"""
from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.domain.models.budget import Budget, BudgetItem, BudgetPinnedItem
from src.domain.models.cash_movement import CashMovement
from src.domain.models.financial_goal import FinancialGoal
from src.qt_compat.qtcore import QObject
from src.qt_compat.qtqml import QQmlApplicationEngine
from src.ui_qml.controllers.cashflow_controller import CashflowController

_QML_FILE = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "qml" / "views" / "CashflowView.qml"


def _load(controller):
    engine = QQmlApplicationEngine()
    warnings_seen = []
    engine.warnings.connect(lambda warns: warnings_seen.extend(warns))
    engine.rootContext().setContextProperty("cashflowController", controller)
    engine.load(str(_QML_FILE))
    return engine, warnings_seen


def test_qml_file_exists():
    assert _QML_FILE.exists(), f"CashflowView.qml bulunamadı: {_QML_FILE}"


def _empty_container() -> MagicMock:
    container = MagicMock()
    container.planning_service.get_budget_for_month.return_value = None
    container.planning_service.get_budget_draft_from_pinned_items.return_value = Budget(
        id=None, month="2026-09", savings_target=Decimal("0"), items=[],
    )
    container.planning_service.get_pinned_budget_items.return_value = []
    container.planning_service.get_all_goals.return_value = []
    container.cash_movement_service.get_movements.return_value = []
    container.cash_movement_service.get_cash_balance.return_value = Decimal("0")
    return container


class TestEmptyState:
    @pytest.fixture
    def loaded_engine(self, qapp):
        controller = CashflowController(_empty_container())
        engine, warnings_seen = _load(controller)
        yield engine, controller, warnings_seen
        engine.deleteLater()

    def test_loads_without_warnings(self, loaded_engine):
        engine, _controller, warnings_seen = loaded_engine
        assert engine.rootObjects(), "QML kök nesnesi oluşturulamadı"
        assert not warnings_seen, f"QML uyarı/hata verdi: {warnings_seen}"

    def test_tab_content_has_real_positive_geometry(self, loaded_engine):
        engine, _controller, _warnings = loaded_engine
        root = engine.rootObjects()[0]
        root.setProperty("width", 1280)
        root.setProperty("height", 800)

        tab_content = root.findChild(QObject, "tabContent")
        assert tab_content is not None
        height = tab_content.property("height")
        assert height == height  # NaN != NaN
        assert height > 0


class TestWithData:
    @pytest.fixture
    def loaded_engine(self, qapp):
        container = MagicMock()
        budget = Budget(
            id=1, month=date.today().strftime("%Y-%m"), savings_target=Decimal("2000"),
            items=[
                BudgetItem(id=None, budget_id=None, item_type="income", name="Maaş", amount=Decimal("30000")),
                BudgetItem(id=None, budget_id=None, item_type="expense", name="Kira", amount=Decimal("10000")),
            ],
        )
        container.planning_service.get_budget_for_month.return_value = budget
        container.planning_service.get_budget_draft_from_pinned_items.return_value = budget
        container.planning_service.get_pinned_budget_items.return_value = [
            BudgetPinnedItem(id=1, item_type="expense", name="Kira", default_amount=Decimal("10000")),
        ]
        container.planning_service.get_all_goals.return_value = [
            FinancialGoal(
                id=1, name="Araba", target_amount=Decimal("100000"), current_amount=Decimal("20000"),
                deadline=date(2027, 1, 1), priority="HIGH", status="ACTIVE",
            ),
        ]
        container.cash_movement_service.get_movements.return_value = [
            CashMovement.create_deposit(amount=Decimal("10000"), movement_date=date(2026, 1, 5), movement_time=time(10, 0), notes="ilk yatırım"),
        ]
        container.cash_movement_service.get_cash_balance.return_value = Decimal("10000")

        controller = CashflowController(container)
        engine, warnings_seen = _load(controller)
        yield engine, controller, warnings_seen
        engine.deleteLater()

    def test_loads_without_warnings(self, loaded_engine):
        engine, _controller, warnings_seen = loaded_engine
        assert engine.rootObjects(), "QML kök nesnesi oluşturulamadı"
        assert not warnings_seen, f"QML uyarı/hata verdi: {warnings_seen}"

    def test_tab_content_has_real_positive_geometry(self, loaded_engine):
        engine, _controller, _warnings = loaded_engine
        root = engine.rootObjects()[0]
        root.setProperty("width", 1280)
        root.setProperty("height", 800)

        tab_content = root.findChild(QObject, "tabContent")
        assert tab_content is not None
        height = tab_content.property("height")
        assert height == height  # NaN != NaN
        assert height > 0
