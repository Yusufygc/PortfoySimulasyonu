from __future__ import annotations
from src.ui.shared.locale_tr import L10N

import logging
from decimal import Decimal

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMessageBox, QDialog

from src.domain.models.trade import TradeSide
from src.ui.shared.market_session_confirm import confirm_market_session_if_needed
from src.ui.widgets.shared import Toast
from src.ui.worker import Worker

from .dashboard_corporate_action_actions import DashboardCorporateActionActions
from .dashboard_export_actions import DashboardExportActions

logger = logging.getLogger(__name__)


class DashboardActions:
    def __init__(self, page, presenter) -> None:
        self._page = page
        self._presenter = presenter
        self._export_actions = DashboardExportActions(page)
        self._corporate_action_actions = DashboardCorporateActionActions(page, presenter)

    def on_capital_management(self) -> None:
        dialog = self._page.capital_dialog_cls(self._page._capital, self._page)
        if dialog.exec_() != QDialog.Accepted:
            return
        result = dialog.get_result()
        if not result:
            return

        action = result["action"]
        amount = result["amount"]
        m_date = result.get("movement_date")
        m_time = result.get("movement_time")
        notes = result.get("notes") or (L10N.SERMAYE_EKLEME if action == "deposit" else L10N.SERMAYE_CEKME)
        try:
            if action == "deposit":
                self._page.cash_movement_service.add_deposit(
                    amount, movement_date=m_date, movement_time=m_time, notes=notes
                )
                QMessageBox.information(self._page, L10N.SUCCESS, L10N.SERMAYE_EKLENDI_TMPL.format(amount=f"{amount:,.2f}"))
            else:
                self._page.cash_movement_service.add_withdraw(
                    amount, movement_date=m_date, movement_time=m_time, notes=notes
                )
                QMessageBox.information(self._page, L10N.SUCCESS, L10N.SERMAYE_CEKILDI_TMPL.format(amount=f"{amount:,.2f}"))
        except ValueError as exc:
            QMessageBox.warning(self._page, L10N.WARNING, str(exc))
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
            QMessageBox.information(self._page, L10N.SUCCESS, L10N.ISLEM_BASARIYLA_EKLENDI)
            self._page._last_trade_result = result
        except ValueError as exc:
            QMessageBox.warning(self._page, L10N.GECERSIZ_ISLEM, str(exc))
        except Exception as exc:
            QMessageBox.critical(self._page, L10N.ERROR, L10N.ISLEM_KAYDEDILEMEDI_TMPL.format(exc=exc))

    def on_update_prices(self) -> None:
        self._page.btn_update_prices.setEnabled(False)
        self._page.btn_update_prices.setText(L10N.GUNCELLENIYOR)

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
        self._page.btn_update_prices.setText(L10N.FIYATLARI_GUNCELLE)

    def on_update_prices_success(self, result) -> None:
        price_update_result, _snapshot = result
        self._presenter.refresh_data()
        self._presenter.update_returns()
        if price_update_result.updated_count <= 0:
            skipped_reason = getattr(price_update_result, "skipped_reason", None)
            Toast.warning(
                self._page,
                skipped_reason or L10N.GUNCELLENECEK_FIYAT_BULUNAMADI,
                duration_ms=4000,
                position="top",
            )
            return

        self._page.record_last_update_time()
        self._page.show_last_update_toast_once(
            force=True,
            detail=L10N.HISSE_TARIHSEL_KAPANIS_VERISI_GUNCELLENDI_TMPL.format(count=price_update_result.updated_count),
        )

    def on_update_prices_error(self, err_tuple) -> None:
        QMessageBox.critical(self._page, L10N.ERROR, L10N.HATA_DETAYLARI_TMPL.format(exc=err_tuple[1]))

    def on_export_today(self) -> None:
        self._export_actions.on_export_today()

    def on_export_range(self) -> None:
        self._export_actions.on_export_range()

    def on_corporate_action(self, row: int, action_type_str: str) -> None:
        self._corporate_action_actions.on_corporate_action(row, action_type_str)

    def on_reset(self) -> None:
        reply = QMessageBox.question(
            self._page,
            L10N.PORTFOYU_SIFIRLA,
            L10N.TUM_VERILER_SILINECEK_EMIN_MISINIZ,
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
            QMessageBox.information(self._page, L10N.TAMAMLANDI, L10N.BASARIYLA_SIFIRLANDI)
        except Exception as exc:
            QMessageBox.critical(self._page, L10N.ERROR, L10N.HATA_TEK_SATIR_TMPL.format(exc=exc))
