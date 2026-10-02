"""
SettingsController — Uygulama Ayarları, Veritabanı Yönetimi ve Dışa Aktarım QML Controller'ı (Faz 11).

Sorumluluklar:
- Koyu / Açık tema geçişi (Theme.isDark yönetimi ve QSettings kalıcılığı)
- API anahtarları (Google Gemini ve TCMB EVDS) yönetimi ve canlı bağlantı testi
- SQLite OLTP (data/portfolio.db) sağlık metrikleri ve tablo satır sayıları
- DuckDB OLAP (data/market_history.duckdb) 624 hisse bar istatistikleri ve seans kapanış senkronizasyonu
- SQLite ve DuckDB bütünlük kontrolü (Integrity Check)
- Excel (.xlsx) ve JSON portföy dışa aktarımı / yedekleme
- ThreadPoolExecutor ile UI bloklamayan asenkron operasyonlar ve Qt Queued Signal mimarisi
"""
from __future__ import annotations

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Property, QObject, QSettings, Signal, Slot

from config.settings_loader import persist_api_keys
from src.application.services.database.database_maintenance_service import DatabaseMaintenanceService

logger = logging.getLogger(__name__)



class SettingsController(QObject):
    """QML SettingsView için iş mantığı ve veri köprüsü."""

    # QML Property Sinyalleri
    isLoadingChanged = Signal(bool)
    statusMessageChanged = Signal(str)
    isDarkThemeChanged = Signal(bool)
    geminiApiKeyChanged = Signal(str)
    evdsApiKeyChanged = Signal(str)
    sqliteDbSizeChanged = Signal(str)
    sqliteTableStatsChanged = Signal()
    duckDbSizeChanged = Signal(str)
    duckDbStockCountChanged = Signal(int)
    duckDbTotalBarsChanged = Signal(str)
    duckDbLastDateChanged = Signal(str)
    duckDbIsUpToDateChanged = Signal(bool)
    isSyncingChanged = Signal(bool)
    apiTestResultChanged = Signal(str)
    integrityCheckResultChanged = Signal(str)

    # Bildirim Sinyali
    operationNotification = Signal(bool, str)  # success, message

    # İç iş parçacığı sinyalleri (Qt Queued Connection garantisi)
    _asyncStatsReady = Signal(dict)
    _asyncSyncFinished = Signal(dict)
    _asyncApiTestFinished = Signal(bool, str)
    _asyncIntegrityFinished = Signal(bool, str)
    _asyncExportFinished = Signal(bool, str)

    def __init__(self, container=None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._container = container
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="SettingsWorker")
        self._settings = QSettings("PortfoySimulasyonu", "PortfoySimulasyonu")

        # Dahili Durumlar
        self._is_loading = False
        self._status_message = "Hazır"
        self._is_dark_theme = self._settings.value("ui/isDarkTheme", True, type=bool)
        self._is_syncing = False
        self._api_test_result = ""
        self._integrity_check_result = ""

        # Veritabanı Yolları
        configured = getattr(getattr(container, "db_config", None), "db_path", None) if container else None
        self._maintenance = DatabaseMaintenanceService.from_config(configured if isinstance(configured, str) else None)
        self._sqlite_path = self._maintenance.sqlite_path
        self._duckdb_path = self._maintenance.duckdb_path

        # İstatistik Değerleri
        self._sqlite_size = "0 B"
        self._sqlite_table_stats: List[Dict[str, Any]] = []
        self._duckdb_size = "0 B"
        self._duckdb_stock_count = 0
        self._duckdb_total_bars = "0"
        self._duckdb_last_date = "-"
        self._duckdb_is_up_to_date = True

        # İç sinyal bağlantıları
        self._asyncStatsReady.connect(self._on_stats_ready)
        self._asyncSyncFinished.connect(self._on_sync_finished)
        self._asyncApiTestFinished.connect(self._on_api_test_finished)
        self._asyncIntegrityFinished.connect(self._on_integrity_finished)
        self._asyncExportFinished.connect(self._on_export_finished)

        # İlk istatistikleri yükle
        self.refreshDatabaseStats()

    # -------------------------------------------------------------------------
    # QML Property'leri
    # -------------------------------------------------------------------------

    @Property(bool, notify=isLoadingChanged)
    def isLoading(self) -> bool:
        return self._is_loading

    @Property(str, notify=statusMessageChanged)
    def statusMessage(self) -> str:
        return self._status_message

    @Property(bool, notify=isDarkThemeChanged)
    def isDarkTheme(self) -> bool:
        return self._is_dark_theme

    @Property(str, notify=geminiApiKeyChanged)
    def geminiApiKey(self) -> str:
        if self._container:
            settings = getattr(self._container, "settings", None)
            if settings and hasattr(settings, "ai"):
                return getattr(settings.ai, "gemini_api_key", "") or ""
        return ""

    @Property(str, notify=evdsApiKeyChanged)
    def evdsApiKey(self) -> str:
        if self._container:
            settings = getattr(self._container, "settings", None)
            market = getattr(settings, "market", None) if settings else None
            if market is not None:
                return getattr(market, "evds_api_key", "") or ""
        return ""

    @Property(str, constant=True)
    def sqliteDbPath(self) -> str:
        return str(self._sqlite_path)

    @Property(str, notify=sqliteDbSizeChanged)
    def sqliteDbSize(self) -> str:
        return self._sqlite_size

    @Property("QVariantList", notify=sqliteTableStatsChanged)
    def sqliteTableStats(self) -> List[Dict[str, Any]]:
        return self._sqlite_table_stats

    @Property(str, constant=True)
    def duckDbPath(self) -> str:
        return str(self._duckdb_path)

    @Property(str, notify=duckDbSizeChanged)
    def duckDbSize(self) -> str:
        return self._duckdb_size

    @Property(int, notify=duckDbStockCountChanged)
    def duckDbStockCount(self) -> int:
        return self._duckdb_stock_count

    @Property(str, notify=duckDbTotalBarsChanged)
    def duckDbTotalBars(self) -> str:
        return self._duckdb_total_bars

    @Property(str, notify=duckDbLastDateChanged)
    def duckDbLastDate(self) -> str:
        return self._duckdb_last_date

    @Property(bool, notify=isSyncingChanged)
    def isSyncing(self) -> bool:
        return self._is_syncing

    @Property(str, notify=apiTestResultChanged)
    def apiTestResult(self) -> str:
        return self._api_test_result

    @Property(str, notify=integrityCheckResultChanged)
    def integrityCheckResult(self) -> str:
        return self._integrity_check_result

    # -------------------------------------------------------------------------
    # Tema Yönetimi
    # -------------------------------------------------------------------------

    @Slot()
    def toggleTheme(self) -> None:
        """Koyu / Açık tema geçişini sağlar ve QSettings'e kaydeder."""
        self._is_dark_theme = not self._is_dark_theme
        self._settings.setValue("ui/isDarkTheme", self._is_dark_theme)
        self.isDarkThemeChanged.emit(self._is_dark_theme)
        theme_name = "Koyu Tema" if self._is_dark_theme else "Açık Tema"
        self._set_status(f"{theme_name} aktif edildi")
        self.operationNotification.emit(True, f"{theme_name} başarıyla etkinleştirildi.")

    # -------------------------------------------------------------------------
    # API Anahtarları ve Bağlantı Testi
    # -------------------------------------------------------------------------

    @Slot(str, str)
    def saveApiKeys(self, gemini_key: str, evds_key: str) -> None:
        """API anahtarlarını günceller ve yapılandırmaya yansıtır."""
        clean_gemini = (gemini_key or "").strip()
        clean_evds = (evds_key or "").strip()

        try:
            persist_api_keys(
                getattr(self._container, "settings", None) if self._container else None,
                gemini_key=clean_gemini,
                evds_key=clean_evds,
            )
        except Exception as exc:
            logger.exception("API anahtarları kaydedilemedi: %s", exc)
            self.operationNotification.emit(False, f"API anahtarları kaydedilemedi: {exc}")
            self._set_status("API anahtarları kaydedilemedi")
            return

        self.geminiApiKeyChanged.emit(clean_gemini)
        self.evdsApiKeyChanged.emit(clean_evds)
        self.operationNotification.emit(True, "API anahtarları kaydedildi. EVDS anahtarı bir sonraki açılışta etkin olur.")
        self._set_status("API anahtarları kaydedildi")

    @Slot(str)
    def testGeminiApiKey(self, key_to_test: str) -> None:
        """Google Gemini API anahtarı için canlı bağlantı testi yapar."""
        key = (key_to_test or "").strip()
        if not key:
            self._api_test_result = "Lütfen önce geçerli bir API anahtarı girin."
            self.apiTestResultChanged.emit(self._api_test_result)
            return

        self._set_loading(True)
        self._api_test_result = "Google Gemini sunucularına bağlanılıyor..."
        self.apiTestResultChanged.emit(self._api_test_result)

        self._executor.submit(self._run_gemini_test_worker, key)

    def _run_gemini_test_worker(self, key: str) -> None:
        try:
            from google import genai
            client = genai.Client(api_key=key)
            # En hafif model ile hızlı ping sorgusu
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents="Ping. Sadece 'PONG' cevabını ver.",
            )
            success = bool(resp and resp.text)
            msg = "Bağlantı Başarılı! Gemini 2.5 Flash erişilebilir durumda." if success else "Sunucu yanıt vermedi."
            self._asyncApiTestFinished.emit(success, msg)
        except Exception as exc:
            logger.warning("Gemini API test hatası: %s", exc)
            self._asyncApiTestFinished.emit(False, f"Bağlantı Hatası: {exc}")

    def _on_api_test_finished(self, success: bool, message: str) -> None:
        self._api_test_result = message
        self.apiTestResultChanged.emit(self._api_test_result)
        self._set_loading(False)
        self.operationNotification.emit(success, message)

    # -------------------------------------------------------------------------
    # Veritabanı İstatistikleri ve Sağlık Taraması
    # -------------------------------------------------------------------------

    @Slot()
    def refreshDatabaseStats(self) -> None:
        """SQLite ve DuckDB metriklerini asenkron hesaplar."""
        self._set_loading(True)
        self._set_status("Veritabanı metrikleri taranıyor...")
        self._executor.submit(self._run_db_stats_worker)

    def _run_db_stats_worker(self) -> None:
        self._asyncStatsReady.emit(self._maintenance.collect_stats())

    def _on_stats_ready(self, payload: Dict[str, Any]) -> None:
        self._sqlite_size = payload.get("sqlite_size", "0 B")
        self._sqlite_table_stats = payload.get("sqlite_table_stats", [])
        self._duckdb_size = payload.get("duckdb_size", "0 B")
        self._duckdb_stock_count = payload.get("duckdb_stock_count", 0)
        self._duckdb_total_bars = payload.get("duckdb_total_bars", "0")
        self._duckdb_last_date = payload.get("duckdb_last_date", "-")
        self._duckdb_is_up_to_date = payload.get("duckdb_is_up_to_date", True)

        self.sqliteDbSizeChanged.emit(self._sqlite_size)
        self.sqliteTableStatsChanged.emit()
        self.duckDbSizeChanged.emit(self._duckdb_size)
        self.duckDbStockCountChanged.emit(self._duckdb_stock_count)
        self.duckDbTotalBarsChanged.emit(self._duckdb_total_bars)
        self.duckDbLastDateChanged.emit(self._duckdb_last_date)
        self.duckDbIsUpToDateChanged.emit(self._duckdb_is_up_to_date)

        self._set_loading(False)
        self._set_status("Veritabanı metrikleri güncellendi")

    # -------------------------------------------------------------------------
    # Piyasa Verisi Manuel Senkronizasyonu
    # -------------------------------------------------------------------------

    @Slot()
    def runFullMarketSync(self) -> None:
        """Kullanıcının tetiklediği eksik BIST verisi senkronizasyonunu yürütür."""
        if self._is_syncing:
            return

        self._is_syncing = True
        self.isSyncingChanged.emit(True)
        self._set_status("BIST seans verileri senkronize ediliyor...")
        self._executor.submit(self._run_market_sync_worker)

    def _run_market_sync_worker(self) -> None:
        try:
            from src.application.services.market_data.market_data_sync_service import MarketDataSyncService
            sync_svc = getattr(self._container, "market_data_sync_service", None) if self._container else None
            if not isinstance(sync_svc, MarketDataSyncService):
                sync_svc = MarketDataSyncService(duckdb_path=str(self._duckdb_path))
            result = sync_svc.sync_daily_delta()
            self._asyncSyncFinished.emit({
                "success": True,
                "message": result.message,
                "added_bars": result.added_bars,
            })
        except Exception as e:
            logger.exception("Senkronizasyon işlemi hatası: %s", e)
            self._asyncSyncFinished.emit({
                "success": False,
                "message": f"Senkronizasyon hatası: {e}",
                "added_bars": 0,
            })

    def _on_sync_finished(self, res: Dict[str, Any]) -> None:
        self._is_syncing = False
        self.isSyncingChanged.emit(False)
        success = res.get("success", False)
        msg = res.get("message", "Tamamlandı")
        self._set_status(msg)
        self.operationNotification.emit(success, msg)
        # İstatistikleri otomatik tazele
        self.refreshDatabaseStats()

    # -------------------------------------------------------------------------
    # Veritabanı Bütünlük Kontrolü (Integrity Check)
    # -------------------------------------------------------------------------

    @Slot()
    def checkDatabaseIntegrity(self) -> None:
        """SQLite ve DuckDB için PRAGMA integrity_check çalıştırır."""
        self._set_loading(True)
        self._integrity_check_result = "Veritabanı bütünlük kontrolü yürütülüyor..."
        self.integrityCheckResultChanged.emit(self._integrity_check_result)
        self._executor.submit(self._run_integrity_worker)

    def _run_integrity_worker(self) -> None:
        errors = self._maintenance.check_integrity()
        if errors:
            self._asyncIntegrityFinished.emit(False, " | ".join(errors))
        else:
            self._asyncIntegrityFinished.emit(
                True,
                "Mükemmel! SQLite (OLTP) ve DuckDB (OLAP) veritabanı bütünlüğü doğrulandı (OK)."
            )

    def _on_integrity_finished(self, success: bool, message: str) -> None:
        self._integrity_check_result = message
        self.integrityCheckResultChanged.emit(self._integrity_check_result)
        self._set_loading(False)
        self.operationNotification.emit(success, message)

    # -------------------------------------------------------------------------
    # Dışa Aktarım (Excel & JSON)
    # -------------------------------------------------------------------------

    @Slot()
    def exportPortfolioToExcel(self) -> None:
        """Kullanıcının portföyünü Excel formatında masaüstüne veya reports klasörüne kaydeder."""
        self._set_loading(True)
        self._set_status("Excel raporu hazırlanıyor...")
        self._executor.submit(self._run_excel_export_worker)

    def _run_excel_export_worker(self) -> None:
        try:
            # Hedef yol: Masaüstü veya proje içi reports/
            desktop = Path.home() / "Desktop"
            out_dir = desktop if desktop.exists() else Path("reports").resolve()
            out_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_file = out_dir / f"PortfoySim_Rapor_{timestamp}.xlsx"

            excel_service = getattr(self._container, "excel_export_service", None) if self._container else None
            portfolio_service = getattr(self._container, "portfolio_service", None) if self._container else None

            if excel_service and portfolio_service:
                first_date = portfolio_service.get_first_trade_date() or date.today()
                from src.application.services.reporting.daily_history_models import ExportMode
                excel_service.export_history(
                    start_date=first_date,
                    end_date=date.today(),
                    file_path=target_file,
                    mode=ExportMode.OVERWRITE,
                )
                self._asyncExportFinished.emit(True, f"Kapsamlı portföy Excel raporu oluşturuldu:\n{target_file.name}")
            else:
                self._maintenance.export_tables_to_excel(target_file)

                self._asyncExportFinished.emit(True, f"Excel raporu oluşturuldu:\n{target_file.name}")
        except Exception as e:
            logger.exception("Excel export hatası: %s", e)
            self._asyncExportFinished.emit(False, f"Excel dışa aktarım hatası: {e}")

    @Slot()
    def exportPortfolioToJson(self) -> None:
        """Tüm portföyü JSON yedek dosyası olarak kaydeder."""
        self._set_loading(True)
        self._set_status("JSON yedeği alınıyor...")
        self._executor.submit(self._run_json_export_worker)

    def _run_json_export_worker(self) -> None:
        try:
            desktop = Path.home() / "Desktop"
            out_dir = desktop if desktop.exists() else Path("reports").resolve()
            out_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_file = out_dir / f"PortfoySim_Yedek_{timestamp}.json"

            backup_data = self._maintenance.export_backup_data()

            with open(target_file, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2, default=str)

            self._asyncExportFinished.emit(True, f"JSON yedeği kaydedildi:\n{target_file.name}")
        except Exception as e:
            logger.exception("JSON export hatası: %s", e)
            self._asyncExportFinished.emit(False, f"JSON yedekleme hatası: {e}")

    def _on_export_finished(self, success: bool, message: str) -> None:
        self._set_loading(False)
        self._set_status("Dışa aktarım tamamlandı")
        self.operationNotification.emit(success, message)

    # -------------------------------------------------------------------------
    # Durum Yönetimi
    # -------------------------------------------------------------------------

    def _set_loading(self, val: bool) -> None:
        if self._is_loading != val:
            self._is_loading = val
            self.isLoadingChanged.emit(val)

    def _set_status(self, msg: str) -> None:
        if self._status_message != msg:
            self._status_message = msg
            self.statusMessageChanged.emit(msg)
