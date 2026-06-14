from __future__ import annotations
from src.ui.shared.locale_tr import L10N

from datetime import date, timedelta

from src.qt_compat.qtwidgets import QMessageBox

from src.application.services.corporate_actions.corporate_action_service import CorporateActionResult
from src.domain.models.corporate_action import BedelliSpec
from src.domain.models.corporate_action import ActionType
from src.ui.formatters import display_ticker
from src.ui.widgets.dashboard.dialogs.corporate_action_dialog import CorporateActionDialog, CorporateActionDialogContext
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
            QMessageBox.warning(self._page, L10N.ERROR, L10N.HISSE_BILGISI_BULUNAMADI)
            return

        ticker = stock.ticker
        price_map = getattr(self._page.portfolio_model, "_price_map", {}) if self._page.portfolio_model else {}
        current_price = price_map.get(position.stock_id)

        dialog = CorporateActionDialog(
            ctx=CorporateActionDialogContext(
                ticker=ticker,
                stock_id=position.stock_id,
                current_qty=position.total_quantity,
                avg_cost=position.average_cost,
                total_cost=position.total_cost,
                current_price=current_price,
            ),
            parent=self._page,
        )
        if dialog.exec() != dialog.Accepted:
            return

        result_data = dialog.get_result()
        if not result_data:
            return

        try:
            action = self._register_action(result_data)
        except Exception as exc:
            QMessageBox.critical(self._page, L10N.KAYIT_HATASI, str(exc))
            return

        try:
            ca_result: CorporateActionResult = self._page.corporate_action_service.apply_action(
                action_id=action.id,
                current_price=current_price,
            )
        except Exception as exc:
            QMessageBox.critical(self._page, L10N.UYGULAMA_HATASI, str(exc))
            return

        self._refresh_prices_after_corporate_action(
            stock_id=result_data["stock_id"],
            ticker=ticker,
            ca_result=ca_result,
        )

    def _register_action(self, result_data: dict):
        if result_data["action_type"] == "BEDELSIZ":
            return self._page.corporate_action_service.register_bedelsiz(
                stock_id=result_data["stock_id"],
                ex_date=result_data["ex_date"],
                ratio=result_data["ratio"],
                notes=result_data.get("notes"),
            )
        return self._page.corporate_action_service.register_bedelli(BedelliSpec(
            stock_id=result_data["stock_id"],
            ex_date=result_data["ex_date"],
            ratio=result_data["ratio"],
            subscription_price=result_data["subscription_price"],
            notes=result_data.get("notes"),
        ))

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

        worker = Worker(_do_backfill)
        worker.signals.result.connect(lambda n: self._on_ca_backfill_success(n, ca_result))
        worker.signals.error.connect(lambda e: self._on_ca_backfill_error(e, ca_result))
        self._page.threadpool.start(worker)

    def _on_ca_backfill_success(self, updated_count: int, ca_result: CorporateActionResult) -> None:
        self._presenter.refresh_data()
        self._presenter.update_returns()
        type_label = L10N.BEDELSIZ if ca_result.action_type == ActionType.BEDELSIZ else L10N.BEDELLI
        Toast.info(
            self._page,
            L10N.SERMAYE_ARTIRIMI_UYGULANDI_TMPL.format(
                type=type_label,
                before=ca_result.shares_before,
                after=ca_result.shares_after,
                count=updated_count,
            ),
            duration_ms=6000,
            position="top",
        )

    def _on_ca_backfill_error(self, err_tuple, ca_result: CorporateActionResult) -> None:
        self._presenter.refresh_data()
        type_label = L10N.BEDELSIZ if ca_result.action_type == ActionType.BEDELSIZ else L10N.BEDELLI
        QMessageBox.warning(
            self._page,
            L10N.FIYAT_GUNCELLEME_UYARISI,
            L10N.SERMAYE_ARTIRIMI_FIYAT_HATASI_TMPL.format(type=type_label, exc=err_tuple[1])
            + L10N.FIYATLARI_DAHA_SONRA_MANUEL_OLARAK,
        )
