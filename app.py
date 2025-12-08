import sys
from PyQt5.QtWidgets import QApplication

from config.settings_loader import load_settings
from src.infrastructure.db.mysql_connection import MySQLConnectionProvider
from src.infrastructure.db.portfolio_repository import MySQLPortfolioRepository
from src.infrastructure.db.price_repository import MySQLPriceRepository
from src.infrastructure.db.stock_repository import MySQLStockRepository
from src.infrastructure.market_data.yfinance_client import YFinanceMarketDataClient

from src.application.services.portfolio_service import PortfolioService
from src.application.services.price_update_service import PriceUpdateService
from src.application.services.return_calc_service import ReturnCalcService
from src.application.services.portfolio_update_coordinator import PortfolioUpdateCoordinator
from src.application.services.portfolio_reset_service import PortfolioResetService
from src.application.services.excel_export_service import ExcelExportService, ExportMode

from src.ui.style import apply_app_style
from src.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    apply_app_style(app)

    # 1) DB config & connection pool
    db_config = load_settings()
    conn_provider = MySQLConnectionProvider(db_config)

    # 2) Repositories
    portfolio_repo = MySQLPortfolioRepository(conn_provider)
    price_repo = MySQLPriceRepository(conn_provider)
    stock_repo = MySQLStockRepository(conn_provider)

    # 3) Market data client (yfinance)
    market_client = YFinanceMarketDataClient()

    # 4) Services
    portfolio_service = PortfolioService(portfolio_repo, price_repo)
    price_update_service = PriceUpdateService(price_repo, market_client)
    return_calc_service = ReturnCalcService(portfolio_repo, price_repo)
    reset_service = PortfolioResetService(portfolio_repo, price_repo, stock_repo)
    excel_export_service = ExcelExportService(
        portfolio_repo=portfolio_repo,
        price_repo=price_repo,
        stock_repo=stock_repo,
        market_data_client=market_client,
    )
    # 5) Coordinator
    coordinator = PortfolioUpdateCoordinator(
        portfolio_repo=portfolio_repo,
        stock_repo=stock_repo,
        price_update_service=price_update_service,
        return_calc_service=return_calc_service,
    )

    # 6) UI
    window = MainWindow(
        portfolio_service=portfolio_service,
        return_calc_service=return_calc_service,
        update_coordinator=coordinator,
        stock_repo=stock_repo,        # <--- EKLENDİ
        reset_service=reset_service, 
        market_client=market_client, 
        excel_export_service=excel_export_service,
    )
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
