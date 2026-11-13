"""
Model Portföy Controller — QML tarafına portföy CRUD, alım-satım,
sermaye yönetimi ve fiyat güncelleme kapasitesi sağlar.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, time as dt_time
from decimal import Decimal
from typing import Any, Dict, List

from PySide6.QtCore import QObject, Signal, Property, Slot
from src.ui_qml.controllers.date_input import parse_date_text
from src.ui_qml.controllers.model_portfolio_export import resolve_range, run_history_export
from src.ui_qml.controllers.model_portfolio_valuation import ModelPortfolioValuation, display_ticker, empty_summary
from src.ui_qml.controllers.deps import ServiceView
from src.ui_qml.messages import msg
from src.ui_qml.presenters.formatting import tr_number


logger = logging.getLogger(__name__)


def _entry_date(text: str) -> date:
    """Formdaki tarih; boşsa bugün, geçersizse kullanıcıya gösterilecek `ValueError`."""
    if not (text or "").strip():
        return date.today()
    parsed = parse_date_text(text)
    if parsed is None:
        raise ValueError(msg("model_portfolio.tarih_bicimi_gecersiz_bicim_gg_aa"))
    return parsed


class ModelPortfolioController(QObject):
    """QML ↔ Python köprüsü: Model Portföy yönetimi."""
    REQUIRES = (
        "model_portfolio_excel_export_service", "model_portfolio_service", "position_query_service",
        "stock_lookup_service",
    )

    # --- Signals ---
    portfolioListChanged = Signal()
    currentPortfolioChanged = Signal()
    summaryChanged = Signal()
    positionsChanged = Signal()
    loadingChanged = Signal()
    operationResult = Signal(bool, str)  # success, message
    excelExported = Signal(bool, str)    # success, message

    _asyncExportFinished = Signal(bool, str)

    def __init__(self, container=None, parent=None):
        super().__init__(parent)
        self._deps = ServiceView(container, self.REQUIRES)
        self._service = self._deps.model_portfolio_service
        self._lookup = self._deps.stock_lookup_service
        self._valuation = ModelPortfolioValuation(self._service, self._deps.position_query_service)
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ModelPortWorker")
        self._asyncExportFinished.connect(self._on_export_finished)

        # State
        self._portfolio_list: List[Dict[str, Any]] = []
        self._current_portfolio_id: int = -1
        self._current_portfolio_name: str = ""
        self._current_portfolio_desc: str = ""

        # Summary
        self._summary_net_capital: str = "₺0,00"
        self._summary_remaining_cash: str = "₺0,00"
        self._summary_total_value: str = "₺0,00"
        self._summary_profit_loss: str = "₺0,00"
        self._summary_profit_loss_pct: float = 0.0
        self._summary_profit_loss_state: str = "neutral"
        self._summary_remaining_cash_raw: Decimal = Decimal("0")

        # Positions
        self._positions_list: List[Dict[str, Any]] = []
        self._has_positions: bool = False
        self._is_loading: bool = False

        # Price map
        self._current_price_map: Dict[int, Decimal] = {}

    # =====================================================================
    #  Properties (QML'e açılan)
    # =====================================================================

    def _get_portfolio_list(self):
        return self._portfolio_list

    portfolioList = Property("QVariantList", _get_portfolio_list, notify=portfolioListChanged)

    def _get_current_portfolio_id(self):
        return self._current_portfolio_id

    currentPortfolioId = Property(int, _get_current_portfolio_id, notify=currentPortfolioChanged)

    def _get_current_portfolio_name(self):
        return self._current_portfolio_name

    currentPortfolioName = Property(str, _get_current_portfolio_name, notify=currentPortfolioChanged)

    def _get_current_portfolio_desc(self):
        return self._current_portfolio_desc

    currentPortfolioDesc = Property(str, _get_current_portfolio_desc, notify=currentPortfolioChanged)

    # Summary properties
    def _get_summary_net_capital(self):
        return self._summary_net_capital

    summaryNetCapital = Property(str, _get_summary_net_capital, notify=summaryChanged)

    def _get_summary_remaining_cash(self):
        return self._summary_remaining_cash

    summaryRemainingCash = Property(str, _get_summary_remaining_cash, notify=summaryChanged)

    def _get_summary_total_value(self):
        return self._summary_total_value

    summaryTotalValue = Property(str, _get_summary_total_value, notify=summaryChanged)

    def _get_summary_profit_loss(self):
        return self._summary_profit_loss

    summaryProfitLoss = Property(str, _get_summary_profit_loss, notify=summaryChanged)

    def _get_summary_profit_loss_pct(self):
        return self._summary_profit_loss_pct

    summaryProfitLossPct = Property(float, _get_summary_profit_loss_pct, notify=summaryChanged)

    def _get_summary_profit_loss_state(self):
        return self._summary_profit_loss_state

    summaryProfitLossState = Property(str, _get_summary_profit_loss_state, notify=summaryChanged)

    def _get_summary_remaining_cash_raw(self):
        return float(self._summary_remaining_cash_raw)

    summaryRemainingCashRaw = Property(float, _get_summary_remaining_cash_raw, notify=summaryChanged)

    # Positions
    def _get_positions_list(self):
        return self._positions_list

    positionsList = Property("QVariantList", _get_positions_list, notify=positionsChanged)

    hasPositions = Property(bool, lambda self: self._has_positions, notify=positionsChanged)

    isLoading = Property(bool, lambda self: self._is_loading, notify=loadingChanged)

    # =====================================================================
    #  Slots (QML'den çağrılan)
    # =====================================================================

    @Slot()
    @Slot(int, int)
    def movePortfolio(self, from_index: int, to_index: int) -> None:
        """Model portföyü sürükle-bırak ile yeni sıraya taşır ve sırayı kalıcı kaydeder."""
        size = len(self._portfolio_list)
        if not self._service or not (0 <= from_index < size and 0 <= to_index < size) or from_index == to_index:
            return
        reordered = list(self._portfolio_list)
        reordered.insert(to_index, reordered.pop(from_index))
        try:
            self._service.reorder_portfolios([p["portfolioId"] for p in reordered])
        except Exception as exc:
            logger.error("Model portföy sırası kaydedilemedi: %s", exc)
            self.operationResult.emit(False, msg("model_portfolio.sira_kaydedilemedi", exc=exc))
            return
        self._portfolio_list = reordered
        self.portfolioListChanged.emit()

    def refreshData(self):
        """Portföy listesini veritabanından yeniden yükler."""
        if not self._service:
            return
        try:
            portfolios = self._service.get_all_portfolios()
            self._portfolio_list = [
                {
                    "portfolioId": p.id,
                    "name": p.name,
                    "description": p.description or "",
                    "positionCount": self._service.get_active_position_count(p.id),
                }
                for p in portfolios
            ]
            self.portfolioListChanged.emit()

            # Mevcut seçili portföy hâlâ mevcutsa koru, değilse ilk portföyü seç
            if self._current_portfolio_id > 0:
                ids = [p["portfolioId"] for p in self._portfolio_list]
                if self._current_portfolio_id not in ids:
                    if self._portfolio_list:
                        self.selectPortfolio(self._portfolio_list[0]["portfolioId"])
                    else:
                        self._clear_current()
                else:
                    self._load_price_map(self._current_portfolio_id)
                    self._update_view()
            elif self._portfolio_list:
                self.selectPortfolio(self._portfolio_list[0]["portfolioId"])
        except Exception as exc:
            logger.error("Portföy listesi yüklenemedi: %s", exc)
            self.operationResult.emit(False, msg("model_portfolio.veri_yukleme_hatasi", exc=exc))

    @Slot(int)
    def selectPortfolio(self, portfolio_id: int):
        """Bir portföyü seçip detaylarını yükler."""
        if not self._service:
            return
        try:
            portfolio = self._service.get_portfolio_by_id(portfolio_id)
            if portfolio is None:
                return
            self._current_portfolio_id = portfolio.id
            self._current_portfolio_name = portfolio.name
            self._current_portfolio_desc = portfolio.description or ""
            self.currentPortfolioChanged.emit()
            self._load_price_map(portfolio_id)
            self._update_view()
        except Exception as exc:
            logger.error("Portföy seçilemedi: %s", exc)

    @Slot(str, str, float)
    def createPortfolio(self, name: str, description: str, initial_cash: float):
        """Yeni portföy oluşturur."""
        if not self._service:
            return
        name = name.strip()
        if not name:
            self.operationResult.emit(False, msg("model_portfolio.portfoy_adi_bos_olamaz"))
            return
        try:
            portfolio = self._service.create_portfolio(
                name=name,
                description=description.strip() or None,
                initial_cash=Decimal(str(initial_cash)),
            )
            if portfolio and portfolio.id is not None:
                self._current_portfolio_id = portfolio.id
            self.refreshData()
            self.operationResult.emit(True, msg("model_portfolio.portfoyu_olusturuldu", name=name))
        except Exception as exc:
            self.operationResult.emit(False, msg("model_portfolio.portfoy_olusturulamadi", exc=exc))

    @Slot(int, str, str)
    def updatePortfolio(self, portfolio_id: int, name: str, description: str):
        """Portföy bilgilerini günceller."""
        if not self._service:
            return
        name = name.strip()
        if not name:
            self.operationResult.emit(False, msg("model_portfolio.portfoy_adi_bos_olamaz"))
            return
        try:
            self._service.update_portfolio(
                portfolio_id=portfolio_id,
                name=name,
                description=description.strip() or None,
            )
            self.refreshData()
            self.operationResult.emit(True, msg("model_portfolio.portfoy_guncellendi"))
        except Exception as exc:
            self.operationResult.emit(False, msg("model_portfolio.portfoy_guncellenemedi", exc=exc))

    @Slot(int)
    def deletePortfolio(self, portfolio_id: int):
        """Portföyü siler."""
        if not self._service:
            return
        try:
            self._service.delete_portfolio(portfolio_id)
            if self._current_portfolio_id == portfolio_id:
                self._current_portfolio_id = -1
            self.refreshData()
            self.operationResult.emit(True, msg("model_portfolio.portfoy_silindi"))
        except Exception as exc:
            self.operationResult.emit(False, msg("model_portfolio.portfoy_silinemedi", exc=exc))

    @Slot(str, str, int, float, str, str)
    def addTrade(self, ticker: str, side: str, quantity: int, price: float,
                 trade_date_str: str, trade_time_str: str):
        """Portföye yeni alım/satım işlemi ekler."""
        if not self._service or self._current_portfolio_id <= 0:
            self.operationResult.emit(False, msg("model_portfolio.portfoy_secili_degil"))
            return
        try:
            from src.application.services.planning.model_portfolio_trade_service import ModelTradeInput
            trade_date = _entry_date(trade_date_str)
            trade_time = None
            if trade_time_str:
                parts = trade_time_str.split(":")
                trade_time = dt_time(int(parts[0]), int(parts[1]))

            self._service.add_trade_by_ticker(
                portfolio_id=self._current_portfolio_id,
                ticker=ticker.strip(),
                trade_input=ModelTradeInput(
                    side=side.upper(),
                    quantity=quantity,
                    price=Decimal(str(price)),
                    trade_date=trade_date,
                    trade_time=trade_time,
                ),
            )
            action = msg("model_portfolio.alindi") if side.upper() == "BUY" else msg("model_portfolio.satildi")
            self.refreshData()
            self.operationResult.emit(True, f"{quantity} lot {display_ticker(ticker)} {action}")
        except ValueError as exc:
            self.operationResult.emit(False, str(exc))
        except Exception as exc:
            self.operationResult.emit(False, msg("model_portfolio.islem_gerceklestirilemedi", exc=exc))

    @Slot(str, result=float)
    def getLatestPriceForTicker(self, ticker: str) -> float:
        """Hisse kodunun son bilinen fiyatını döner."""
        raw = (ticker or "").strip().upper()
        if not raw:
            return 0.0
        stock = self._lookup.find_stock(raw) if self._lookup else None
        if stock and stock.id:
            price = self._valuation.resolve_prices([stock.id]).get(stock.id)
            if price and price > 0:
                return float(price)
        return 0.0

    @Slot(str, float, str, str, str)
    def addCapitalMovement(self, movement_type: str, amount: float,
                           move_date_str: str, move_time_str: str, notes: str):
        """Sermaye hareketi ekler (yatır/çek)."""
        if not self._service or self._current_portfolio_id <= 0:
            self.operationResult.emit(False, msg("model_portfolio.portfoy_secili_degil"))
            return
        try:
            from src.application.services.planning.model_portfolio_trade_service import CapitalMovementSpec
            move_date = _entry_date(move_date_str)
            move_time = None
            if move_time_str:
                parts = move_time_str.split(":")
                move_time = dt_time(int(parts[0]), int(parts[1]))

            self._service.add_capital_movement(
                CapitalMovementSpec(
                    portfolio_id=self._current_portfolio_id,
                    movement_type=movement_type.upper(),
                    amount=Decimal(str(amount)),
                    movement_date=move_date,
                    movement_time=move_time,
                    notes=notes.strip() or None,
                )
            )
            action = msg("model_portfolio.yatirildi") if movement_type.upper() == "DEPOSIT" else msg("model_portfolio.cekildi")
            self.refreshData()
            self.operationResult.emit(True, f"₺{tr_number(amount)} {action}")
        except ValueError as exc:
            self.operationResult.emit(False, str(exc))
        except Exception as exc:
            self.operationResult.emit(False, f"Sermaye hareketi kaydedilemedi: {exc}")

    @Slot()
    def reloadPrices(self) -> None:
        """Fiyatlar veritabanında değişti (`PriceRefreshController.pricesChanged`): seçili portföy yeniden okunur."""
        if not self._service or self._current_portfolio_id <= 0:
            return
        self._load_price_map(self._current_portfolio_id)
        self._update_view()

    # =====================================================================
    #  Internal helpers
    # =====================================================================

    def _load_price_map(self, portfolio_id: int):
        """Seçili portföyün hisse fiyatlarını yükler."""
        self._current_price_map = self._valuation.price_map(portfolio_id)

    def _update_view(self):
        """Seçili portföyün özet ve pozisyon bilgilerini günceller."""
        if not self._service or self._current_portfolio_id <= 0:
            return
        try:
            s = self._valuation.summary(self._current_portfolio_id, self._current_price_map)
            self._summary_net_capital = s["net_capital"]
            self._summary_remaining_cash = s["remaining_cash"]
            self._summary_remaining_cash_raw = s["remaining_cash_raw"]
            self._summary_total_value = s["total_value"]
            self._summary_profit_loss = s["profit_loss"]
            self._summary_profit_loss_pct = s["profit_loss_pct"]
            self._summary_profit_loss_state = s["state"]
            self.summaryChanged.emit()
            self._positions_list = self._valuation.position_rows(self._current_portfolio_id, self._current_price_map)
            self._has_positions = len(self._positions_list) > 0
            self.positionsChanged.emit()
        except Exception as exc:
            logger.error("Görünüm güncellenemedi: %s", exc)

    def _clear_current(self):
        """Seçili portföy bilgilerini temizler."""
        self._current_portfolio_id = -1
        self._current_portfolio_name = ""
        self._current_portfolio_desc = ""
        self.currentPortfolioChanged.emit()

        s = empty_summary()
        self._summary_net_capital, self._summary_remaining_cash = s["net_capital"], s["remaining_cash"]
        self._summary_remaining_cash_raw, self._summary_total_value = s["remaining_cash_raw"], s["total_value"]
        self._summary_profit_loss, self._summary_profit_loss_pct = s["profit_loss"], s["profit_loss_pct"]
        self._summary_profit_loss_state = s["state"]
        self.summaryChanged.emit()

        self._positions_list = []
        self._has_positions = False
        self.positionsChanged.emit()

    # -------------------------------------------------------------------------
    # EXCEL RAPOR DIŞA AKTARIMI
    # -------------------------------------------------------------------------

    @Slot(result=str)
    def firstTradeDateText(self) -> str:
        """Seçili model portföyün ilk işlem tarihi (GG.AA.YYYY), yoksa boş."""
        if self._current_portfolio_id < 0 or not self._service:
            return ""
        try:
            first = self._service.get_first_trade_date(self._current_portfolio_id)
        except Exception:
            first = None
        return first.strftime("%d.%m.%Y") if first else ""

    @Slot(str, str, str, bool)
    def exportHistoryToFile(self, start_text: str, end_text: str, file_path: str, append: bool = False) -> None:
        """Seçili model portföyün tarihsel (günlük) Excel raporunu seçilen aralık ve dosyaya yazar."""
        if self._current_portfolio_id < 0:
            self.operationResult.emit(False, msg("model_portfolio.disa_aktarmak_icin_bir_model_portfoy"))
            return
        first = self._service.get_first_trade_date(self._current_portfolio_id) if self._service else None
        start, end, error = resolve_range(start_text, end_text, first)
        if error:
            self.operationResult.emit(False, error)
            return
        excel_service = self._deps.model_portfolio_excel_export_service
        portfolio_id, path, do_append = self._current_portfolio_id, file_path.strip(), bool(append)
        self._executor.submit(
            lambda: self._asyncExportFinished.emit(*run_history_export(excel_service, portfolio_id, start, end, path, do_append))
        )

    def _on_export_finished(self, success: bool, message: str) -> None:
        self.excelExported.emit(success, message)
        self.operationResult.emit(success, message)

