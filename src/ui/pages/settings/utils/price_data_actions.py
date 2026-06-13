from __future__ import annotations
from src.ui.shared.confirm_dialog import ask_confirm
from src.ui.shared.locale_tr import L10N

from datetime import date, timedelta
from typing import TYPE_CHECKING

from src.qt_compat.qtwidgets import QApplication, QMessageBox

from src.application.services.market.price_data_health_service import (
    PriceDataHealthReport,
    PriceDataUpdateResult,
)
from src.ui.widgets.shared import Toast
from src.ui.worker import Worker

if TYPE_CHECKING:
    from src.ui.pages.settings.price_data_panel import PriceDataPanel


class PriceDataActions:
    """Worker tabanlı işlem metodlarını yönetir (analiz, güncelleme, silme)."""

    def __init__(self, panel: PriceDataPanel) -> None:
        self.panel = panel

    def analyze(self) -> None:
        panel = self.panel
        if panel.price_data_health_service is None:
            Toast.warning(panel, L10N.FIYAT_VERISI_YONETIM_SERVISI_KULLANILAMIYOR)
            return
        start_date, end_date = panel._date_range()
        scope = panel._selected_scope()
        self._run_worker(
            panel.price_data_health_service.analyze,
            self._on_analyze_success,
            L10N.VERI_SAGLIGI_ANALIZ_EDILIYOR,
            start_date,
            end_date,
            scope,
        )

    def update_missing(self) -> None:
        panel = self.panel
        if panel.price_data_health_service is None:
            return
        start_date, end_date = panel._date_range()
        scope = panel._selected_scope()
        self._run_worker(
            panel.price_data_health_service.update_missing_prices,
            self._on_update_success,
            L10N.EKSIK_FIYATLAR_GUNCELLENIYOR,
            start_date,
            end_date,
            None,
            scope,
        )

    def update_selected(self) -> None:
        panel = self.panel
        if panel.price_data_health_service is None:
            return
        stock_id = panel._selected_stock_id()
        if stock_id is None:
            Toast.warning(panel, L10N.ONCE_TABLODAN_BIR_HISSE_SECIN)
            return
        start_date, end_date = panel._date_range()
        self._run_worker(
            panel.price_data_health_service.update_stock_range,
            self._on_update_success,
            L10N.SECILI_HISSE_GUNCELLENIYOR,
            stock_id,
            start_date,
            end_date,
        )

    def update_from_latest(self) -> None:
        panel = self.panel
        if panel.price_data_health_service is None:
            return
        target_date = self._last_completed_trading_day(date.today())
        self._run_worker(
            panel.price_data_health_service.update_from_latest_to_today,
            self._on_update_success,
            L10N.SON_GUNCEL_GUNDEN_BUGUNE_EKSIKLER,
            target_date,
            panel._selected_scope(),
        )

    def delete_range(self) -> None:
        panel = self.panel
        if panel.price_data_health_service is None:
            return
        start_date, end_date = panel._date_range()
        scope = panel._selected_scope()
        scope_label = panel._selected_scope_label()
        if not ask_confirm(
            panel,
            L10N.FIYAT_VERISINI_SIL,
            L10N.FIYAT_KAYITLARI_SILINECEK_ONAY_TMPL.format(
                start=start_date.strftime('%d.%m.%Y'),
                end=end_date.strftime('%d.%m.%Y'),
                scope=scope_label,
            ),
        ):
            return
        self._run_worker(
            panel.price_data_health_service.delete_range,
            self._on_delete_success,
            L10N.FIYAT_KAYITLARI_SILINIYOR,
            start_date,
            end_date,
            scope,
        )

    def copy_report(self) -> None:
        panel = self.panel
        if panel._current_report is None:
            Toast.warning(panel, L10N.KOPYALANACAK_ANALIZ_RAPORU_YOK)
            return
        QApplication.clipboard().setText(
            panel._report_renderer.format_report_text(panel._current_report)
        )
        Toast.success(panel, L10N.VERI_SAGLIGI_RAPORU_PANOYA_KOPYALANDI)

    def _run_worker(self, fn, success_slot, busy_text: str, *args) -> None:
        panel = self.panel
        panel._set_busy(True, busy_text)
        worker = Worker(fn, *args)
        worker.signals.result.connect(success_slot)
        worker.signals.error.connect(self._on_worker_error)
        worker.signals.finished.connect(lambda: panel._set_busy(False))
        panel.threadpool.start(worker)

    def _last_completed_trading_day(self, today: date) -> date:
        candidate = today - timedelta(days=1)
        calendar = getattr(getattr(self.panel, "container", None), "trading_calendar", None)
        while calendar is not None and not calendar.is_trading_day(candidate):
            candidate -= timedelta(days=1)
        return candidate

    def _on_analyze_success(self, report: PriceDataHealthReport) -> None:
        self.panel._apply_report(report)
        Toast.success(self.panel, L10N.ANALIZ_TAMAMLANDI_TMPL.format(label=report.health_label))

    def _on_update_success(self, result: PriceDataUpdateResult) -> None:
        panel = self.panel
        panel._emit_prices_updated(result)
        if result.updated_count:
            Toast.success(
                panel,
                L10N.FIYAT_KAYDI_TAMAMLANDI_TMPL.format(updated=result.updated_count, skipped=result.skipped_holiday_count),
            )
        else:
            Toast.warning(panel, L10N.GUNCELLENECEK_FIYAT_KAYDI_BULUNAMADI)
            if result.errors:
                panel.detail_text.setText(L10N.HATA_DETAYLARI + "\n" + "\n".join(result.errors[:30]))
            return
        if result.errors:
            Toast.warning(panel, L10N.VERI_KAYNAGI_UYARISI_TMPL.format(count=len(result.errors)))
        self.analyze()

    def _on_delete_success(self, deleted_count: int) -> None:
        Toast.success(self.panel, L10N.FIYAT_KAYDI_SILINDI_TMPL.format(count=deleted_count))
        self.analyze()

    def _on_worker_error(self, err_tuple) -> None:
        QMessageBox.critical(self.panel, L10N.ERROR, L10N.HATA_DETAYLARI_TMPL.format(exc=err_tuple[1]))
