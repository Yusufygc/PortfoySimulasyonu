from __future__ import annotations

from datetime import date, timedelta

from PyQt5.QtWidgets import QMessageBox

from src.application.services.corporate_actions.corporate_action_service import CorporateActionResult
from src.domain.models.corporate_action import ActionType
from src.ui.formatters import display_ticker
from src.ui.widgets.dashboard.dialogs.corporate_action_dialog import CorporateActionDialog
from src.ui.widgets.shared import Toast
from src.ui.worker import Worker


class DashboardCorporateActionActions:
    def __init__(self, page, presenter) -> None:
        self._page = page
        self._presenter = presenter

    def on_corporate_action(self, row: int, action_type_str: str) -> None:
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
        if dialog.exec_() != dialog.Accepted:
            return

        result_data = dialog.get_result()
        if not result_data:
            return

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

        try:
            ca_result: CorporateActionResult = self._page.corporate_action_service.apply_action(
                action_id=action.id,
                current_price=current_price,
            )
        except Exception as exc:
            QMessageBox.critical(self._page, "Uygulama Hatası", str(exc))
            return

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
