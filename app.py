import sys

from src.qt_compat.scaling import configure_qt_scale_normalization

configure_qt_scale_normalization()

from src.qt_compat.qtcore import QCoreApplication, Qt

from src.infrastructure.logging.logger_setup import setup_logger, setup_global_exception_handler


def configure_qt_application_attributes():
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)


def main():
    logger = setup_logger()
    setup_global_exception_handler()
    logger.info("Uygulama başlatılıyor...")

    configure_qt_application_attributes()

    from src.ui_qml.app import run_qml_app

    container = None
    try:
        from src.application.container import AppContainer
        container = AppContainer()
    except Exception as exc:
        logger.warning("Veritabanı bağlantısı sağlanamadı (%s). Arayüz çevrimdışı modda devam ediyor.", exc)

    sys.exit(run_qml_app(container=container))


if __name__ == "__main__":
    main()
