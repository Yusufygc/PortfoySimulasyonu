"""
Faz 8 Finansal Planlama, Bütçe, Hedefler ve DCA Simülasyonu Doğrulama Testi.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineQuick import QtWebEngineQuick

from src.application.container import AppContainer
from src.ui_qml.controllers.shell_controller import ShellController
from src.ui_qml.controllers.chart_controller import ChartController
from src.ui_qml.controllers.dashboard_controller import DashboardController
from src.ui_qml.controllers.watchlist_controller import WatchlistController
from src.ui_qml.controllers.stock_360_controller import Stock360Controller
from src.ui_qml.controllers.model_portfolio_controller import ModelPortfolioController
from src.ui_qml.controllers.comparison_controller import ComparisonController
from src.ui_qml.controllers.screener_controller import ScreenerController
from src.ui_qml.controllers.planning_controller import PlanningController


@pytest.fixture(scope="session")
def qapp():
    QtWebEngineQuick.initialize()
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def container():
    return AppContainer()


def test_planning_controller_initialization(qapp, container):
    """PlanningController'ın başlatılmasını ve varsayılan alanlarını test eder."""
    ctrl = PlanningController(container=container)
    assert ctrl.currentMonth != ""
    assert isinstance(ctrl.totalIncomeFormatted, str)
    assert isinstance(ctrl.totalExpenseFormatted, str)
    assert isinstance(ctrl.netSavingsPotentialFormatted, str)
    assert isinstance(ctrl.incomeItems, list)
    assert isinstance(ctrl.expenseItems, list)
    assert isinstance(ctrl.goalsList, list)
    assert not ctrl.dcaIsRunning
    assert isinstance(ctrl.dcaSharesList, list)


def test_planning_budget_item_operations(qapp, container):
    """Bütçeye kalem ekleme, çıkarma, pinleme ve hesaplama döngüsünü test eder."""
    ctrl = PlanningController(container=container)

    # availableMonths kontrolü
    assert len(ctrl.availableMonths) > 0
    assert ctrl.currentMonth in ctrl.availableMonths

    initial_inc_count = len(ctrl.incomeItems)
    ctrl.addBudgetItem("INCOME", "Test Gelir", 15000.0)
    assert len(ctrl.incomeItems) == initial_inc_count + 1

    initial_exp_count = len(ctrl.expenseItems)
    ctrl.addBudgetItem("EXPENSE", "Test Gider", 5000.0)
    assert len(ctrl.expenseItems) == initial_exp_count + 1

    assert ctrl.netSavingsPotential >= 10000.0

    # Pinleme mekanizması testi
    ctrl.togglePinItem("INCOME", "Test Gelir", 15000.0, True)
    # Tekrar çağrıldığında kaldırılması (toggle)
    ctrl.togglePinItem("INCOME", "Test Gelir", 15000.0, False)

    # Kalem düzenleme (updateBudgetItem) testi
    last_idx = len(ctrl.incomeItems) - 1
    ctrl.updateBudgetItem("INCOME", last_idx, "Guncellenmis Gelir", 22000.0)
    assert ctrl.incomeItems[last_idx]["name"] == "Guncellenmis Gelir"
    assert ctrl.incomeItems[last_idx]["amount"] == 22000.0

    # Kalem silme
    ctrl.removeBudgetItem("INCOME", len(ctrl.incomeItems) - 1)
    assert len(ctrl.incomeItems) == initial_inc_count

    # Backend PlanningService update_budget_item testi
    if ctrl._service:
        test_month = "2099-12"
        updated_budget = ctrl._service.update_budget_item(
            month=test_month,
            old_name="Eski Kalem",
            new_name="Servis Guncel Gelir",
            new_amount=25000.0,
            item_type="INCOME",
        )
        assert updated_budget is not None
        matched = next((i for i in updated_budget.items if i.name == "Servis Guncel Gelir"), None)
        assert matched is not None
        assert float(matched.amount) == 25000.0
        if updated_budget.id:
            ctrl._service.delete_budget(updated_budget.id)


