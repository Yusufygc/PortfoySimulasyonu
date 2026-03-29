import sys
from PyQt5.QtWidgets import QApplication

from src.infrastructure.logging.logger_setup import setup_logger, setup_global_exception_handler
from src.application.container import AppContainer

from src.ui.style import apply_app_style
from src.ui.main_window import MainWindow


def main():
    logger = setup_logger()
    setup_global_exception_handler()
    logger.info("Uygulama başlatılıyor...")

    app = QApplication(sys.argv)
    apply_app_style(app)

    # Container yapısını başlat (Bütün repo ve servisler içinde ayağa kalkar)
    container = AppContainer()

    # 6) UI
    window = MainWindow(container=container)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
