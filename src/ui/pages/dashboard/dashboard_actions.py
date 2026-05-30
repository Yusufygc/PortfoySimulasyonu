from __future__ import annotations

import logging
from datetime import date, timedelta

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QDialog

from src.application.services.corporate_actions.corporate_action_service import CorporateActionResult
from src.application.services.reporting.daily_history_models import ExportMode
from src.domain.models.corporate_action import ActionType
from src.domain.models.trade import TradeSide
from src.ui.widgets.dashboard.dialogs.corporate_action_dialog import CorporateActionDialog
from src.ui.formatters import display_ticker
from src.ui.shared.market_session_confirm import confirm_market_session_if_needed
from src.ui.widgets.shared import Toast
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
        try:
            if action == "deposit":
                self._page.cash_movement_service.add_deposit(amount, notes="Sermaye ekleme")
                QMessageBox.information(self._page, "Başarılı", f"{amount:,.2f} TL sermaye eklendi.")
            else:
                self._page.cash_movement_service.add_withdraw(amount, notes="Sermaye çekme")
                QMessageBox.information(self._page, "Başarılı", f"{amount:,.2f} TL sermaye çekildi.")
        except ValueError as exc:
            QMessageBox.warning(self._page, "Uyarı", str(exc))
            return

        self._presenter.load_capital()
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
        if not confirm_market_session_if_needed(
            self._page,
            getattr(self._page, "market_session_service", None),
            data["trade_date"],
            data.get("trade_time"),
        ):
            return

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
            self._presenter.load_capital()
            self._presenter.refresh_data()
            QMessageBox.information(self._page, "Başarılı", "İşlem başarıyla eklendi.")
            self._page._last_trade_result = result
        except ValueError as exc:
            QMessageBox.warning(self._page, "Geçersiz İşlem", str(exc))
        except Exception as exc:
            QMessageBox.critical(self._page, "Hata", f"İşlem kaydedilemedi: {exc}")

    def on_update_prices(self) -> None:
        self._page.btn_update_prices.setEnabled(False)
        self._page.btn_update_prices.setText("Güncelleniyor...")

        # Ağ zaman aşımı durumunda butonu zorla aktifleştir (2 dakika)
        self._update_timeout_timer = QTimer(self._page)
        self._update_timeout_timer.setSingleShot(True)
        self._update_timeout_timer.timeout.connect(self._finish_update_prices)
        self._update_timeout_timer.start(120_000)

        worker = Worker(self._page.update_coordinator.update_today_prices_and_get_snapshot)
        worker.signals.result.connect(self.on_update_prices_success)
        worker.signals.error.connect(self.on_update_prices_error)
        worker.signals.finished.connect(self._finish_update_prices)
        self._page.threadpool.start(worker)

    def _finish_update_prices(self) -> None:
        timer = getattr(self, "_update_timeout_timer", None)
        if timer and timer.isActive():
            timer.stop()
        self._page.btn_update_prices.setEnabled(True)
        self._page.btn_update_prices.setText(" Fiyatları Güncelle")

    def on_update_prices_success(self, result) -> None:
        price_update_result, _snapshot = result
        self._presenter.refresh_data()
        self._presenter.update_returns()
        if price_update_result.updated_count <= 0:
            skipped_reason = getattr(price_update_result, "skipped_reason", None)
            Toast.warning(
                self._page,
                skipped_reason or "Güncellenecek fiyat bulunamadı.",
                duration_ms=4000,
                position="top",
            )
            return

        self._page.record_last_update_time()
        self._page.show_last_update_toast_once(
            force=True,
            detail=f"{price_update_result.updated_count} hisse güncellendi.",
        )

    def on_update_prices_error(self, err_tuple) -> None:
        QMessageBox.critical(self._page, "Hata", f"Hata:\n{err_tuple[1]}")

    def on_export_today(self) -> None:
        first_date = self._page.portfolio_service.get_first_trade_date()
        if first_date is None:
            QMessageBox.information(self._page, "Bilgi", "Herhangi bir işlem bulunamadı.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self._page,
            "Excel Dosyası Seç",
            "portfoy_takip.xlsx",
            "Excel Dosyaları (*.xlsx)",
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
            QMessageBox.information(self._page, "Başarılı", "Excel aktarımı tamamlandı.")
        except Exception as exc:
            QMessageBox.critical(self._page, "Hata", f"Excel hatası: {exc}")

    def on_export_range(self) -> None:
        first_date = self._page.portfolio_service.get_first_trade_date()
        if first_date is None:
            QMessageBox.information(self._page, "Bilgi", "İşlem bulunamadı.")
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
            "Excel Seç",
            "portfoy_takip.xlsx",
            "Excel Dosyaları (*.xlsx)",
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
            QMessageBox.information(self._page, "Başarılı", "Excel aktarımı tamamlandı.")
        except Exception as exc:
            QMessageBox.critical(self._page, "Hata", f"Hata: {exc}")

    # ══════════════════════════════════════════════════════════
    #  SERMAYE ARTIRIMI (sağ-tık context menüden tetiklenir)
    # ══════════════════════════════════════════════════════════

    def on_corporate_action(self, row: int, action_type_str: str) -> None:
        """
        Portföy tablosuna sağ tıklanınca çağrılır.
        row            : Tablodaki satır indeksi
        action_type_str: "BEDELLI" veya "BEDELSIZ"
        """
        if self._page.portfolio_model is None:
            return

        try:
            position = self._page.portfolio_model.get_position(row)
        except IndexError:
            return

        stock = self._page.stock_repo.get_stock_by_id(position.stock_id)
        if stock is None:
            QMessageBox.warning(self._page, "Hata", "Hisse bilgisi bulunamadı.")
            return

        ticker = stock.ticker
        price_map = getattr(self._page.portfolio_model, "_price_map", {}) if self._page.portfolio_model else {}
        current_price = price_map.get(position.stock_id)

        dialog = CorporateActionDialog(
            ticker=ticker,
            stock_id=position.stock_id,
            current_qty=position.total_quantity,
            avg_cost=position.average_cost,
            total_cost=position.total_cost,
            current_price=current_price,
            parent=self._page,
        )
        if dialog.exec_() != QDialog.Accepted:
            return

        result_data = dialog.get_result()
        if not result_data:
            return

        # 1) Aksiyonu DB'ye kaydet
        try:
            if result_data["action_type"] == "BEDELSIZ":
                action = self._page.corporate_action_service.register_bedelsiz(
                    stock_id=result_data["stock_id"],
                    ex_date=result_data["ex_date"],
                    ratio=result_data["ratio"],
                    notes=result_data.get("notes"),
                )
            else:
                action = self._page.corporate_action_service.register_bedelli(
                    stock_id=result_data["stock_id"],
                    ex_date=result_data["ex_date"],
                    ratio=result_data["ratio"],
                    subscription_price=result_data["subscription_price"],
                    notes=result_data.get("notes"),
                )
        except Exception as exc:
            QMessageBox.critical(self._page, "Kayıt Hatası", str(exc))
            return

        # 2) Aksiyonu portföye uygula
        try:
            ca_result: CorporateActionResult = self._page.corporate_action_service.apply_action(
                action_id=action.id,
                current_price=current_price,
            )
        except Exception as exc:
            QMessageBox.critical(self._page, "Uygulama Hatası", str(exc))
            return

        # 3) Geçmiş fiyatları YFinance'den yenile (arka planda Worker ile)
        self._refresh_prices_after_corporate_action(
            stock_id=result_data["stock_id"],
            ticker=ticker,
            ca_result=ca_result,
        )

    def _refresh_prices_after_corporate_action(
        self,
        stock_id: int,
        ticker: str,
        ca_result: CorporateActionResult,
    ) -> None:
        """
        Sermaye artırımı uygulandıktan sonra o hissenin geçmiş fiyatlarını
        YFinance'den yeniden indirir. YFinance ex-date sonrasında retroaktif
        adjusted fiyatlar verir; daily_prices tablosundaki eski fiyatlar
        upsert ile doğru değerlere güncellenir.
        """
        first_date = self._page.portfolio_service.get_first_trade_date()
        if first_date is None:
            first_date = date.today() - timedelta(days=365)

        end_date = date.today()

        def _do_backfill():
            return self._page.backfill_service.backfill_for_single_stock(
                stock_id=stock_id,
                ticker=ticker,
                start_date=first_date,
                end_date=end_date,
            )

        Toast.info(
            self._page,
            f"{display_ticker(ticker)} için geçmiş fiyatlar güncelleniyor...",
            duration_ms=3000,
            position="top",
        )

        ca_result_ref = ca_result

        def _on_success(updated_count: int):
            self._presenter.refresh_data()
            # Adjusted fiyatlar artık DB'de; getiri kartını doğru değerle güncelle
            self._presenter.update_returns()
            type_label = "Bedelsiz" if ca_result_ref.action_type == ActionType.BEDELSIZ else "Bedelli"
            Toast.info(
                self._page,
                f"{type_label} sermaye artırımı uygulandı. "
                f"{ca_result_ref.shares_before} lot → {ca_result_ref.shares_after} lot | "
                f"Fiyat geçmişi güncellendi ({updated_count} kayıt).",
                duration_ms=6000,
                position="top",
            )

        def _on_error(err_tuple):
            # Fiyat güncelleme başarısız olsa da pozisyon zaten güncellendi
            self._presenter.refresh_data()
            type_label = "Bedelsiz" if ca_result_ref.action_type == ActionType.BEDELSIZ else "Bedelli"
            QMessageBox.warning(
                self._page,
                "Fiyat Güncelleme Uyarısı",
                f"{type_label} sermaye artırımı uygulandı, ancak geçmiş fiyatlar "
                f"güncellenirken hata oluştu:\n{err_tuple[1]}\n\n"
                "Fiyatları daha sonra manuel olarak 'Fiyatları Güncelle' butonuyla yenileyebilirsiniz.",
            )

        worker = Worker(_do_backfill)
        worker.signals.result.connect(_on_success)
        worker.signals.error.connect(_on_error)
        self._page.threadpool.start(worker)

    def on_reset(self) -> None:
        reply = QMessageBox.question(
            self._page,
            "Portföyü Sıfırla",
            "TÜM veriler silinecek. Emin misiniz?",
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
            QMessageBox.information(self._page, "Tamamlandı", "Başarıyla sıfırlandı.")
        except Exception as exc:
            QMessageBox.critical(self._page, "Hata", f"Hata: {exc}")
