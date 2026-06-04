from __future__ import annotations
from src.ui.shared.locale_tr import L10N

from decimal import Decimal

from PyQt5.QtWidgets import QMessageBox

from src.domain.models.trade import TradeSide
from src.ui.shared.market_session_confirm import confirm_market_session_if_needed


class StockTradeSubmitter:
    def __init__(self, page) -> None:
        self.page = page

    def submit(self, is_buy: bool, qty: int, price: float, date_sel, time_sel=None) -> None:
        page = self.page
        if not page.current_ticker:
            return

        trade_date = date_sel.toPyDate()
        trade_time = time_sel.toPyTime() if time_sel is not None else page.trade_form.time_edit.time().toPyTime()
        if not confirm_market_session_if_needed(
            page,
            page.market_session_service,
            trade_date,
            trade_time,
        ):
            return

        if page._is_model_context():
            self._submit_model_trade(is_buy, qty, price, trade_date, trade_time)
            return

        self._submit_dashboard_trade(is_buy, qty, price, trade_date, trade_time)

    def _submit_dashboard_trade(self, is_buy: bool, qty: int, price: float, trade_date, trade_time) -> None:
        page = self.page
        trade_side = TradeSide.BUY if is_buy else TradeSide.SELL
        try:
            result = page.trade_entry_service.submit_trade(
                ticker=page.current_ticker,
                stock_id=page.current_stock_id,
                side=trade_side,
                quantity=qty,
                price=Decimal(str(price)),
                trade_date=trade_date,
                trade_time=trade_time,
                name=page.current_ticker,
            )
            page.current_stock_id = result.stock_id
            page.current_ticker = result.ticker
            position_closed = (
                not is_buy
                and page.portfolio_service.get_position_quantity_as_of(page.current_stock_id) <= 0
            )
            message = L10N.POZISYON_KAPANDI_DASHBOARDA_DONULUYOR if position_closed else L10N.ISLEM_BASARIYLA_KAYDEDILDI
            QMessageBox.information(page, L10N.SUCCESS, message)
            page.refresh_data()
            page.trade_form.update_impact_preview(page.portfolio_service, page.current_stock_id)
            if position_closed:
                main_window = page.window()
                if hasattr(main_window, "show_dashboard"):
                    main_window.show_dashboard()
        except ValueError as exc:
            QMessageBox.warning(page, L10N.GECERSIZ_ISLEM, str(exc))
        except Exception as exc:
            QMessageBox.critical(page, L10N.ERROR, f"İşlem hatası: {exc}")

    def _submit_model_trade(self, is_buy: bool, qty: int, price: float, trade_date, trade_time) -> None:
        page = self.page
        portfolio_id = page._model_portfolio_id()
        if not portfolio_id or not page.model_portfolio_service:
            QMessageBox.critical(page, L10N.ERROR, L10N.MODEL_PORTFOY_BAGLAMI_BULUNAMADI)
            return

        side = "BUY" if is_buy else "SELL"
        try:
            trade = page.model_portfolio_service.add_trade_by_ticker(
                portfolio_id=portfolio_id,
                ticker=page.current_ticker,
                side=side,
                quantity=qty,
                price=Decimal(str(price)),
                trade_date=trade_date,
                trade_time=trade_time,
            )
            page.current_stock_id = trade.stock_id
            page._detail_context.setdefault("price_map", {})[trade.stock_id] = Decimal(str(price))
            position_closed = False
            if not is_buy and hasattr(page.model_portfolio_service, "get_position_quantity_as_of"):
                position_closed = page.model_portfolio_service.get_position_quantity_as_of(
                    portfolio_id,
                    page.current_stock_id,
                ) <= 0
            message = (
                L10N.POZISYON_KAPANDI_MODEL_PORTFOY_SAYFASINA
                if position_closed
                else L10N.MODEL_PORTFOY_ISLEMI_BASARIYLA_KAYDEDILDI
            )
            QMessageBox.information(page, L10N.SUCCESS, message)
            page.refresh_data()
            page._trigger_impact_update()
            if position_closed:
                main_window = page.window()
                if hasattr(main_window, "show_model_portfolios"):
                    main_window.show_model_portfolios()
        except ValueError as exc:
            QMessageBox.warning(page, L10N.GECERSIZ_ISLEM, str(exc))
        except Exception as exc:
            QMessageBox.critical(page, L10N.ERROR, f"Model portföy işlem hatası: {exc}")
