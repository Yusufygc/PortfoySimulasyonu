# src/infrastructure/logging/logger_setup.py

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

def setup_logger():
    """
    Sistemin genel loglama konfigürasyonunu yapar.
    Terminal (Console) ve 'app.log' dosyasına eşzamanlı yazar.
    """
    # Kök logger'ı yapılandır (En düşük seviye DEBUG/INFO)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Formatlayıcı
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Dosya İşleyicisi (RotatingFileHandler - 5MB, 5 Ydek)
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    log_file = os.path.join(log_dir, 'app.log')
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # Konsol İşleyicisi (StreamHandler)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)  # Konsolda daha fazla detay istenebilir
    console_handler.setFormatter(formatter)

    # Varsa eski handler'ları temizle (Çift yazmayı engeller)
    if logger.hasHandlers():
        logger.handlers.clear()

    # Log mekanizmalarını ekle
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

def handle_exception(exc_type, exc_value, exc_traceback):
    """
    Yakalanmayan (Unhandled) hataların programa sessizce çökmesi
    yerine loglanmasını sağlayan global hook fonksiyonu.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        # KeyboardInterrupt'i (Ctrl+C) normal akışta bırak
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger = logging.getLogger("UnhandledException")
    logger.critical("Kritik Hata (Unhandled exception)", exc_info=(exc_type, exc_value, exc_traceback))

def setup_global_exception_handler():
    """
    Python'un yerleşik exception hook'una loglamayı bağlar.
    """
    sys.excepthook = handle_exception
