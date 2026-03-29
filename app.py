import sys
from PyQt5.QtWidgets import QApplication

from src.infrastructure.logging.logger_setup import setup_logger, setup_global_exception_handler
from src.application.container import AppContainer

from src.ui.theme_manager import ThemeManager
from src.ui.main_window import MainWindow

def main():
    logger = setup_logger()
    setup_global_exception_handler()
    logger.info("Uygulama başlatılıyor...")

    app = QApplication(sys.argv)
    
    # Yeni modüler Tema Yöneticisi
    ThemeManager.apply_theme(app, "dark_theme")

    # Container yapısını başlat (Bütün repo ve servisler içinde ayağa kalkar)
    container = AppContainer()

    # 6) UI
    window = MainWindow(container=container)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
