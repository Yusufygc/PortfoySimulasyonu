"""
test_ai_advisor_phase10.py — Faz 10 Gemini AI Karar Destek Danışmanı QML test paketi.

Kapsam:
- AiAdvisorController ilklendirme, karşılama mesajı ve varsayılan özellikler
- Hızlı soru önerileri ve mesaj gönderme akışı
- Portföy Sağlık Skoru (0-100) ve 4 XAI faktörü hesaplama
- API anahtarı kaydetme ve durum geçişi
- AiAdvisorView.qml dosyasının QML motorunda hatasız derlenmesi
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

from src.ui_qml.controllers.ai_advisor_controller import AiAdvisorController
from src.ui_qml.controllers.chart_controller import ChartController
from src.ui_qml.controllers.comparison_controller import ComparisonController
from src.ui_qml.controllers.dashboard_controller import DashboardController
from src.ui_qml.controllers.market_sync_controller import MarketSyncController
from src.ui_qml.controllers.model_portfolio_controller import ModelPortfolioController
from src.ui_qml.controllers.optimization_controller import OptimizationController
from src.ui_qml.controllers.planning_controller import PlanningController
from src.ui_qml.controllers.screener_controller import ScreenerController
from src.ui_qml.controllers.shell_controller import ShellController
from src.ui_qml.controllers.stock_360_controller import Stock360Controller
from src.ui_qml.controllers.watchlist_controller import WatchlistController
from src.application.container import AppContainer


@pytest.fixture
def container():
    return AppContainer()


def test_ai_advisor_controller_initialization():
    """AiAdvisorController'ın varsayılan karşılama mesajı, model adı ve property'lerini test eder."""
    ctrl = AiAdvisorController(container=None)

    assert ctrl.modelName == "Gemini 2.5 Flash"
    assert ctrl.isLoading is False
    assert ctrl.statusMessage == "Hazır"
    assert len(ctrl.messages) >= 1
    assert ctrl.messages[0]["role"] == "ai"
    assert "Merhaba!" in ctrl.messages[0]["content"]
    assert len(ctrl.quickPrompts) == 4
    assert ctrl.portfolioHealthScore > 0
    assert ctrl.healthScoreLabel in ("Çok Güçlü", "Dengeli", "Orta Risk", "Yüksek Risk")


def test_ai_advisor_controller_send_message():
    """sendMessage çağrıldığında kullanıcı mesajının kuyruğa eklendiğini ve loading durumunun değiştiğini test eder."""
    ctrl = AiAdvisorController(container=None)

    initial_count = len(ctrl.messages)
    ctrl.sendMessage("Portföyümün risk seviyesi nedir?")

    # Kullanıcı mesajı listeye hemen eklenmelidir
    assert len(ctrl.messages) == initial_count + 1
    user_msg = ctrl.messages[-1]
    assert user_msg["role"] == "user"
    assert "Portföyümün risk seviyesi" in user_msg["content"]
    assert ctrl.isLoading is True


def test_ai_advisor_controller_quick_prompts():
    """sendQuickPrompt slotunun ilgili promptu başarıyla tetiklediğini test eder."""
    ctrl = AiAdvisorController(container=None)

    ctrl.sendQuickPrompt(0)  # "Portföy Risk Analizi"
    assert len(ctrl.messages) >= 2
    assert "genel risk ve getiri durumunu" in ctrl.messages[-1]["content"]


def test_ai_advisor_controller_clear_chat():
    """clearChat slotunun sohbet geçmişini sıfırlayıp sadece karşılama mesajını bıraktığını test eder."""
    ctrl = AiAdvisorController(container=None)

    ctrl.sendMessage("Deneme sorusu")
    assert len(ctrl.messages) >= 2

    ctrl.clearChat()
    assert len(ctrl.messages) == 1
    assert ctrl.messages[0]["role"] == "ai"


def test_ai_advisor_controller_health_score_calculation():
    """refreshHealthScore slotunun 4 alt XAI faktörünü ve genel puanı ürettiğini test eder."""
    mock_container = MagicMock()
    mock_advisor = MagicMock()
    mock_advisor.call_tool.return_value = {
        "top_three_weight_pct": 45.0,
        "volatility_pct": 24.5,
        "sharpe_ratio": 1.45,
        "max_drawdown_pct": 18.2,
    }
    mock_container.ai_advisor_service = mock_advisor

    ctrl = AiAdvisorController(container=mock_container)
    ctrl.refreshHealthScore()

    assert 0 <= ctrl.portfolioHealthScore <= 100
    assert len(ctrl.healthFactors) == 4
    factor_titles = [f["title"] for f in ctrl.healthFactors]
    assert "Varlık Çeşitliliği" in factor_titles
    assert "Volatilite & Risk" in factor_titles
    assert "Sharpe Rasyosu" in factor_titles
    assert "Maksimum Düşüş" in factor_titles


def test_ai_advisor_controller_save_api_key():
    """saveApiKey slotunun ayarları güncellediğini ve sistem mesajı eklediğini test eder."""
    mock_container = MagicMock()
    mock_settings = MagicMock()
    mock_settings.ai.gemini_api_key = ""
    mock_container.settings = mock_settings

    ctrl = AiAdvisorController(container=mock_container)
    assert ctrl.hasApiKey is False

    ctrl.saveApiKey("AIzaSyTEST_KEY_123456789")
    assert mock_settings.ai.gemini_api_key == "AIzaSyTEST_KEY_123456789"
    assert ctrl.hasApiKey is True
    assert any("Google Gemini API anahtarınız" in m["content"] for m in ctrl.messages)


def test_ai_advisor_qml_view_compilation(qapp, container):
    """AiAdvisorView.qml dosyasının QML motorunda hatasız derlendiğini test eder."""
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
    market_sync_ctrl = MarketSyncController(parent=engine)
    optimization_ctrl = OptimizationController(container=container, parent=engine)
    ai_advisor_ctrl = AiAdvisorController(container=container, parent=engine)

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
    ctx.setContextProperty("marketSyncController", market_sync_ctrl)
    ctx.setContextProperty("optimizationController", optimization_ctrl)
    ctx.setContextProperty("aiAdvisorController", ai_advisor_ctrl)

    qml_dir = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"
    engine.addImportPath(str(qml_dir))

    view_file = qml_dir / "views" / "AiAdvisorView.qml"
    assert view_file.exists(), f"{view_file} bulunamadı!"

    component = QQmlComponent(engine, QUrl.fromLocalFile(str(view_file)))
    if not component.isReady():
        errors = [err.toString() for err in component.errors()]
        pytest.fail(f"AiAdvisorView.qml derlenemedi:\n" + "\n".join(errors))

    item = component.create()
    assert item is not None, "AiAdvisorView item nesnesi oluşturulamadı!"
