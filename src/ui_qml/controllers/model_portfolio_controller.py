"""
Model Portföy Controller — QML tarafına portföy CRUD, alım-satım,
sermaye yönetimi ve fiyat güncelleme kapasitesi sağlar.
"""
from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, time as dt_time, datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Any

from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer

from src.ui_qml.last_update_store import LastUpdateStore, format_last_update

logger = logging.getLogger(__name__)


def _fmt_currency(value: Decimal | float | None) -> str:
    """Standart Türkçe para formatı: 1.000.000,00 ₺ veya -62.608,18 ₺."""
    if value is None:
        return "0,00 ₺"
    try:
        val = float(value)
        sign = "-" if val < 0 else ""
        abs_val = abs(val)
        formatted = f"{abs_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{sign}{formatted} ₺"
    except Exception:
        return f"{value} ₺"


def _fmt_pct(value: Decimal | float | None) -> str:
    """Standart getiri yüzdesi formatı: +%1,07 veya -%30,96."""
    if value is None:
        return "%0,00"
    try:
        val = float(value)
        abs_val = abs(val)
        formatted = f"{abs_val:.2f}".replace(".", ",")
        if val > 0:
            return f"+%{formatted}"
        elif val < 0:
            return f"-%{formatted}"
        return f"%{formatted}"
    except Exception:
        return f"%{value}"


def _display_ticker(ticker: str) -> str:
    text = (ticker or "").strip()
    return text[:-3] if text.upper().endswith(".IS") else text


