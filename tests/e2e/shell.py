"""Gerçek uygulama kabuğunu (AppContainer + build_ui + Main.qml) yalıtılmış test veritabanıyla kurar.

Test veritabanı: boş şemadan başlayan taze SQLite (kişisel veri yok) + `data/market_history.duckdb` piyasa geçmişi kopyası
(kişisel olmayan referans veri; yoksa boş DuckDB). Gerçek dosyalara yazılmaz. Ağ soket düzeyinde kapatılır; uygulama,
internet yokmuş gibi davranır (gerçek kullanıcıdaki çevrimdışı durumla aynı yollar çalışır).
"""
from __future__ import annotations

import os
import shutil
import socket
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, Tuple

ROOT = Path(__file__).resolve().parents[2]
QML_MAIN = ROOT / "src" / "ui_qml" / "qml" / "Main.qml"


def prepare_test_db(work: Path, copy_market_history: bool = True) -> Tuple[Path, Path]:
    """`work` içinde taze portfolio.db yolu ve (varsa) piyasa geçmişi kopyasını hazırlar."""
    work.mkdir(parents=True, exist_ok=True)
    sqlite_path = work / "portfolio.db"
    duck_path = work / "market_history.duckdb"
    for suffix in ("", "-wal", "-shm"):
        (work / f"portfolio.db{suffix}").unlink(missing_ok=True)
    real_duck = ROOT / "data" / "market_history.duckdb"
    if copy_market_history and real_duck.exists() and not duck_path.exists():
        shutil.copy2(real_duck, duck_path)
    return sqlite_path, duck_path


@contextmanager
def network_blocked() -> Iterator[None]:
    """Yerel olmayan her soket bağlantısını anında reddeder (gerçek ağa çıkış olmaz)."""
    original_connect = socket.socket.connect
    original_create = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    def _is_local(address) -> bool:
        host = address[0] if isinstance(address, tuple) else str(address)
        return host in ("127.0.0.1", "localhost", "::1", "0.0.0.0") or str(host).startswith("127.")

    def connect(self, address):
        if not _is_local(address):
            raise OSError("E2E: ağ kapalı")
        return original_connect(self, address)

    def create_connection(address, *args, **kwargs):
        if not _is_local(address):
            raise OSError("E2E: ağ kapalı")
        return original_create(address, *args, **kwargs)

    def getaddrinfo(host, *args, **kwargs):
        if not _is_local((host,)):
            raise socket.gaierror("E2E: ağ kapalı")
        return original_getaddrinfo(host, *args, **kwargs)

    socket.socket.connect = connect
    socket.create_connection = create_connection
    socket.getaddrinfo = getaddrinfo
    restore_libraries = _block_native_http_libraries()
    try:
        yield
    finally:
        restore_libraries()
        socket.socket.connect = original_connect
        socket.create_connection = original_create
        socket.getaddrinfo = original_getaddrinfo


def _block_native_http_libraries():
    """yfinance curl_cffi (C düzeyi soket) kullanır; Python soket yaması onu durdurmaz. Kütüphane girişlerini keser."""
    import yfinance

    def offline(*_args, **_kwargs):
        raise ConnectionError("E2E: ağ kapalı")

    saved = {name: getattr(yfinance, name) for name in ("download", "Ticker", "Tickers", "Search") if hasattr(yfinance, name)}
    for name in saved:
        setattr(yfinance, name, offline)

    def restore():
        for name, value in saved.items():
            setattr(yfinance, name, value)

    return restore


def build_shell(sqlite_path: Path, duck_path: Path, size=(1440, 900)):
    """(app, engine, controllers, container) döndürür; Main.qml yüklenmiş ve gösterilmiş olur."""
    os.environ["DB_SQLITE_PATH"] = str(sqlite_path)
    os.environ["DUCKDB_PATH"] = str(duck_path)
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuick import QQuickWindow
    from PySide6.QtWebEngineQuick import QtWebEngineQuick
    from PySide6.QtWidgets import QApplication

    from config.settings_loader import load_app_settings
    from src.application.container import AppContainer
    from src.infrastructure.db.paths import duckdb_path
    from src.ui_qml.app import build_ui

    # QSettings (son güncelleme, sohbet geçmişi, tema) gerçek kullanıcı kayıt defterine yazmasın: test klasöründe INI.
    from src.qt_compat.user_settings import use_ini_file

    use_ini_file(str(sqlite_path.parent / "qsettings.ini"))
    assert Path(load_app_settings().db.db_path).resolve() == sqlite_path.resolve(), "SQLite yolu test kopyası değil"
    assert Path(duckdb_path()).resolve() == duck_path.resolve(), "DuckDB yolu test kopyası değil"

    QtWebEngineQuick.initialize()
    app = QApplication.instance() or QApplication([])
    container = AppContainer()
    engine = QQmlApplicationEngine()
    engine.warnings.connect(lambda warns: _WARNINGS.extend(w.toString() for w in warns))
    controllers: Dict = build_ui(engine, container, autostart=False)
    engine.load(QUrl.fromLocalFile(str(QML_MAIN)))
    assert engine.rootObjects(), f"Main.qml yüklenemedi: {_WARNINGS[-5:]}"
    window = engine.rootObjects()[0]
    if isinstance(window, QQuickWindow):
        window.resize(*size)
        window.show()
        window.requestActivate()
    return app, engine, controllers, container


_WARNINGS: list = []


def qml_warnings() -> list:
    """Yüklenme sırasında ve sonrasında QML motorunun bildirdiği tüm uyarılar (bağlama hatası, null erişim vb.)."""
    return list(_WARNINGS)
