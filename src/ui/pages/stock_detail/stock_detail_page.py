from src.ui.shared.locale_tr import L10N
import logging
from datetime import time as dt_time
from decimal import Decimal
from typing import Optional

from src.qt_compat.qtcore import QDate, QTime, Qt, QThreadPool
from src.qt_compat.qtgui import QColor
from src.ui.worker import Worker
from src.qt_compat.qtwidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QScrollArea,
    QSizePolicy,
)

from src.domain.models.model_portfolio import ModelTradeSide
from src.domain.models.trade import TradeSide
from src.ui.formatters import display_ticker
from src.ui.pages.base_page import BasePage

from .stock_chart_widget import StockChartWidget
from .stock_stats_panel import StockStatsPanel
from .stock_trade_submitter import StockTradeSubmitter
from .trade_form_panel import TradeFormPanel

logger = logging.getLogger(__name__)


class StockDetailPage(BasePage):
    _LEFT_SCROLL_MIN_WIDTH = 620
    _LEFT_CONTENT_MIN_WIDTH = 875
    _HISTORY_VISIBLE_ROW_LIMIT = 10

    def __init__(
        self,
        container,
        price_lookup_func,
        parent=None,
    ):
        super().__init__(parent)
        self.container = container
        self.page_title = L10N.HISSE_DETAYI
        self.portfolio_service = container.portfolio_service
        self.stock_repo = container.stock_repo
        self.trade_entry_service = container.trade_entry_service
        self.model_portfolio_service = getattr(container, "model_portfolio_service", None)
        self.price_repo = getattr(container, "price_repo", None)
        self.market_client = getattr(container, "market_client", None)
        self.market_session_service = getattr(container, "bist_market_session_service", None)
        self.price_lookup_func = price_lookup_func

        self.current_ticker: Optional[str] = None
        self.current_stock_id: Optional[int] = None
        self.current_price: Optional[Decimal] = None
        self._detail_context: dict = {}
        self._trade_submitter = StockTradeSubmitter(self)
        self._init_ui()

    def _init_ui(self):
        # Create a scroll area for the left side content
        self.scroll_area = QScrollArea()
        self.scroll_area.setProperty("cssClass", "stockDetailScroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setMinimumWidth(self._LEFT_SCROLL_MIN_WIDTH)
        self.scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Create left content container widget
        left_content_widget = QWidget()
        left_content_widget.setMinimumWidth(self._LEFT_CONTENT_MIN_WIDTH)
        left_layout = QVBoxLayout(left_content_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_layout.setSpacing(15)

        # 1. Başlık (Breadcrumb ve Başlık satırı)
        top_layout = QVBoxLayout()
        top_layout.setSpacing(0)
        top_layout.setContentsMargins(0, 0, 0, 10)

        breadcrumb_row = QHBoxLayout()
        breadcrumb_row.setSpacing(10)
        
        from src.ui.widgets.shared.controls.animated_button import AnimatedButton
        self.btn_back = AnimatedButton(L10N.GERI)
        self.btn_back.setIconName("arrow-left", color="@COLOR_TEXT_PRIMARY", size=16)
        self.btn_back.setProperty("cssClass", "secondaryButton")
        self.btn_back.clicked.connect(self.navigate_back.emit)
        
        self.lbl_breadcrumb = QLabel(L10N.PORTFOY_1)
        self.lbl_breadcrumb.setProperty("cssClass", "breadcrumbText")
        
        breadcrumb_row.addWidget(self.btn_back)
        breadcrumb_row.addWidget(self.lbl_breadcrumb)
        breadcrumb_row.addStretch()
        
        top_layout.addLayout(breadcrumb_row)

        title_row = QHBoxLayout()
        title_row.setSpacing(15)

        self.lbl_ticker = QLabel("TICKER")
        self.lbl_ticker.setProperty("cssClass", "stockTitleLarge")
        self.lbl_name = QLabel(L10N.HISSE_ADI)
        self.lbl_name.setProperty("cssClass", "stockSubtitle")
        self.lbl_price = QLabel(L10N.TL_000)
        self.lbl_price.setProperty("cssClass", "stockPriceCurrent")

        title_row.addWidget(self.lbl_ticker)
        title_row.addWidget(self.lbl_name)
        title_row.addStretch()

        price_container = QVBoxLayout()
        price_label_caption = QLabel(L10N.GUNCEL_FIYAT)
        price_label_caption.setAlignment(Qt.AlignRight)
        price_label_caption.setProperty("cssClass", "stockPriceCaption")
        price_container.addWidget(price_label_caption)
        price_container.addWidget(self.lbl_price)
        title_row.addLayout(price_container)

        top_layout.addLayout(title_row)
        left_layout.addLayout(top_layout)

        # 2. Divider line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setProperty("cssClass", "horizontalDivider")
        left_layout.addWidget(line)

        # 3. Grafik
        self.chart_widget = StockChartWidget()
        self.chart_widget.setMinimumHeight(400)
        if self.market_client is not None:
            self.chart_widget.set_price_series_provider(self.market_client.get_price_series)
        left_layout.addWidget(self.chart_widget)

        # 4. Özet Kartları
        self.stats_panel = StockStatsPanel()
        left_layout.addWidget(self.stats_panel)

        # 5. İşlem Geçmişi Tablosu
        lbl_history = QLabel(L10N.ISLEM_GECMISI)
        lbl_history.setProperty("cssClass", "panelTitle")
        left_layout.addWidget(lbl_history)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels([L10N.TARIH, "İşlem", L10N.ADET, L10N.FIYAT, L10N.TUTAR])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setSelectionMode(QTableWidget.NoSelection)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setFocusPolicy(Qt.NoFocus)
        self.history_table.setShowGrid(False)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setProperty("cssClass", "stockHistoryTable")
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history_table.setMinimumHeight(150)
        self.history_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        left_layout.addWidget(self.history_table)

        # 6. Sermaye Tablosu
        lbl_corp_actions = QLabel(L10N.UYGULANAN_SERMAYE_ARTIRIMLARI)
        lbl_corp_actions.setProperty("cssClass", "panelTitle")
        left_layout.addWidget(lbl_corp_actions)

        self.corp_actions_table = QTableWidget()
        self.corp_actions_table.setColumnCount(3)
        self.corp_actions_table.setHorizontalHeaderLabels([L10N.TARIH, L10N.ISLEM_TURU, L10N.ARTIRIM_ORANI])
        self.corp_actions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.corp_actions_table.setSelectionMode(QTableWidget.NoSelection)
        self.corp_actions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.corp_actions_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.corp_actions_table.setFocusPolicy(Qt.NoFocus)
        self.corp_actions_table.setShowGrid(False)
        self.corp_actions_table.setAlternatingRowColors(True)
        self.corp_actions_table.setProperty("cssClass", "stockHistoryTable")
        self.corp_actions_table.verticalHeader().setVisible(False)
        self.corp_actions_table.setMinimumHeight(150)
        self.corp_actions_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout.addWidget(self.corp_actions_table)

        # Set the scroll area content widget
        self.scroll_area.setWidget(left_content_widget)

        # Right sidebar (trade form)
        self.trade_form = TradeFormPanel()
        self.trade_form.trade_submitted.connect(self._on_submit_trade)
        self.trade_form.spin_qty.valueChanged.connect(self._trigger_impact_update)
        self.trade_form.spin_price.valueChanged.connect(self._trigger_impact_update)
        self.trade_form.date_edit.dateChanged.connect(self._trigger_impact_update)
        self.trade_form.time_edit.timeChanged.connect(self._trigger_impact_update)
        self.trade_form.btn_buy_mode.toggled.connect(self._trigger_impact_update)

        self.content_wrapper = QWidget()
        self.content_wrapper.setProperty("cssClass", "stockDetailContentWrapper")
        # Main horizontal content layout inside a horizontally scrollable wrapper.
        content_layout = QHBoxLayout(self.content_wrapper)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        content_layout.addWidget(self.scroll_area, 1)
        content_layout.addWidget(self.trade_form, 0)
        wrapper_min_width = (
            self._LEFT_CONTENT_MIN_WIDTH
            + content_layout.spacing()
            + self.trade_form.minimumWidth()
        )
        self.content_wrapper.setMinimumWidth(wrapper_min_width)
        self.content_wrapper.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.content_scroll_area = QScrollArea()
        self.content_scroll_area.setProperty("cssClass", "stockDetailContentScroll")
        self.content_scroll_area.setWidgetResizable(True)
        self.content_scroll_area.setFrameShape(QFrame.NoFrame)
        self.content_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.content_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content_scroll_area.setWidget(self.content_wrapper)
        self.content_scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.main_layout.addWidget(self.content_scroll_area, 1)

    def _trigger_impact_update(self):
        self._sync_quantity_limits()
        if self._is_model_context():
            detail = self._model_position_detail()
            self.trade_form.update_impact_preview_for_position(
                detail.get("quantity", 0) if detail else 0,
                detail.get("avg_cost", Decimal("0")) if detail else Decimal("0"),
            )
            return
        cash_balance = self.portfolio_service.get_cash_balance() if hasattr(self.portfolio_service, "get_cash_balance") else None
        self.trade_form.update_impact_preview(self.portfolio_service, self.current_stock_id, cash_balance=cash_balance)

    def set_stock(self, ticker: str, stock_id: Optional[int] = None, context: Optional[dict] = None):
        self.current_ticker = ticker
        self.current_stock_id = stock_id
        self._detail_context = context or {}
        display = display_ticker(ticker)
        self.lbl_ticker.setText(display)
        breadcrumb_root = L10N.MODEL_PORTFOY if self._is_model_context() else L10N.PORTFOY_2
        self.lbl_breadcrumb.setText(f"{breadcrumb_root} > {display}")

        if stock_id:
            stock = self.stock_repo.get_stock_by_id(stock_id)
            if stock:
                self.lbl_name.setText(stock.name or "")

        # Initial UI states during loading
        self.current_price = None
        self.lbl_price.setText(L10N.FIYAT_YUKLENIYOR)
        self.chart_widget.draw_empty_chart(L10N.YUKLENIYOR)
        self.stats_panel.clear_stats()

        self._update_price_info()

    def refresh_data(self):
        if not self.current_ticker:
            return
        model_detail = self._model_position_detail() if self._is_model_context() else None
        self.chart_widget.draw_chart(
            self.current_ticker,
            self.current_stock_id,
            self.current_price,
            None if self._is_model_context() else self.portfolio_service,
            price_repo=self.price_repo,
            average_cost=model_detail.get("avg_cost") if model_detail else None,
        )
        if self._is_model_context():
            self.stats_panel.update_model_stats(
                self.model_portfolio_service,
                self._model_portfolio_id(),
                self.current_stock_id,
                self.current_price,
                self._model_price_map(),
            )
        else:
            self.stats_panel.update_stats(self.portfolio_service, self.current_stock_id, self.current_price)
        self._load_history()
        self._load_corp_actions()

    def _update_price_info(self):
        if not self.current_ticker or not self.price_lookup_func:
            # If no ticker or lookup function, refresh with empty state/fallback directly
            self.refresh_data()
            self._trigger_impact_update()
            return

        ticker = self.current_ticker

        def _fetch_price():
            return self.price_lookup_func(ticker)

        worker = Worker(_fetch_price)

        def on_result(result):
            # Check for ticker mismatch to avoid race condition
            if ticker != self.current_ticker:
                logger.info("Fiyat yukleme sonucu yoksayildi, ticker degisti: %s -> %s", ticker, self.current_ticker)
                return
            if result:
                self.current_price = result.price
                self.lbl_price.setText(f"TL {self.current_price:,.2f}")
                self.trade_form.set_price(float(self.current_price))
            else:
                self.current_price = None
                self.lbl_price.setText("TL -")
            self.refresh_data()
            self._trigger_impact_update()

        def on_error(exc_info):
            if ticker != self.current_ticker:
                return
            logger.error("Asenkron fiyat yukleme hatasi (%s): %s", ticker, exc_info)
            self.current_price = None
            self.lbl_price.setText("TL -")
            self.refresh_data()
            self._trigger_impact_update()

        worker.signals.result.connect(on_result)
        worker.signals.error.connect(on_error)

        QThreadPool.globalInstance().start(worker)

    def _load_history(self):
        if not self.current_stock_id:
            self.history_table.setRowCount(0)
            self._update_history_table_height()
            return

        if self._is_model_context():
            portfolio_id = self._model_portfolio_id()
            trades = (
                self.model_portfolio_service.get_stock_trades(portfolio_id, self.current_stock_id)
                if self.model_portfolio_service and portfolio_id
                else []
            )
        else:
            trades = self.portfolio_service.get_trades_for_stock(self.current_stock_id)
        trades.sort(
            key=lambda trade: (
                trade.trade_date,
                getattr(trade, "trade_time", None) or dt_time.min,
                getattr(trade, "id", None) or 0,
            ),
            reverse=True,
        )

        self.history_table.setRowCount(len(trades))
        for row_index, trade in enumerate(trades):
            self.history_table.setItem(row_index, 0, self._history_item(trade.trade_date.strftime("%d.%m.%Y")))
            is_buy = trade.side in (TradeSide.BUY, ModelTradeSide.BUY)
            type_str = "ALIM" if is_buy else "SATIM"
            type_color = QColor("#10b981" if is_buy else "#ef4444")
            type_item = self._history_item(type_str, type_color)
            self.history_table.setItem(row_index, 1, type_item)
            
            # Use original trade quantity/price for history display in UI
            qty = getattr(trade, "original_quantity", trade.quantity)
            price = getattr(trade, "original_price", trade.price)
            total = price * Decimal(qty)

            self.history_table.setItem(row_index, 2, self._history_item(str(qty)))
            self.history_table.setItem(row_index, 3, self._history_item(f"TL {price:,.2f}"))
            self.history_table.setItem(row_index, 4, self._history_item(f"TL {total:,.2f}"))
        self._update_history_table_height()

    def _update_history_table_height(self) -> None:
        row_count = self.history_table.rowCount()
        visible_rows = min(max(row_count, 1), self._HISTORY_VISIBLE_ROW_LIMIT)
        default_row_height = self.history_table.verticalHeader().defaultSectionSize()
        row_height = sum(
            self.history_table.rowHeight(row) or default_row_height
            for row in range(min(row_count, visible_rows))
        )
        if row_count == 0:
            row_height = default_row_height
        header_height = self.history_table.horizontalHeader().height() or self.history_table.horizontalHeader().sizeHint().height()
        frame_height = self.history_table.frameWidth() * 2
        table_height = header_height + row_height + frame_height + 2

        if row_count > self._HISTORY_VISIBLE_ROW_LIMIT:
            self.history_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        else:
            self.history_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history_table.setFixedHeight(table_height)
        self.history_table.updateGeometry()

    @staticmethod
    def _history_item(text: str, foreground: Optional[QColor] = None) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setFlags(Qt.ItemIsEnabled)
        item.setTextAlignment(Qt.AlignCenter)
        if foreground is not None:
            item.setForeground(foreground)
        return item

    def _load_corp_actions(self):
        if not self.current_stock_id or self._is_model_context():
            self.corp_actions_table.setRowCount(0)
            return

        corporate_action_service = getattr(self.container, "corporate_action_service", None)
        if not corporate_action_service:
            self.corp_actions_table.setRowCount(0)
            return

        try:
            # Sadece uygulanmis aksiyonlari listele
            actions = [
                a for a in corporate_action_service.get_by_stock(self.current_stock_id)
                if a.applied
            ]
            actions.sort(key=lambda a: a.ex_date, reverse=True)
            
            self.corp_actions_table.setRowCount(len(actions))
            for row_index, action in enumerate(actions):
                self.corp_actions_table.setItem(row_index, 0, self._history_item(action.ex_date.strftime("%d.%m.%Y")))
                type_str = "BEDELSIZ" if action.action_type == "BEDELSIZ" else "BEDELLI"
                self.corp_actions_table.setItem(row_index, 1, self._history_item(type_str))
                self.corp_actions_table.setItem(row_index, 2, self._history_item(f"%{action.ratio_percent:.0f}"))
        except Exception as exc:
            logger.error("Kurumsal islemleri yukleme hatasi: %s", exc)
            self.corp_actions_table.setRowCount(0)

    def _on_submit_trade(self, is_buy: bool, qty: int, price: float, date_sel: QDate, time_sel: QTime | None = None):
        self._trade_submitter.submit(is_buy, qty, price, date_sel, time_sel)

    def _sync_quantity_limits(self) -> None:
        if self.trade_form.btn_buy_mode.isChecked():
            self.trade_form.spin_qty.setMaximum(1_000_000)
            return
        available = 0
        as_of = (self.trade_form.date_edit.date().toPyDate(), self.trade_form.time_edit.time().toPyTime())
        if self._is_model_context():
            portfolio_id = self._model_portfolio_id()
            if (
                portfolio_id
                and self.current_stock_id
                and self.model_portfolio_service
                and hasattr(self.model_portfolio_service, "get_position_quantity_as_of")
            ):
                available = self.model_portfolio_service.get_position_quantity_as_of(
                    portfolio_id,
                    self.current_stock_id,
                    as_of=as_of,
                )
        elif self.current_stock_id and hasattr(self.portfolio_service, "get_position_quantity_as_of"):
            as_of = (self.trade_form.date_edit.date().toPyDate(), self.trade_form.time_edit.time().toPyTime())
            available = self.portfolio_service.get_position_quantity_as_of(self.current_stock_id, as_of=as_of)
        self.trade_form.spin_qty.setMaximum(max(1, available))

    def _is_model_context(self) -> bool:
        return self._detail_context.get("source") == "model_portfolio"

    def _model_portfolio_id(self) -> Optional[int]:
        value = self._detail_context.get("portfolio_id")
        return int(value) if value is not None else None

    def _model_price_map(self) -> dict[int, Decimal]:
        return dict(self._detail_context.get("price_map") or {})

    def _model_position_detail(self) -> dict | None:
        portfolio_id = self._model_portfolio_id()
        if not self._is_model_context() or not portfolio_id or not self.model_portfolio_service or not self.current_stock_id:
            return None
        price_map = self._model_price_map()
        if self.current_price is not None:
            price_map[self.current_stock_id] = self.current_price
        positions = self.model_portfolio_service.get_positions_with_details(portfolio_id, price_map)
        return next((pos for pos in positions if pos.get("stock_id") == self.current_stock_id), None)
