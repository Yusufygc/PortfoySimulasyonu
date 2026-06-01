import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWebEngineWidgets import QWebEngineView

from src.infrastructure.logging.logger_setup import setup_logger, setup_global_exception_handler
from src.application.container import AppContainer

from src.ui.theme_manager import ThemeManager
from src.ui.main_window import MainWindow

def main():
    logger = setup_logger()
    setup_global_exception_handler()
    logger.info("Uygulama başlatılıyor...")

    app = QApplication(sys.argv)

    # Global mouse scroll filtresini yükle
    from src.ui.shared.event_filters import GlobalWheelEventFilter
    wheel_filter = GlobalWheelEventFilter(app)
    app.installEventFilter(wheel_filter)

    # Kayıtlı tema tercihini yükle (varsayılan: "dark")
    ThemeManager.apply_theme(app)

    # Container yapısını başlat (Bütün repo ve servisler içinde ayağa kalkar)
    container = AppContainer()

    # 6) UI
    window = MainWindow(container=container)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
