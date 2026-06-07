# src/ui/pages/model_portfolio/utils/model_portfolio_actions.py

from __future__ import annotations
from src.ui.shared.confirm_dialog import ask_confirm
from src.ui.shared.locale_tr import L10N

from typing import TYPE_CHECKING

from PyQt5.QtWidgets import QDialog, QMessageBox  # noqa: F401 (test monkeypatches QMessageBox here)

from src.ui.formatters import display_ticker
from src.ui.shared.market_session_confirm import confirm_market_session_if_needed
from src.ui.widgets.model_portfolio import CapitalMovementDialog, PortfolioInputDialog, TradeInputDialog
from src.ui.widgets.dashboard import NewStockTradeDialog
from src.ui.widgets.shared import Toast
from src.ui.worker import Worker
from src.ui.shared.price_event_publisher import publish_prices_updated
from PyQt5.QtCore import QTimer

if TYPE_CHECKING:
    from src.ui.pages.model_portfolio.model_portfolio_page import ModelPortfolioPage


class ModelPortfolioActions:
    """Model Portföy sayfası için CRUD ve alım-satım eylemlerini yönetir."""

    def __init__(self, page: ModelPortfolioPage) -> None:
        self.page = page

    def on_new_portfolio(self) -> None:
        dialog = PortfolioInputDialog(self.page)
        if dialog.exec_() != QDialog.Accepted:
            return
        result = dialog.get_result()
        if not result:
            return
        try:
            portfolio = self.page.model_portfolio_service.create_portfolio(**result)
            if portfolio and portfolio.id is not None:
                self.page.current_portfolio_id = portfolio.id
            self.page._load_portfolios()
            Toast.success(self.page, L10N.PORTFOY_OLUSTURULDU_TMPL.format(name=result['name']))
        except Exception as exc:
            Toast.error(self.page, L10N.PORTFOY_OLUSTURULAMADI_TMPL.format(exc=exc))

    def on_edit_portfolio(self) -> None:
        if self.page.current_portfolio_id is None:
            return
        portfolio = self.page.list_panel.current_portfolio()
        if not portfolio:
            return
        dialog = PortfolioInputDialog(self.page, portfolio)
        if dialog.exec_() != QDialog.Accepted:
            return
        result = dialog.get_result()
        if not result:
            return
        try:
            self.page.model_portfolio_service.update_portfolio(
                portfolio_id=self.page.current_portfolio_id, **result
            )
            self.page._load_portfolios()
            self.page.lbl_portfolio_name.setText(result["name"])
            self.page._update_view()
            Toast.success(self.page, L10N.PORTFOY_GUNCELLENDI)
        except Exception as exc:
            Toast.error(self.page, L10N.PORTFOY_GUNCELLENEMEDI_TMPL.format(exc=exc))

    def on_delete_portfolio(self) -> None:
        if self.page.current_portfolio_id is None:
            return
        if not ask_confirm(
            self.page,
            L10N.PORTFOY_SIL,
            L10N.BU_PORTFOYU_SILMEK_ISTEDIGINIZDEN_EMIN,
        ):
            return
        try:
            self.page.model_portfolio_service.delete_portfolio(self.page.current_portfolio_id)
            self.page.settings_manager.remove_portfolio_settings(self.page.current_portfolio_id)
            self.page.current_portfolio_id = None
            self.page.current_price_map = {}
            self.page._last_update_toast_shown_for = None
            self.page._load_portfolios()
            self.page._clear_right_panel()
            Toast.success(self.page, L10N.PORTFOY_SILINDI)
        except Exception as exc:
            Toast.error(self.page, L10N.PORTFOY_SILINEMEDI_TMPL.format(exc=exc))

    def on_portfolios_reordered(self, ordered_ids: list[int]) -> None:
        try:
            self.page.model_portfolio_service.reorder_portfolios(ordered_ids)
        except Exception as exc:
            Toast.error(self.page, L10N.SIRALAMA_GUNCELLENEMEDI_TMPL.format(exc=exc))

    def on_capital_movement(self) -> None:
        if self.page.current_portfolio_id is None:
            return
        summary = self.page.model_portfolio_service.get_portfolio_summary(
            self.page.current_portfolio_id,
            self.page.current_price_map,
        )
        dialog = CapitalMovementDialog(
            current_cash=summary["remaining_cash"],
            net_capital=summary["net_capital"],
            parent=self.page,
        )
        if dialog.exec_() != QDialog.Accepted:
            return
        result = dialog.get_result()
        if not result:
            return
        try:
            self.page.model_portfolio_service.add_capital_movement(
                portfolio_id=self.page.current_portfolio_id,
                **result,
            )
            self.page._load_portfolios()
            self.page._update_view()
            action = L10N.EKLENDI if result["movement_type"] == "DEPOSIT" else L10N.CEKILDI
            Toast.success(self.page, L10N.SERMAYE_HAREKETI_KAYDEDILDI_TMPL.format(amount=f"{result['amount']:,.2f}", action=action))
        except ValueError as exc:
            Toast.warning(self.page, str(exc))
        except Exception as exc:
            Toast.error(self.page, L10N.SERMAYE_HAREKETI_KAYDEDILEMEDI_TMPL.format(exc=exc))

    def on_trade(self, side: str | None = None) -> None:
        if self.page.current_portfolio_id is None:
            return
        dialog = NewStockTradeDialog(
            parent=self.page,
            price_lookup_func=self.page.price_lookup_func,
            lot_size=1,
        )
        if side == "BUY":
            dialog.btn_buy_mode.setChecked(True)
        elif side == "SELL":
            dialog.btn_sell_mode.setChecked(True)

        if dialog.exec_() != QDialog.Accepted:
            return
        result = dialog.get_result()
        if not result:
            return
        effective_side = result.get("side") or side or "BUY"
        if not confirm_market_session_if_needed(
            self.page,
            self.page.market_session_service,
            result["trade_date"],
            result.get("trade_time"),
        ):
            return
        try:
            self.page.model_portfolio_service.add_trade_by_ticker(
                portfolio_id=self.page.current_portfolio_id,
                ticker=result["ticker"],
                side=effective_side,
                quantity=result["quantity"],
                price=result["price"],
                trade_date=result["trade_date"],
                trade_time=result["trade_time"],
            )
            self.page._load_portfolios()
            self.page._update_view()
            action = L10N.ALINDI if effective_side == "BUY" else L10N.SATILDI
            Toast.success(self.page, L10N.ISLEM_GERCEKLESTI_TMPL.format(qty=result['quantity'], ticker=display_ticker(result['ticker']), action=action))
        except ValueError as exc:
            Toast.warning(self.page, str(exc))
        except Exception as exc:
            Toast.error(self.page, L10N.ISLEM_GERCEKLESTIRILEMEDI_TMPL.format(exc=exc))

    def on_update_prices(self) -> None:
        self._update_timeout_timer = QTimer(self.page)
        self._update_timeout_timer.setSingleShot(True)
        self._update_timeout_timer.timeout.connect(self._finish_update_prices)
        self._update_timeout_timer.start(120_000)

        worker = Worker(self.page.price_updater.refresh_prices)
        worker.signals.result.connect(self._on_update_prices_success)
        worker.signals.error.connect(self._on_update_prices_error)
        worker.signals.finished.connect(self._finish_update_prices)
        self.page.threadpool.start(worker)

    def _finish_update_prices(self) -> None:
        timer = getattr(self, "_update_timeout_timer", None)
        if timer and timer.isActive():
            timer.stop()
        self.page.btn_refresh.setEnabled(True)
        self.page.btn_refresh.setText(L10N.FIYAT_GUNCELLE)

    def _on_update_prices_success(self, result) -> None:
        updated_count, event_prices = result
        
        if event_prices:
            publish_prices_updated(getattr(self.page.container, "event_bus", None), event_prices)
            
        self.page._update_view()

        if updated_count <= 0:
            Toast.warning(
                self.page,
                L10N.GUNCELLENECEK_FIYAT_BULUNAMADI,
                duration_ms=self.page.LAST_UPDATE_TOAST_DURATION_MS,
                position="top",
            )
            return

        self.page.record_last_update_time()
        self.page.show_last_update_toast_once(
            force=True,
            detail=L10N.HISSE_FIYAT_GUNCELLENDI_TMPL.format(count=updated_count),
        )

    def _on_update_prices_error(self, err_tuple) -> None:
        Toast.error(self.page, L10N.FIYAT_GUNCELLEME_HATASI_TMPL.format(exc=err_tuple[1]))