class ModelPortfolioController(QObject):
    """QML ↔ Python köprüsü: Model Portföy yönetimi."""

    # --- Signals ---
    portfolioListChanged = Signal()
    currentPortfolioChanged = Signal()
    summaryChanged = Signal()
    positionsChanged = Signal()
    loadingChanged = Signal()
    operationResult = Signal(bool, str)  # success, message
    excelExported = Signal(bool, str)    # success, message
    lastUpdateChanged = Signal()

    _asyncExportFinished = Signal(bool, str)

    def __init__(self, container=None, parent=None):
        super().__init__(parent)
        self._container = container
        self._service = getattr(container, "model_portfolio_service", None) if container else None
        self._lookup = getattr(container, "stock_lookup_service", None) if container else None
        self._store = LastUpdateStore()
        self._live_updated_count: int = 0
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

        # Event bus
        if container and hasattr(container, "event_bus") and container.event_bus:
            try:
                container.event_bus.prices_updated.connect(self._on_prices_updated_event)
            except Exception as exc:
                logger.warning("EventBus bağlantı hatası: %s", exc)

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

    def _get_last_update_text(self):
        if self._current_portfolio_id <= 0:
            return ""
        return format_last_update(self._store.model_portfolio_last_update(self._current_portfolio_id))

    lastUpdateText = Property(str, _get_last_update_text, notify=lastUpdateChanged)

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

    def _get_has_positions(self):
        return self._has_positions

    hasPositions = Property(bool, _get_has_positions, notify=positionsChanged)

    def _get_is_loading(self):
        return self._is_loading

    isLoading = Property(bool, _get_is_loading, notify=loadingChanged)

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
            self.operationResult.emit(False, f"Sıra kaydedilemedi: {exc}")
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
                    self._update_view()
            elif self._portfolio_list:
                self.selectPortfolio(self._portfolio_list[0]["portfolioId"])
        except Exception as exc:
            logger.error("Portföy listesi yüklenemedi: %s", exc)
            self.operationResult.emit(False, f"Veri yükleme hatası: {exc}")

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
            self.lastUpdateChanged.emit()
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
            self.operationResult.emit(False, "Portföy adı boş olamaz")
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
            self.operationResult.emit(True, f"'{name}' portföyü oluşturuldu")
        except Exception as exc:
            self.operationResult.emit(False, f"Portföy oluşturulamadı: {exc}")

    @Slot(int, str, str)
    def updatePortfolio(self, portfolio_id: int, name: str, description: str):
        """Portföy bilgilerini günceller."""
        if not self._service:
            return
        name = name.strip()
        if not name:
            self.operationResult.emit(False, "Portföy adı boş olamaz")
            return
        try:
            self._service.update_portfolio(
                portfolio_id=portfolio_id,
                name=name,
                description=description.strip() or None,
            )
            self.refreshData()
            self.operationResult.emit(True, "Portföy güncellendi")
        except Exception as exc:
            self.operationResult.emit(False, f"Portföy güncellenemedi: {exc}")

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
            self.operationResult.emit(True, "Portföy silindi")
        except Exception as exc:
            self.operationResult.emit(False, f"Portföy silinemedi: {exc}")

    @Slot(str, str, int, float, str, str)
    def addTrade(self, ticker: str, side: str, quantity: int, price: float,
                 trade_date_str: str, trade_time_str: str):
        """Portföye yeni alım/satım işlemi ekler."""
        if not self._service or self._current_portfolio_id <= 0:
            self.operationResult.emit(False, "Portföy seçili değil")
            return
        try:
            from src.application.services.planning.model_portfolio_trade_service import ModelTradeInput
            trade_date = date.fromisoformat(trade_date_str) if trade_date_str else date.today()
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
            action = "alındı" if side.upper() == "BUY" else "satıldı"
            self.refreshData()
            self.operationResult.emit(True, f"{quantity} lot {_display_ticker(ticker)} {action}")
        except ValueError as exc:
            self.operationResult.emit(False, str(exc))
        except Exception as exc:
            self.operationResult.emit(False, f"İşlem gerçekleştirilemedi: {exc}")

    @Slot(str, result=float)
    def getLatestPriceForTicker(self, ticker: str) -> float:
        """Hisse kodunun son bilinen fiyatını döner."""
        raw = (ticker or "").strip().upper()
        if not raw:
            return 0.0
        stock = self._lookup.find_stock(raw) if self._lookup else None
        if stock and stock.id:
            price = self._resolve_prices([stock.id]).get(stock.id)
            if price and price > 0:
                return float(price)
        return 0.0

    @Slot(int)
    def deleteTrade(self, trade_id: int):
        """Bir işlemi siler."""
        if not self._service:
            return
        try:
            self._service.delete_trade(trade_id)
            self.refreshData()
            self.operationResult.emit(True, "İşlem silindi")
        except Exception as exc:
            self.operationResult.emit(False, f"İşlem silinemedi: {exc}")

    @Slot(str, float, str, str, str)
    def addCapitalMovement(self, movement_type: str, amount: float,
                           move_date_str: str, move_time_str: str, notes: str):
        """Sermaye hareketi ekler (yatır/çek)."""
        if not self._service or self._current_portfolio_id <= 0:
            self.operationResult.emit(False, "Portföy seçili değil")
            return
        try:
            from src.application.services.planning.model_portfolio_trade_service import CapitalMovementSpec
            move_date = date.fromisoformat(move_date_str) if move_date_str else date.today()
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
            action = "yatırıldı" if movement_type.upper() == "DEPOSIT" else "çekildi"
            self.refreshData()
            self.operationResult.emit(True, f"₺{amount:,.2f} {action}")
        except ValueError as exc:
            self.operationResult.emit(False, str(exc))
        except Exception as exc:
            self.operationResult.emit(False, f"Sermaye hareketi kaydedilemedi: {exc}")

    @Slot()
    def refreshPrices(self):
        """Fiyatları arka planda günceller."""
        if not self._service or self._current_portfolio_id <= 0:
            return
        self._is_loading = True
        self.loadingChanged.emit()
        threading.Thread(target=self._refresh_prices_worker, daemon=True).start()

    # =====================================================================
    #  Internal helpers
    # =====================================================================

    def _refresh_prices_worker(self):
        """Arka plan iş parçacığında fiyat güncelleme: önce canlı fiyatlar çekilir, sonra fiyat haritası yeniden okunur."""
        try:
            portfolio_id = self._current_portfolio_id
            live_service = getattr(self._container, "live_price_refresh_service", None) if self._container else None
            self._live_updated_count = -1  # -1: canlı servis yok (yalnızca veritabanından okunur)
            if live_service is not None:
                result = live_service.refresh_active_prices(f"model:{portfolio_id}")
                self._live_updated_count = int(getattr(result, "updated_count", 0) or 0)
            self._load_price_map(portfolio_id)
            QTimer.singleShot(0, self._on_prices_refreshed_success)
        except Exception as exc:
            logger.error("Fiyat güncelleme hatası: %s", exc)
            QTimer.singleShot(0, lambda: self._on_prices_refreshed_error(str(exc)))

    def _on_prices_refreshed_success(self):
        self._is_loading = False
        self.loadingChanged.emit()
        self._update_view()
        if self._live_updated_count < 0:
            self.operationResult.emit(True, "Fiyatlar güncellendi")
        elif self._live_updated_count == 0:
            self.operationResult.emit(False, "Güncellenecek fiyat bulunamadı.")
        else:
            self._store.save_model_portfolio_last_update(self._current_portfolio_id)
            self.lastUpdateChanged.emit()
            self.operationResult.emit(True, f"{self._live_updated_count} hissenin fiyatı güncellendi.")

    def _on_prices_refreshed_error(self, error_msg: str):
        self._is_loading = False
        self.loadingChanged.emit()
        self.operationResult.emit(False, f"Fiyat güncelleme hatası: {error_msg}")

    def _on_prices_updated_event(self, prices: Dict[int, Decimal]):
        """EventBus üzerinden gelen fiyat güncellemelerini işler."""
        if self._current_portfolio_id <= 0 or not prices:
            return
        try:
            positions = self._service.get_positions(self._current_portfolio_id)
            relevant = {sid: p for sid, p in prices.items() if sid in positions}
            if relevant:
                self._current_price_map.update(relevant)
                self._update_view()
        except Exception as exc:
            logger.warning("EventBus fiyat güncelleme hatası: %s", exc)

    def _load_price_map(self, portfolio_id: int):
        """Seçili portföyün hisse fiyatlarını yükler."""
        try:
            positions = self._service.get_positions(portfolio_id)
            stock_ids = sorted(positions.keys())
            self._current_price_map = self._resolve_prices(stock_ids)
        except Exception as exc:
            logger.warning("Fiyat haritası yüklenemedi: %s", exc)
            self._current_price_map = {}

    def _resolve_prices(self, stock_ids: list) -> Dict[int, Decimal]:
        """Güncel fiyat: önce çözümleyici (canlı/kapanış), yoksa canlı önbellek, eksikler için son kapanış."""
        price_map: Dict[int, Decimal] = {}
        resolver = getattr(self._container, "current_price_resolver", None) if self._container else None
        if resolver is not None:
            price_map.update(resolver.price_map(stock_ids))
        elif self._lookup:
            price_map.update(self._lookup.get_latest_price_map(stock_ids))
        if self._lookup:
            for sid in [sid for sid in stock_ids if sid not in price_map]:
                close = self._lookup.get_previous_close(sid)
                if close is not None:
                    price_map[sid] = close
        return price_map

    def _update_view(self):
        """Seçili portföyün özet ve pozisyon bilgilerini günceller."""
        if not self._service or self._current_portfolio_id <= 0:
            return
        try:
            self._update_summary()
            self._update_positions()
        except Exception as exc:
            logger.error("Görünüm güncellenemedi: %s", exc)

    def _update_summary(self):
        summary = self._service.get_portfolio_summary(
            self._current_portfolio_id, self._current_price_map
        )
        net_capital = summary.get("net_capital", summary.get("initial_cash", Decimal("0")))
        remaining_cash = summary.get("remaining_cash", Decimal("0"))
        total_value = summary.get("total_value", Decimal("0"))
        profit_loss = summary.get("profit_loss", Decimal("0"))
        profit_loss_pct = summary.get("profit_loss_pct", Decimal("0"))

        self._summary_net_capital = _fmt_currency(net_capital)
        self._summary_remaining_cash = _fmt_currency(remaining_cash)
        self._summary_remaining_cash_raw = remaining_cash
        self._summary_total_value = _fmt_currency(total_value)
        self._summary_profit_loss = _fmt_currency(profit_loss)
        self._summary_profit_loss_pct = float(profit_loss_pct)

        rounded = round(profit_loss, 2)
        if rounded > 0:
            self._summary_profit_loss_state = "positive"
        elif rounded < 0:
            self._summary_profit_loss_state = "negative"
        else:
            self._summary_profit_loss_state = "neutral"

        self.summaryChanged.emit()

    def _update_positions(self):
        positions = self._service.get_positions_with_details(
            self._current_portfolio_id, self._current_price_map
        )
        # Previous close map for daily change
        prev_close_map = self._build_previous_close_map(positions)

        self._positions_list = []
        for pos in positions:
            stock_id = pos.get("stock_id")
            current_price = pos.get("current_price")
            avg_cost = pos.get("avg_cost")
            quantity = pos.get("quantity", 0)
            total_cost = pos.get("total_cost")
            current_value = pos.get("current_value")
            profit_loss = pos.get("profit_loss")

            # Daily change %
            prev_close = prev_close_map.get(stock_id)
            daily_change_pct = None
            if current_price and prev_close and prev_close > 0:
                daily_change_pct = float(((current_price - prev_close) / prev_close) * 100)

            # Total change %
            total_change_pct = None
            if current_price and avg_cost and avg_cost > 0:
                total_change_pct = float(((current_price - avg_cost) / avg_cost) * 100)

            # Weight
            total_val = Decimal("0")
            try:
                summary = self._service.get_portfolio_summary(
                    self._current_portfolio_id, self._current_price_map
                )
                total_val = summary.get("total_value", Decimal("0"))
            except Exception:
                pass

            weight = 0.0
            if current_value and total_val and total_val > 0:
                weight = float((current_value / total_val) * 100)

            self._positions_list.append({
                "stockId": stock_id,
                "ticker": _display_ticker(pos.get("ticker", "")),
                "companyName": pos.get("name", ""),
                "quantity": quantity,
                "avgCost": float(avg_cost) if avg_cost else 0.0,
                "currentPrice": float(current_price) if current_price else 0.0,
                "currentValue": float(current_value) if current_value else 0.0,
                "totalCost": float(total_cost) if total_cost else 0.0,
                "profitLoss": float(profit_loss) if profit_loss else 0.0,
                "dailyChangePct": daily_change_pct if daily_change_pct is not None else 0.0,
                "totalChangePct": total_change_pct if total_change_pct is not None else 0.0,
                "weight": weight,
                "profitLossFormatted": _fmt_currency(profit_loss) if profit_loss else "₺0,00",
                "dailyChangeFormatted": _fmt_pct(Decimal(str(daily_change_pct))) if daily_change_pct is not None else "-",
                "totalChangeFormatted": _fmt_pct(Decimal(str(total_change_pct))) if total_change_pct is not None else "-",
            })

        self._has_positions = len(self._positions_list) > 0
        self.positionsChanged.emit()

    def _build_previous_close_map(self, positions: list) -> Dict[int, Decimal]:
        """Pozisyondaki hisselerin bir önceki kapanış fiyatlarını çeker."""
        result: Dict[int, Decimal] = {}
        if not self._lookup:
            return result
        try:
            stock_ids = [pos.get("stock_id") for pos in positions if pos.get("stock_id")]
            resolver = getattr(self._container, "current_price_resolver", None) if self._container else None
            resolved_map = resolver.resolve(stock_ids) if resolver is not None else {}
            for sid in stock_ids:
                resolved = resolved_map.get(sid)
                if resolved is not None:
                    # Önceki kapanış, güncel fiyatın gününden önceki son kapanıştır
                    previous = resolver.previous_close(sid, resolved)
                    if previous is not None:
                        result[sid] = previous
                    continue
                prev_close = self._lookup.get_previous_close(sid)
                if prev_close is not None:
                    result[sid] = prev_close
        except Exception as exc:
            logger.warning("Previous close map hatası: %s", exc)
        return result

    def _clear_current(self):
        """Seçili portföy bilgilerini temizler."""
        self._current_portfolio_id = -1
        self._current_portfolio_name = ""
        self._current_portfolio_desc = ""
        self.currentPortfolioChanged.emit()
        self.lastUpdateChanged.emit()

        self._summary_net_capital = "₺0,00"
        self._summary_remaining_cash = "₺0,00"
        self._summary_total_value = "₺0,00"
        self._summary_profit_loss = "₺0,00"
        self._summary_profit_loss_pct = 0.0
        self._summary_profit_loss_state = "neutral"
        self._summary_remaining_cash_raw = Decimal("0")
        self.summaryChanged.emit()

        self._positions_list = []
        self._has_positions = False
        self.positionsChanged.emit()

    # -------------------------------------------------------------------------
    # EXCEL RAPOR DIŞA AKTARIMI
    # -------------------------------------------------------------------------

    @Slot()
    def exportToExcel(self) -> None:
        """Mevcut seçili model portföyü Excel'e aktarır."""
        if self._current_portfolio_id < 0:
            self.operationResult.emit(False, "Dışa aktarmak için bir model portföy seçilmelidir.")
            return
        self.exportPortfolioToExcel(self._current_portfolio_id)

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
        from datetime import datetime as _dt

        def parse(text):
            for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
                try:
                    return _dt.strptime((text or "").strip(), fmt).date()
                except ValueError:
                    continue
            return None

        if self._current_portfolio_id < 0:
            self.operationResult.emit(False, "Dışa aktarmak için bir model portföy seçilmelidir.")
            return
        first = self._service.get_first_trade_date(self._current_portfolio_id) if self._service else None
        start = parse(start_text) or first
        end = parse(end_text) or date.today()
        if (start_text.strip() and parse(start_text) is None) or (end_text.strip() and parse(end_text) is None):
            self.operationResult.emit(False, "Tarih biçimi geçersiz. Biçim: GG.AA.YYYY")
            return
        if start is None:
            self.operationResult.emit(False, "Bu model portföyde işlem bulunamadı.")
            return
        if start > end:
            self.operationResult.emit(False, "Başlangıç tarihi bitiş tarihinden büyük olamaz.")
            return
        self._executor.submit(
            self._run_history_export_worker, self._current_portfolio_id, start, end, file_path.strip(), bool(append)
        )

    def _run_history_export_worker(self, portfolio_id: int, start, end, file_path: str, append: bool = False) -> None:
        try:
            from pathlib import Path
            from src.application.services.reporting.daily_history_models import ExportMode

            excel_service = getattr(self._container, "model_portfolio_excel_export_service", None) if self._container else None
            if excel_service is None:
                self._asyncExportFinished.emit(False, "Excel dışa aktarım servisi yapılandırılmamış.")
                return
            target = Path(file_path) if file_path else Path.home() / "Desktop" / f"Model_Portfoy_{portfolio_id}.xlsx"
            if target.suffix.lower() != ".xlsx":
                target = target.with_suffix(".xlsx")
            target.parent.mkdir(parents=True, exist_ok=True)
            excel_service.export_model_portfolio_history(
                portfolio_id=portfolio_id, start_date=start, end_date=end, file_path=target,
                mode=ExportMode.APPEND if append else ExportMode.OVERWRITE,
            )
            self._asyncExportFinished.emit(True, f"Model portföy raporu oluşturuldu:\n{target.name}")
        except Exception as exc:
            logger.exception("Model portföy tarihsel Excel export hatası: %s", exc)
            self._asyncExportFinished.emit(False, f"Excel raporu oluşturulamadı: {exc}")

    @Slot(int)
    def exportPortfolioToExcel(self, portfolio_id: int) -> None:
        """Belirtilen model portföyü Excel dosyası olarak kaydeder."""
        self._executor.submit(self._run_excel_export_worker, portfolio_id)

    def _run_excel_export_worker(self, portfolio_id: int) -> None:
        try:
            from pathlib import Path
            from datetime import datetime
            desktop = Path.home() / "Desktop"
            out_dir = desktop if desktop.exists() else Path("reports").resolve()
            out_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            port = self._service.get_portfolio_by_id(portfolio_id) if self._service else None
            p_name = port.name if port else f"Portfoy_{portfolio_id}"
            safe_name = "".join(c for c in p_name if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
            target_file = out_dir / f"Model_Portfoy_{safe_name}_{timestamp}.xlsx"

            excel_service = getattr(self._container, "model_portfolio_excel_export_service", None) if self._container else None
            if excel_service and self._service:
                positions_dict = self._service.get_positions(portfolio_id)
                # Fiyat haritası oluştur
                resolved_prices = self._resolve_prices(list(positions_dict.keys()))
                price_map = {
                    sid: resolved_prices.get(sid) or getattr(pos, "average_cost", None) or Decimal("100.0")
                    for sid, pos in positions_dict.items()
                }

                excel_service.export_model_portfolio(
                    portfolio_id=portfolio_id,
                    price_map=price_map,
                    file_path=target_file,
                )
                self._asyncExportFinished.emit(True, f"Model portföy Excel raporu oluşturuldu:\n{target_file.name}")
            else:
                self._asyncExportFinished.emit(False, "Excel dışa aktarım servisi yapılandırılmamış.")
        except Exception as exc:
            logger.exception("Model portföy Excel export hatası: %s", exc)
            self._asyncExportFinished.emit(False, f"Excel raporu oluşturulamadı: {exc}")

    def _on_export_finished(self, success: bool, message: str) -> None:
        self.excelExported.emit(success, message)
        self.operationResult.emit(success, message)

