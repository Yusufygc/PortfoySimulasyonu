"""QML görünümlerinin ofscreen ekran görüntülerini alır ve iki görüntü dizinini piksel piksel karşılaştırır.

Büyük QML yeniden düzenlemelerinde (bileşene bölme, taşıma) görsel eşdeğerliği kanıtlamak içindir. Gerçek veritabanlarına
dokunmaz: veri dosyaları geçici bir klasöre kopyalanır (SQLite için tutarlı yedekleme API'siyle).

Kullanım (depo kökünden):

    # Yeniden düzenlemeden ÖNCEKİ commit için ayrı bir çalışma ağacında
    git worktree add <geçici_dizin> <eski_commit>
    cd <geçici_dizin>
    <repo>\\venv\\Scripts\\python.exe <repo>\\scripts\\qml_visual_snapshot.py render <çıktı_eski>
    # Güncel kodda
    .\\venv\\Scripts\\python.exe scripts\\qml_visual_snapshot.py render <çıktı_yeni>
    # Karşılaştır (farklı piksel sayısı 0 olmalı)
    .\\venv\\Scripts\\python.exe scripts\\qml_visual_snapshot.py compare <çıktı_eski> <çıktı_yeni>

Notlar: ofscreen ortamda yazı tipleri kutu olarak çizilir (yerleşim ve renk karşılaştırılır, metin biçimi değil);
asenkron yüklenen içerik çalıştırmadan çalıştırmaya küçük farklar verebilir, şüpheli farkı aynı kodla iki kez çalıştırıp
gürültü tabanıyla kıyaslayın. `render` çalışma dizinindeki kodu (src/ui_qml) çizer.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path


def _prepare_environment(db_dir: Path | None) -> Path:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    sys.path.insert(0, os.getcwd())
    work = db_dir or Path(tempfile.mkdtemp(prefix="qml_snapshot_db_"))
    if db_dir is None:
        from src.infrastructure.db.paths import duckdb_path, sqlite_db_path

        real_sqlite, real_duck = sqlite_db_path(), duckdb_path()
        if real_sqlite.exists():
            source, destination = sqlite3.connect(real_sqlite), sqlite3.connect(work / "portfolio.db")
            try:
                source.backup(destination)
            finally:
                destination.close()
                source.close()
        if real_duck.exists():
            shutil.copy2(real_duck, work / "market_history.duckdb")
    os.environ["DB_SQLITE_PATH"] = str(work / "portfolio.db")
    os.environ["DUCKDB_PATH"] = str(work / "market_history.duckdb")
    return work


def _pump(count: int = 25) -> None:
    from PySide6.QtCore import QCoreApplication

    for _ in range(count):
        QCoreApplication.processEvents()
        time.sleep(0.02)


def _build_engine():
    from PySide6.QtQml import QQmlApplicationEngine

    from src.application.container import AppContainer
    from src.ui_qml.controllers import (
        ai_advisor_controller, chart_controller, comparison_controller, corporate_action_controller,
        dashboard_controller, dividend_controller, golden_cross_controller, market_adjustment_controller,
        market_sync_controller, market_ticker_controller, model_analysis_controller, model_portfolio_controller,
        optimization_controller, planning_controller, price_data_controller, risk_profile_controller,
        screener_controller, settings_controller, shell_controller, startup_jobs_controller, stock_360_controller,
        stock_detail_controller, strategy_backtest_controller, system_controller, watchlist_controller,
    )

    container = AppContainer()
    engine = QQmlApplicationEngine()
    classes = {
        "shellController": shell_controller.ShellController,
        "chartController": chart_controller.ChartController,
        "dashboardController": dashboard_controller.DashboardController,
        "watchlistController": watchlist_controller.WatchlistController,
        "stock360Controller": stock_360_controller.Stock360Controller,
        "portfolioController": model_portfolio_controller.ModelPortfolioController,
        "comparisonController": comparison_controller.ComparisonController,
        "screenerController": screener_controller.ScreenerController,
        "planningController": planning_controller.PlanningController,
        "strategyBacktestController": strategy_backtest_controller.StrategyBacktestController,
        "optimizationController": optimization_controller.OptimizationController,
        "aiAdvisorController": ai_advisor_controller.AiAdvisorController,
        "settingsController": settings_controller.SettingsController,
        "stockDetailController": stock_detail_controller.StockDetailController,
        "corporateActionController": corporate_action_controller.CorporateActionController,
        "dividendController": dividend_controller.DividendController,
        "priceDataController": price_data_controller.PriceDataController,
        "startupJobsController": startup_jobs_controller.StartupJobsController,
        "goldenCrossController": golden_cross_controller.GoldenCrossController,
        "riskProfileController": risk_profile_controller.RiskProfileController,
        "marketAdjustmentController": market_adjustment_controller.MarketAdjustmentController,
        "systemController": system_controller.SystemController,
        "marketTickerController": market_ticker_controller.MarketTickerController,
        "modelAnalysisController": model_analysis_controller.ModelAnalysisController,
    }
    controllers = {name: cls(container=container, parent=engine) for name, cls in classes.items()}
    controllers["marketSyncController"] = market_sync_controller.MarketSyncController(parent=engine, container=container)
    for name, controller in controllers.items():
        engine.rootContext().setContextProperty(name, controller)
    engine.addImportPath(str(Path(os.getcwd()) / "src" / "ui_qml" / "qml"))
    return engine, controllers


def _render_view(engine, out_dir: Path, name: str, qml_relative: str, steps) -> None:
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlComponent
    from PySide6.QtQuick import QQuickWindow

    qml_path = Path(os.getcwd()) / "src" / "ui_qml" / "qml" / qml_relative
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml_path)))
    if not component.isReady():
        raise SystemExit(f"{qml_relative} derlenemedi: {[e.toString() for e in component.errors()]}")
    window = QQuickWindow()
    window.resize(1280, 820)
    item = component.create()
    item.setParentItem(window.contentItem())
    item.setProperty("width", 1280)
    item.setProperty("height", 820)
    window.show()
    _pump()
    for label, action in steps:
        if action is not None:
            action(item)
        _pump()
        window.grabWindow().save(str(out_dir / f"{name}__{label}.png"))
    window.hide()
    item.deleteLater()


def _set_property(name: str, value):
    return lambda item: item.setProperty(name, value)


def _set_on_any(name: str, value):
    """Özelliği, onu tanımlayan nesneye (kök ya da çocuk bileşen) yazar; bölünmeden önce/sonra aynı betik çalışır."""
    from PySide6.QtCore import QObject

    def run(item):
        for obj in [item] + item.findChildren(QObject):
            meta = obj.metaObject()
            if name in [meta.property(i).name() for i in range(meta.propertyCount())]:
                obj.setProperty(name, value)
    return run


def render(out_dir: Path, db_dir: Path | None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    _prepare_environment(db_dir)
    from PySide6.QtQuick import QQuickWindow, QSGRendererInterface
    from PySide6.QtWebEngineQuick import QtWebEngineQuick
    from PySide6.QtWidgets import QApplication

    QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Software)
    QtWebEngineQuick.initialize()
    app = QApplication.instance() or QApplication([])
    engine, controllers = _build_engine()
    _pump(40)  # arka plan açılış yüklemelerinin oturması için

    _render_view(engine, out_dir, "settings", "views/SettingsView.qml",
                 [(f"tab{i}", _set_property("activeTabIndex", i)) for i in range(8)])
    _render_view(engine, out_dir, "aiadvisor", "views/AiAdvisorView.qml",
                 [("mode0", _set_property("mode", 0)), ("mode1", _set_property("mode", 1))])
    _render_view(engine, out_dir, "optimization", "views/OptimizationView.qml", [("default", None)])
    _render_view(engine, out_dir, "stock360", "views/Stock360View.qml",
                 [(f"viewmode{m}", (lambda m: lambda item: controllers["stock360Controller"].setViewMode(m))(m)) for m in (0, 1, 2)])

    def open_detail(item):
        controllers["stockDetailController"].openStock(os.environ.get("QML_SNAPSHOT_TICKER", "THYAO"))
        _pump(60)

    _render_view(engine, out_dir, "stockdetail", "components/StockDetailModal.qml",
                 [("closed", None), ("open_tab0", open_detail), ("open_tab1", _set_on_any("activeTab", 1))])
    print(f"{len(list(out_dir.glob('*.png')))} görüntü yazıldı: {out_dir}")
    del app


def _different_pixels(a, b) -> int:
    width = a.width() * 4
    return sum(
        1
        for y in range(a.height())
        if bytes(a.constScanLine(y))[:width] != bytes(b.constScanLine(y))[:width]
        for x in range(a.width())
        if a.pixel(x, y) != b.pixel(x, y)
    )


def _compare_one(path_a: Path, path_b: Path) -> bool:
    """Dosya çifti özdeşse True; farkı yazdırır."""
    from PySide6.QtGui import QImage

    if not path_b.exists():
        print(f"{path_a.name}: karşılığı yok")
        return False
    a, b = QImage(str(path_a)), QImage(str(path_b))
    if a.size() != b.size():
        print(f"{path_a.name}: boyut farkı")
        return False
    count = _different_pixels(a, b)
    print(f"{path_a.name}: {count} farklı piksel")
    return count == 0


def compare(dir_a: Path, dir_b: Path) -> int:
    different = sum(not _compare_one(path, dir_b / path.name) for path in sorted(dir_a.glob("*.png")))
    print("SONUÇ:", "özdeş" if different == 0 else f"{different} dosyada fark var")
    return 1 if different else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    render_parser = sub.add_parser("render", help="görünümleri ofscreen çizip PNG yaz")
    render_parser.add_argument("out_dir", type=Path)
    render_parser.add_argument("--db-dir", type=Path, default=None, help="portfolio.db ve market_history.duckdb içeren klasör (varsayılan: gerçek veriden geçici kopya)")
    compare_parser = sub.add_parser("compare", help="iki görüntü dizinini piksel piksel karşılaştır")
    compare_parser.add_argument("dir_a", type=Path)
    compare_parser.add_argument("dir_b", type=Path)
    args = parser.parse_args(argv)
    if args.command == "render":
        render(args.out_dir, args.db_dir)
        return 0
    from PySide6.QtGui import QGuiApplication  # noqa: F401  (QImage için yeterli)

    return compare(args.dir_a, args.dir_b)


if __name__ == "__main__":
    raise SystemExit(main())
