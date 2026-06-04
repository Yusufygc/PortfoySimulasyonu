# src/ui/pages/model_portfolio/utils/model_portfolio_actions.py

from __future__ import annotations
from src.ui.shared.locale_tr import L10N

from typing import TYPE_CHECKING

from PyQt5.QtWidgets import QDialog, QMessageBox

from src.ui.formatters import display_ticker
from src.ui.shared.market_session_confirm import confirm_market_session_if_needed
from src.ui.widgets.model_portfolio import CapitalMovementDialog, PortfolioInputDialog, TradeInputDialog
from src.ui.widgets.shared import Toast

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
            Toast.success(self.page, f"'{result['name']}' portföyü oluşturuldu.")
        except Exception as exc:
            Toast.error(self.page, f"Portföy oluşturulamadı: {exc}")

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
            Toast.error(self.page, f"Portföy güncellenemedi: {exc}")

    def on_delete_portfolio(self) -> None:
        if self.page.current_portfolio_id is None:
            return
        reply = QMessageBox.question(
            self.page,
            L10N.PORTFOY_SIL,
            L10N.BU_PORTFOYU_SILMEK_ISTEDIGINIZDEN_EMIN,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            self.page.model_portfolio_service.delete_portfolio(self.page.current_portfolio_id)
            if "settings_manager" not in self.page.__dict__:
                from src.ui.pages.model_portfolio.utils.portfolio_settings import PortfolioSettingsManager
                self.page.settings_manager = PortfolioSettingsManager()
            self.page.settings_manager.remove_portfolio_settings(self.page.current_portfolio_id)
            self.page.current_portfolio_id = None
            self.page.current_price_map = {}
            self.page._last_update_toast_shown_for = None
            self.page._load_portfolios()
            self.page._clear_right_panel()
            Toast.success(self.page, L10N.PORTFOY_SILINDI)
        except Exception as exc:
            Toast.error(self.page, f"Portföy silinemedi: {exc}")

    def on_portfolios_reordered(self, ordered_ids: list[int]) -> None:
        try:
            self.page.model_portfolio_service.reorder_portfolios(ordered_ids)
        except Exception as exc:
            Toast.error(self.page, f"Sıralama güncellenemedi: {exc}")

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
            action = L10N.EKLENDI if result["movement_type"] == "DEPOSIT" else "cekildi"
            Toast.success(self.page, f"Sermaye hareketi kaydedildi: {result['amount']:,.2f} TL {action}.")
        except ValueError as exc:
            Toast.warning(self.page, str(exc))
        except Exception as exc:
            Toast.error(self.page, f"Sermaye hareketi kaydedilemedi: {exc}")

    def on_trade(self, side: str) -> None:
        if self.page.current_portfolio_id is None:
            return
        dialog = TradeInputDialog(side, self.page.price_lookup_func, self.page)
        if dialog.exec_() != QDialog.Accepted:
            return
        result = dialog.get_result()
        if not result:
            return
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
                side=side,
                quantity=result["quantity"],
                price=result["price"],
                trade_date=result["trade_date"],
                trade_time=result["trade_time"],
            )
            self.page._load_portfolios()
            self.page._update_view()
            action = "alındı" if side == "BUY" else "satıldı"
            Toast.success(self.page, f"{result['quantity']} lot {display_ticker(result['ticker'])} {action}.")
        except ValueError as exc:
            Toast.warning(self.page, str(exc))
        except Exception as exc:
            Toast.error(self.page, f"İşlem gerçekleştirilemedi: {exc}")
