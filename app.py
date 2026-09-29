import os
import sys

from src.qt_compat.scaling import configure_qt_scale_normalization

configure_qt_scale_normalization()

from src.qt_compat.qtcore import QCoreApplication, Qt
from src.qt_compat.qtwidgets import QApplication

from src.infrastructure.logging.logger_setup import setup_logger, setup_global_exception_handler


def configure_qt_application_attributes():
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)


def main():
    configure_qt_application_attributes()

    from src.application.container import AppContainer
    from src.ui.theme_manager import ThemeManager
    from src.ui.main_window import MainWindow

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
    ThemeManager.connect_system_theme(app)

    # Container yapısını başlat (Bütün repo ve servisler içinde ayağa kalkar)
    container = AppContainer()

    # UI Seçimi: --ui=qml veya normal Widgets
    if "--ui=qml" in sys.argv or os.environ.get("PORTFOYSIM_UI") == "qml":
        from src.ui_qml.app import run_qml_app
        logger.info("QML arayüz modu seçildi (--ui=qml).")
        sys.exit(run_qml_app(container=container))

    # 6) Klasik UI (Qt Widgets)
    window = MainWindow(container=container)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
