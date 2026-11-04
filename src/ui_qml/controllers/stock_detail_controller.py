"""
StockDetailController — BIST Hisse Detayı, Pozisyon Analitiği, İşlem Geçmişi ve Excel Rapor Denetleyicisi.

Sorumluluklar:
- Seçili hissenin portföy pozisyon metriklerini (Lot, Ortalama Maliyet, Güncel Değer, Net K/Z, Ağırlık) hesaplama
- Bu hisseye ait tüm alış/satış işlem geçmişini (Trade History) getirme
- Varsa uygulanan sermaye artırımlarını (Bedelsiz / Bedelli) listeleme
- Hızlı alım/satım emir girişi ve maliyet etki önizlemesi
- Hissenin işlem ve pozisyon dökümünü openpyxl ile profesyonelce formatlanmış Excel (.xlsx) olarak dışa aktarma
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time as dt_time
from decimal import Decimal
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.domain.models.trade import TradeSide
from src.domain.models.trade_impact import INSUFFICIENT_CASH, INSUFFICIENT_LOTS, OrderSpec, preview_order
from src.domain.ticker import clean_ticker
from src.domain.market_clock import market_now, market_time, market_today
from src.ui_qml.messages import msg
from src.ui_qml.presenters.formatting import tr_number, tr_pct
from src.ui_qml.controllers.stock_detail_actions import StockDetailActionsMixin
from src.ui_qml.controllers.stock_detail_loader import StockDetailLoaderMixin

logger = logging.getLogger(__name__)


def parse_trade_moment(date_str: str, time_str: str) -> tuple[date, dt_time]:
    """Form alanlarından işlem anı. Boş tarih bugün; boş saat bugün için şimdi, geçmiş gün için 12:00.

    Geçersiz biçim veya gelecek tarih için ValueError (kullanıcıya gösterilecek mesajla) fırlatır."""
    today = market_today()
    text = (date_str or "").strip()
    try:
        trade_date = datetime.strptime(text, "%Y-%m-%d").date() if text else today
    except ValueError:
        raise ValueError(msg("stock_detail.tarih_bicimi_gecersiz_ornek_2026_10")) from None
    if trade_date > today:
        raise ValueError(msg("stock_detail.gelecek_tarihli_islem_girilemez"))

    text = (time_str or "").strip()
    if not text:
        return trade_date, (market_time() if trade_date == today else dt_time(12, 0))
    try:
        trade_time = datetime.strptime(text, "%H:%M").time()
    except ValueError:
        raise ValueError(msg("stock_detail.saat_bicimi_gecersiz_ornek_14_30")) from None
    if trade_date == today and trade_time > market_now().time():
        raise ValueError(msg("stock_detail.gelecek_saatli_islem_girilemez"))
    return trade_date, trade_time


class StockDetailController(StockDetailLoaderMixin, StockDetailActionsMixin, QObject):
    """QML StockDetailModal / StockDetailView için ViewModel denetleyicisi."""

    # QML Property Değişim Sinyalleri
    stockChanged = Signal()
    tradesChanged = Signal()
    corpActionsChanged = Signal()
    loadingChanged = Signal(bool)
    statusMessageChanged = Signal(str)

    # Bildirim ve Aksiyon Sinyalleri
    tradeExecuted = Signal(bool, str)        # success, message
    excelExported = Signal(bool, str)        # success, message

    # Dahili Asenkron Qt Sinyalleri
    _asyncDataReady = Signal(dict)
    _asyncTradeResult = Signal(bool, str)
    _asyncExportResult = Signal(bool, str)

    def __init__(self, container=None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._container = container
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="StockDetailWorker")

        # Durum Değişkenleri
        self._is_open: bool = False
        self._is_loading: bool = False
        self._trade_pending: bool = False  # emir işçide sürerken ikinci tıklamayı reddeder
        self._status_message: str = ""

        # Hisse & Pozisyon Bilgileri
        self._ticker: str = ""
        self._raw_ticker: str = ""
        self._stock_id: Optional[int] = None
        self._company_name: str = ""
        self._sector: str = ""
        self._context_type: str = "main"   # "main" veya "model"
        self._context_id: int = 0          # model portfolio id (varsa)
        self._portfolio_name: str = msg("stock_detail.ana_portfoy")

        # Metrikler
        self._current_price: float = 0.0
        self._daily_diff: float = 0.0
        self._quantity: int = 0
        self._avg_cost: float = 0.0
        self._market_value: float = 0.0
        self._unrealized_pnl: float = 0.0
        self._unrealized_pnl_pct: float = 0.0
        self._portfolio_weight_pct: float = 0.0
        self._cash: Optional[float] = None

        # Tablo Verileri
        self._trades_list: List[Dict[str, Any]] = []
        self._corp_actions_list: List[Dict[str, Any]] = []

        # Sinyal Bağlantıları
        self._asyncDataReady.connect(self._on_data_ready)
        self._asyncTradeResult.connect(self._on_trade_result)
        self._asyncExportResult.connect(self._on_export_result)

    # -------------------------------------------------------------------------
    # QML PROPERTIES
    # -------------------------------------------------------------------------

    @Property(bool, notify=stockChanged)
    def isOpen(self) -> bool:
        return self._is_open

    @Property(bool, notify=stockChanged)
    def isModelContext(self) -> bool:
        return self._context_type == "model"

    @Property(bool, notify=loadingChanged)
    def isLoading(self) -> bool:
        return self._is_loading

    @Property(str, notify=statusMessageChanged)
    def statusMessage(self) -> str:
        return self._status_message

    @Property(str, notify=stockChanged)
    def ticker(self) -> str:
        return self._ticker

    @Property(str, notify=stockChanged)
    def companyName(self) -> str:
        return self._company_name or self._ticker

    @Property(str, notify=stockChanged)
    def sector(self) -> str:
        return self._sector

    @Property(str, notify=stockChanged)
    def portfolioName(self) -> str:
        return self._portfolio_name

    @Property(float, notify=stockChanged)
    def currentPrice(self) -> float:
        return self._current_price

    @Property(str, notify=stockChanged)
    def currentPriceStr(self) -> str:
        return f"₺{tr_number(self._current_price)}" if self._current_price > 0 else "₺-"

    @Property(float, notify=stockChanged)
    def dailyDiff(self) -> float:
        return self._daily_diff

    @Property(str, notify=stockChanged)
    def dailyDiffStr(self) -> str:
        return tr_pct(self._daily_diff, with_sign=True)

    @Property(bool, notify=stockChanged)
    def isDailyPositive(self) -> bool:
        return self._daily_diff >= 0

    @Property(int, notify=stockChanged)
    def quantity(self) -> int:
        return self._quantity

    @Property(str, notify=stockChanged)
    def quantityStr(self) -> str:
        return f"{tr_number(self._quantity, 0)} Lot"

    @Property(float, notify=stockChanged)
    def avgCost(self) -> float:
        return self._avg_cost

    @Property(str, notify=stockChanged)
    def avgCostStr(self) -> str:
        return f"₺{tr_number(self._avg_cost)}" if self._avg_cost > 0 else "₺0,00"

    @Property(float, notify=stockChanged)
    def marketValue(self) -> float:
        return self._market_value

    @Property(str, notify=stockChanged)
    def marketValueStr(self) -> str:
        return f"₺{tr_number(self._market_value)}"

    @Property(str, notify=stockChanged)
    def unrealizedPnlStr(self) -> str:
        sign = "+" if self._unrealized_pnl >= 0 else "-"
        return f"{sign}₺{tr_number(abs(self._unrealized_pnl))}"

    @Property(str, notify=stockChanged)
    def unrealizedPnlPctStr(self) -> str:
        return tr_pct(self._unrealized_pnl_pct, with_sign=True)

    @Property(bool, notify=stockChanged)
    def isPnlPositive(self) -> bool:
        return self._unrealized_pnl >= 0

    @Property("QVariantList", notify=tradesChanged)
    def tradesList(self) -> List[Dict[str, Any]]:
        return self._trades_list

    @Property("QVariantList", notify=corpActionsChanged)
    def corpActionsList(self) -> List[Dict[str, Any]]:
        return self._corp_actions_list

    # -------------------------------------------------------------------------
    # PUBLIC SLOTS
    # -------------------------------------------------------------------------

    @Slot(str)
    def openStock(self, ticker: str) -> None:
        """Ana portföy bağlamında hisse detayını açar."""
        self.openStockWithContext(ticker, "main", 0)

    @Slot(str, str, int)
    def openStockWithContext(self, ticker: str, context_type: str, context_id: int) -> None:
        """Belirtilen bağlamda (ana portföy veya model portföy) hisse detayını açar."""
        clean = clean_ticker(ticker)
        if not clean:
            return

        self._ticker = clean
        self._raw_ticker = clean
        self._context_type = context_type.lower()
        self._context_id = context_id
        self._is_open = True
        self._set_loading(True)
        self._set_status(msg("stock_detail.verileri_yukleniyor", clean=clean))
        self.stockChanged.emit()

        self._executor.submit(self._fetch_stock_details_worker, clean, self._context_type, self._context_id)

    @Slot()
    def close(self) -> None:
        """Detay penceresini kapatır."""
        self._is_open = False
        self.stockChanged.emit()

    @Slot()
    def refreshData(self) -> None:
        """Mevcut hisse verilerini tazeler."""
        if self._ticker:
            self.openStockWithContext(self._ticker, self._context_type, self._context_id)

    @Slot(str, int, float, result="QVariantMap")
    def tradeImpact(self, side: str, quantity: int, price: float) -> Dict[str, Any]:
        """Emir girilirse pozisyonun alacağı hali (lot, ortalama maliyet, nakit) önceden hesaplar."""
        trade_side = TradeSide.BUY if side.upper() in ("BUY", "ALIM") else TradeSide.SELL
        cash = None if self._cash is None else Decimal(str(self._cash))
        unit_price = Decimal(str(price or 0))
        entry = getattr(self._container, "trade_entry_service", None) if self._container else None
        fee = entry.estimate_fee(max(0, int(quantity)), unit_price) if entry is not None and unit_price > 0 and quantity > 0 else Decimal("0")
        impact = preview_order(OrderSpec(trade_side, quantity, unit_price, fee), int(self._quantity), Decimal(str(self._avg_cost)), cash)
        reasons = {INSUFFICIENT_CASH: msg("stock_detail.insufficient_cash"), INSUFFICIENT_LOTS: msg("stock_detail.insufficient_lots")}
        return {
            "valid": impact.valid,
            "message": reasons.get(impact.reason, ""),
            "fee": "₺" + tr_number(fee),
            "newQty": f"{max(impact.new_quantity, 0):,}".replace(",", "."),
            "newAvg": "-" if impact.new_avg_cost is None else "₺" + tr_number(impact.new_avg_cost),
            "cashAfter": "-" if impact.cash_after is None else "₺" + tr_number(impact.cash_after),
        }

    @Slot(str, int, float, str, str)
    def submitTrade(self, side: str, quantity: int, price: float, date_str: str = "", time_str: str = "") -> None:
        """Hisse detayından doğrudan hızlı alım veya satım emri gönderir.

        `date_str` (YYYY-AA-GG) ve `time_str` (SS:DD) boşsa bugün/şimdi kullanılır."""
        if quantity <= 0:
            self.tradeExecuted.emit(False, msg("stock_detail.lot_adedi_0_dan_buyuk_olmalidir"))
            return
        if price <= 0:
            self.tradeExecuted.emit(False, msg("stock_detail.fiyat_0_dan_buyuk_olmalidir"))
            return

        try:
            trade_date, trade_time = parse_trade_moment(date_str, time_str)
        except ValueError as exc:
            self.tradeExecuted.emit(False, str(exc))
            return

        if self._trade_pending:
            self.tradeExecuted.emit(False, msg("stock_detail.onceki_islem_suruyor"))
            return
        self._trade_pending = True
        self._set_loading(True)
        self._executor.submit(self._execute_trade_worker, side, quantity, price, trade_date, trade_time)

    @Slot()
    def exportStockToExcel(self) -> None:
        """Bu hisseye ait pozisyon özeti, işlem geçmişi ve sermaye artırımlarını Excel'e aktarır."""
        self._set_loading(True)
        self._set_status(msg("stock_detail.hisse_excel_raporu_hazirlaniyor"))
        self._executor.submit(self._export_excel_worker)

    # -------------------------------------------------------------------------
    # WORKER METODLARI
    # -------------------------------------------------------------------------

    def _on_data_ready(self, data: Dict[str, Any]) -> None:
        """Arka plandan gelen hisse detay verilerini QML özelliklerine yansıtır."""
        self._set_loading(False)
        if "error" in data:
            self._set_status(f"Hata: {data['error']}")
            return

        self._company_name = data.get("company_name", self._ticker)
        self._sector = data.get("sector", "BIST")
        self._current_price = data.get("current_price", 0.0)
        self._daily_diff = data.get("daily_diff", 0.0)
        self._quantity = data.get("quantity", 0)
        self._avg_cost = data.get("avg_cost", 0.0)
        self._market_value = data.get("market_value", 0.0)
        self._unrealized_pnl = data.get("unrealized_pnl", 0.0)
        self._unrealized_pnl_pct = data.get("unrealized_pnl_pct", 0.0)
        self._portfolio_weight_pct = data.get("portfolio_weight_pct", 0.0)
        self._cash = data.get("cash")
        self._portfolio_name = data.get("portfolio_name", msg("stock_detail.portfoy"))

        self._trades_list = data.get("trades", [])
        self._corp_actions_list = data.get("corp_actions", [])

        self._set_status(msg("stock_detail.hazir", ticker=self._ticker))
        self.stockChanged.emit()
        self.tradesChanged.emit()
        self.corpActionsChanged.emit()

    def _on_trade_result(self, success: bool, message: str) -> None:
        self._trade_pending = False
        self._set_loading(False)
        self._set_status(message)
        self.tradeExecuted.emit(success, message)
        if success:
            self.refreshData()

    def _on_export_result(self, success: bool, message: str) -> None:
        self._set_loading(False)
        self._set_status(message)
        self.excelExported.emit(success, message)

    def _set_loading(self, val: bool) -> None:
        if self._is_loading != val:
            self._is_loading = val
            self.loadingChanged.emit(val)

    def _set_status(self, msg: str) -> None:
        if self._status_message != msg:
            self._status_message = msg
            self.statusMessageChanged.emit(msg)
