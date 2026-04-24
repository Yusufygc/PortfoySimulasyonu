from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal

from PyQt5.QtWidgets import QFileDialog, QMessageBox, QDialog

from src.application.services.reporting.daily_history_models import ExportMode
from src.domain.models.trade import TradeSide
from src.ui.worker import Worker

logger = logging.getLogger(__name__)


class DashboardActions:
    def __init__(self, page, presenter) -> None:
        self._page = page
        self._presenter = presenter

    def on_capital_management(self) -> None:
        dialog = self._page.capital_dialog_cls(self._page._capital, self._page)
        if dialog.exec_() != QDialog.Accepted:
            return
        result = dialog.get_result()
        if not result:
            return

        action = result["action"]
        amount = result["amount"]
        if action == "deposit":
            self._page._capital += amount
            QMessageBox.information(self._page, "Basarili", f"{amount:,.2f} TL sermaye eklendi.")
        else:
            if amount > self._page._capital:
                QMessageBox.warning(self._page, "Uyari", "Yetersiz sermaye.")
                return
            self._page._capital -= amount
            QMessageBox.information(self._page, "Basarili", f"{amount:,.2f} TL sermaye cekildi.")

        self._presenter.refresh_data()

    def on_new_trade(self) -> None:
        dialog = self._page.new_trade_dialog_cls(
            parent=self._page,
            price_lookup_func=self._page.price_lookup_func,
            lot_size=1,
        )
        if dialog.exec_() != QDialog.Accepted:
            return
        data = dialog.get_result()
        if not data:
            return

        trade_amount = data["price"] * Decimal(data["quantity"])
        try:
            result = self._page.trade_entry_service.submit_trade(
                ticker=data["ticker"],
                name=data["name"],
                side=TradeSide(data["side"]),
                quantity=data["quantity"],
                price=data["price"],
                trade_date=data["trade_date"],
                trade_time=data["trade_time"],
            )
            if data["side"] == "BUY":
                self._page._capital = max(Decimal("0"), self._page._capital - trade_amount)
            else:
                self._page._capital += trade_amount
            self._presenter.refresh_data()
            QMessageBox.information(self._page, "Basarili", "Islem basariyla eklendi.")
            self._page._last_trade_result = result
        except ValueError as exc:
            QMessageBox.warning(self._page, "Gecersiz Islem", str(exc))
        except Exception as exc:
            QMessageBox.critical(self._page, "Hata", f"Islem kaydedilemedi: {exc}")

    def on_update_prices(self) -> None:
        self._page.btn_update_prices.setEnabled(False)
        self._page.btn_update_prices.setText("Guncelleniyor...")
        self._page.btn_backfill.setEnabled(False)

        worker = Worker(self._page.update_coordinator.update_today_prices_and_get_snapshot)
        worker.signals.result.connect(self.on_update_prices_success)
        worker.signals.error.connect(self.on_update_prices_error)
        worker.signals.finished.connect(self._finish_update_prices)
        self._page.threadpool.start(worker)

    def _finish_update_prices(self) -> None:
        self._page.btn_update_prices.setEnabled(True)
        self._page.btn_update_prices.setText(" Fiyatlari Guncelle")
        self._page.btn_backfill.setEnabled(True)

    def on_update_prices_success(self, result) -> None:
        price_update_result, _snapshot = result
        self._presenter.refresh_data()
        self._presenter.update_returns()
        self._page.lbl_last_update.setText(
            f"Son guncelleme: {datetime.now().strftime('%H:%M')} (15dk gecikmeli)"
        )
        QMessageBox.information(
            self._page,
            "Guncelleme Tamamlandi",
            f"{price_update_result.updated_count} hisse guncellendi.",
        )

    def on_update_prices_error(self, err_tuple) -> None:
        QMessageBox.critical(self._page, "Hata", f"Hata:\n{err_tuple[1]}")

    def on_export_today(self) -> None:
        first_date = self._page.portfolio_service.get_first_trade_date()
        if first_date is None:
            QMessageBox.information(self._page, "Bilgi", "Herhangi bir islem bulunamadi.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self._page,
            "Excel Dosyasi Sec",
            "portfoy_takip.xlsx",
            "Excel Dosyalari (*.xlsx)",
        )
        if not file_path:
            return

        try:
            self._page.excel_export_service.export_history(
                start_date=first_date,
                end_date=date.today(),
                file_path=file_path,
                mode=ExportMode.OVERWRITE,
            )
            QMessageBox.information(self._page, "Basarili", "Excel aktarimi tamamlandi.")
        except Exception as exc:
            QMessageBox.critical(self._page, "Hata", f"Excel hatasi: {exc}")

    def on_export_range(self) -> None:
        first_date = self._page.portfolio_service.get_first_trade_date()
        if first_date is None:
            QMessageBox.information(self._page, "Bilgi", "Islem bulunamadi.")
            return

        dialog = self._page.date_range_dialog_cls(self._page, min_date=first_date, max_date=date.today())
        if dialog.exec_() != QDialog.Accepted:
            return

        result = dialog.get_range()
        if not result:
            return
        start_date, end_date = result

        file_path, _ = QFileDialog.getSaveFileName(
            self._page,
            "Excel Sec",
            "portfoy_takip.xlsx",
            "Excel Dosyalari (*.xlsx)",
        )
        if not file_path:
            return

        try:
            self._page.excel_export_service.export_history(
                start_date=start_date,
                end_date=end_date,
                file_path=file_path,
                mode=ExportMode.OVERWRITE,
            )
            QMessageBox.information(self._page, "Basarili", "Excel aktarimi tamamlandi.")
        except Exception as exc:
            QMessageBox.critical(self._page, "Hata", f"Hata: {exc}")

    def on_reset(self) -> None:
        reply = QMessageBox.question(
            self._page,
            "Portfoyu Sifirla",
            "TUM veriler silinecek. Emin misiniz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            self._page.reset_service.reset_all()
            self._page._capital = Decimal("0")
            self._presenter.refresh_data()
            self._page.summary_cards.update_returns(None, None)
            QMessageBox.information(self._page, "Tamamlandi", "Basariyla sifirlandi.")
        except Exception as exc:
            QMessageBox.critical(self._page, "Hata", f"Hata: {exc}")

    def on_backfill(self) -> None:
        if not self._page.backfill_service:
            QMessageBox.warning(self._page, "Uyari", "Backfill servisi kullanilamiyor.")
            return

        dialog = self._page.backfill_dialog_cls(self._page)
        if dialog.exec_() != QDialog.Accepted:
            return
        result = dialog.get_result()
        if not result:
            QMessageBox.warning(self._page, "Uyari", "Baslangic bitisten sonra olamaz.")
            return

        action = result["action"]
        start_date = result["start_date"]
        end_date = result["end_date"]

        if action == "delete":
            reply = QMessageBox.question(
                self._page,
                "Silme Onayi",
                "Veriler silinecek, emin misiniz?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
            try:
                count = self._page.backfill_service.delete_range(start_date, end_date)
                self._presenter.refresh_data()
                QMessageBox.information(self._page, "Basarili", f"{count} veri silindi.")
            except Exception as exc:
                QMessageBox.critical(self._page, "Hata", f"Hata: {exc}")
            return

        self._page.btn_backfill.setEnabled(False)
        self._page.btn_backfill.setText("Indiriliyor...")
        self._page.btn_update_prices.setEnabled(False)

        worker = Worker(self._page.backfill_service.backfill_range, start_date, end_date)
        worker.signals.result.connect(lambda count, sd=start_date, ed=end_date: self.on_backfill_success(count, sd, ed))
        worker.signals.error.connect(self.on_backfill_error)
        worker.signals.finished.connect(self._finish_backfill)
        self._page.threadpool.start(worker)

    def _finish_backfill(self) -> None:
        self._page.btn_backfill.setEnabled(True)
        self._page.btn_backfill.setText(" Gecmis Veri Yonetimi")
        self._page.btn_update_prices.setEnabled(True)

    def on_backfill_success(self, count, start_date, end_date) -> None:
        self._presenter.refresh_data()
        QMessageBox.information(self._page, "Basarili", f"{count} veri indirildi.")

    def on_backfill_error(self, err_tuple) -> None:
        QMessageBox.critical(self._page, "Hata", f"Hata:\n{err_tuple[1]}")
