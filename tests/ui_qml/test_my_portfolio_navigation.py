"""Portföyüm sayfası yönlendirmesi: Genel Bakış'tan ayrılan portföy sayfası kabukta kayıtlıdır."""
from __future__ import annotations

from pathlib import Path

from src.ui_qml.controllers.shell_controller import ShellController

QML_DIR = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "qml"
MY_PORTFOLIO_PAGE = 10


def test_shell_navigates_to_my_portfolio_page():
    shell = ShellController()

    shell.navigateTo(MY_PORTFOLIO_PAGE)

    assert shell.activePage == MY_PORTFOLIO_PAGE
    assert shell.pageTitle == "Portföyüm"


def test_dashboard_stays_first_page_so_chart_navigation_keeps_working():
    shell = ShellController()

    shell.navigateTo(MY_PORTFOLIO_PAGE)
    shell.navigateTo(0)

    assert shell.activePage == 0
    assert shell.pageTitle == "Ana Sayfa"


def test_main_qml_loads_my_portfolio_view_lazily_at_last_stack_index():
    main_qml = (QML_DIR / "Main.qml").read_text(encoding="utf-8")

    assert 'source: "views/MyPortfolioView.qml"' in main_qml
    assert "shellController.activePage === 10" in main_qml


def test_sidebar_lists_my_portfolio_right_after_dashboard():
    sidebar = (QML_DIR / "components" / "Sidebar.qml").read_text(encoding="utf-8")

    dashboard = sidebar.index("Strings.navDashboard")
    my_portfolio = sidebar.index("Strings.navMyPortfolio")
    watchlist = sidebar.index("Strings.navWatchlist")
    assert dashboard < my_portfolio < watchlist


def test_dashboard_view_no_longer_holds_portfolio_widgets():
    dashboard = (QML_DIR / "views" / "DashboardView.qml").read_text(encoding="utf-8")

    for forbidden in ("QuickTradeModal", "CapitalModal", "ExcelExportDialog", "positionsModel", "AssetAllocationCard"):
        assert forbidden not in dashboard
    assert "TradingViewChart" in dashboard