def test_planning_goals_lifecycle(qapp, container):
    """Hedef oluşturma, güncelleme, katkı ekleme ve silme döngüsünü test eder."""
    ctrl = PlanningController(container=container)

    goal_name = "FZ8_TEST_HEDEF"
    ctrl.addGoal(goal_name, 50000.0, "2027-12-31", "HIGH")
    ctrl.loadGoals()

    created = next((g for g in ctrl.goalsList if g["name"] == goal_name), None)
    assert created is not None
    goal_id = created["id"]
    assert created["targetAmount"] == 50000.0

    # Hedef güncelleme testi
    ctrl.updateGoal(goal_id, "FZ8_TEST_HEDEF_GUNCELLENDI", 75000.0, "2028-06-30", "MEDIUM")
    ctrl.loadGoals()
    updated_goal = next((g for g in ctrl.goalsList if g["id"] == goal_id), None)
    assert updated_goal is not None
    assert updated_goal["name"] == "FZ8_TEST_HEDEF_GUNCELLENDI"
    assert updated_goal["targetAmount"] == 75000.0
    assert updated_goal["deadline"] == "2028-06-30"

    # Katkı ekleme
    ctrl.addContribution(goal_id, 10000.0)
    ctrl.loadGoals()
    updated = next((g for g in ctrl.goalsList if g["id"] == goal_id), None)
    assert updated is not None
    assert updated["currentAmount"] >= 10000.0

    # Silme
    ctrl.deleteGoal(goal_id)
    ctrl.loadGoals()
    deleted = next((g for g in ctrl.goalsList if g["id"] == goal_id), None)
    assert deleted is None


def test_planning_dca_backtest_execution(qapp, container):
    """DCA simülasyon servisi çağrısını test eder."""
    ctrl = PlanningController(container=container)
    ctrl._execute_dca(["ALARK"], Decimal("1000"), date(2023, 1, 1), date(2023, 6, 1))

    assert ctrl.dcaContributionCount > 0
    assert ctrl.dcaTotalInvested != "0,00 ₺"
    assert ctrl.dcaFinalValue != "0,00 ₺"
    assert len(ctrl.dcaSharesList) > 0
    assert ctrl.dcaChartHtml != ""


def test_planning_qml_view_compilation(qapp, container):
    """PlanningView.qml dosyasının QML motorunda hatasız derlendiğini test eder."""
    engine = QQmlApplicationEngine()

    shell_ctrl = ShellController(container=container, parent=engine)
    chart_ctrl = ChartController(container=container, parent=engine)
    dash_ctrl = DashboardController(container=container, parent=engine)
    watchlist_ctrl = WatchlistController(container=container, parent=engine)
    stock_360_ctrl = Stock360Controller(container=container, parent=engine)
    portfolio_ctrl = ModelPortfolioController(container=container, parent=engine)
    comparison_ctrl = ComparisonController(container=container, parent=engine)
    screener_ctrl = ScreenerController(container=container, parent=engine)
    planning_ctrl = PlanningController(container=container, parent=engine)

    ctx = engine.rootContext()
    ctx.setContextProperty("shellController", shell_ctrl)
    ctx.setContextProperty("chartController", chart_ctrl)
    ctx.setContextProperty("dashboardController", dash_ctrl)
    ctx.setContextProperty("watchlistController", watchlist_ctrl)
    ctx.setContextProperty("stock360Controller", stock_360_ctrl)
    ctx.setContextProperty("portfolioController", portfolio_ctrl)
    ctx.setContextProperty("comparisonController", comparison_ctrl)
    ctx.setContextProperty("screenerController", screener_ctrl)
    ctx.setContextProperty("planningController", planning_ctrl)

    qml_dir = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"
    engine.addImportPath(str(qml_dir))

    view_file = qml_dir / "views" / "PlanningView.qml"
    assert view_file.exists(), f"{view_file} bulunamadı!"

    component = QQmlComponent(engine, QUrl.fromLocalFile(str(view_file)))
    if not component.isReady():
        errors = [err.toString() for err in component.errors()]
        pytest.fail(f"PlanningView.qml derlenemedi:\n" + "\n".join(errors))

    item = component.create()
    assert item is not None, "PlanningView item nesnesi oluşturulamadı!"
