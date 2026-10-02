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
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time as dt_time
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb
from PySide6.QtCore import Property, QObject, Signal, Slot

from src.application.services.portfolio.trade_entry_service import TradeRequest
from src.domain.models.trade import TradeSide
from src.domain.models.model_portfolio import ModelTradeSide
from src.ui.formatters import display_ticker

logger = logging.getLogger(__name__)


def _clean_ticker(t: str) -> str:
    """Hisse kodunu temizler ve .IS uzantısını kaldırır."""
    if not t:
        return ""
    return t.replace(".IS", "").strip().upper()


class StockDetailController(QObject):
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
        self._status_message: str = ""

        # Hisse & Pozisyon Bilgileri
        self._ticker: str = ""
        self._raw_ticker: str = ""
        self._stock_id: Optional[int] = None
        self._company_name: str = ""
        self._sector: str = ""
        self._context_type: str = "main"   # "main" veya "model"
        self._context_id: int = 0          # model portfolio id (varsa)
        self._portfolio_name: str = "Ana Portföy"

        # Metrikler
        self._current_price: float = 0.0
        self._daily_diff: float = 0.0
        self._quantity: int = 0
        self._avg_cost: float = 0.0
        self._market_value: float = 0.0
        self._unrealized_pnl: float = 0.0
        self._unrealized_pnl_pct: float = 0.0
        self._portfolio_weight_pct: float = 0.0

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
        return f"₺{self._current_price:,.2f}" if self._current_price > 0 else "₺-"

    @Property(float, notify=stockChanged)
    def dailyDiff(self) -> float:
        return self._daily_diff

    @Property(str, notify=stockChanged)
    def dailyDiffStr(self) -> str:
        sign = "+" if self._daily_diff > 0 else ""
        return f"{sign}%{self._daily_diff:.2f}"

    @Property(bool, notify=stockChanged)
    def isDailyPositive(self) -> bool:
        return self._daily_diff >= 0

    @Property(int, notify=stockChanged)
    def quantity(self) -> int:
        return self._quantity

    @Property(str, notify=stockChanged)
    def quantityStr(self) -> str:
        return f"{self._quantity:,} Lot"

    @Property(float, notify=stockChanged)
    def avgCost(self) -> float:
        return self._avg_cost

    @Property(str, notify=stockChanged)
    def avgCostStr(self) -> str:
        return f"₺{self._avg_cost:,.2f}" if self._avg_cost > 0 else "₺0.00"

    @Property(float, notify=stockChanged)
    def marketValue(self) -> float:
        return self._market_value

    @Property(str, notify=stockChanged)
    def marketValueStr(self) -> str:
        return f"₺{self._market_value:,.2f}"

    @Property(float, notify=stockChanged)
    def unrealizedPnl(self) -> float:
        return self._unrealized_pnl

    @Property(str, notify=stockChanged)
    def unrealizedPnlStr(self) -> str:
        sign = "+" if self._unrealized_pnl >= 0 else ""
        return f"{sign}₺{self._unrealized_pnl:,.2f}"

    @Property(float, notify=stockChanged)
    def unrealizedPnlPct(self) -> float:
        return self._unrealized_pnl_pct

    @Property(str, notify=stockChanged)
    def unrealizedPnlPctStr(self) -> str:
        sign = "+" if self._unrealized_pnl_pct >= 0 else ""
        return f"{sign}%{self._unrealized_pnl_pct:.2f}"

    @Property(bool, notify=stockChanged)
    def isPnlPositive(self) -> bool:
        return self._unrealized_pnl >= 0

    @Property(float, notify=stockChanged)
    def portfolioWeightPct(self) -> float:
        return self._portfolio_weight_pct

    @Property(str, notify=stockChanged)
    def portfolioWeightStr(self) -> str:
        return f"%{self._portfolio_weight_pct:.1f}"

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
        clean = _clean_ticker(ticker)
        if not clean:
            return

        self._ticker = clean
        self._raw_ticker = f"{clean}.IS"
        self._context_type = context_type.lower()
        self._context_id = context_id
        self._is_open = True
        self._set_loading(True)
        self._set_status(f"{clean} verileri yükleniyor...")
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

    @Slot(str, int, float, str)
    def submitTrade(self, side: str, quantity: int, price: float, date_str: str = "") -> None:
        """Hisse detayından doğrudan hızlı alım veya satım emri gönderir."""
        if quantity <= 0:
            self.tradeExecuted.emit(False, "Lot adedi 0'dan büyük olmalıdır.")
            return
        if price <= 0:
            self.tradeExecuted.emit(False, "Fiyat 0'dan büyük olmalıdır.")
            return

        self._set_loading(True)
        self._executor.submit(self._execute_trade_worker, side, quantity, price, date_str)

    @Slot()
    def exportStockToExcel(self) -> None:
        """Bu hisseye ait pozisyon özeti, işlem geçmişi ve sermaye artırımlarını Excel'e aktarır."""
        self._set_loading(True)
        self._set_status("Hisse Excel raporu hazırlanıyor...")
        self._executor.submit(self._export_excel_worker)

    # -------------------------------------------------------------------------
    # WORKER METODLARI
    # -------------------------------------------------------------------------

    def _fetch_stock_details_worker(self, ticker: str, ctx_type: str, ctx_id: int) -> None:
        """Arka plan thread'inde hisse ve işlem verilerini toplar."""
        try:
            data: Dict[str, Any] = {
                "ticker": ticker,
                "company_name": "",
                "sector": "BIST",
                "stock_id": None,
                "current_price": 0.0,
                "daily_diff": 0.0,
                "quantity": 0,
                "avg_cost": 0.0,
                "market_value": 0.0,
                "unrealized_pnl": 0.0,
                "unrealized_pnl_pct": 0.0,
                "portfolio_weight_pct": 0.0,
                "portfolio_name": "Ana Portföy" if ctx_type == "main" else f"Model Portföy #{ctx_id}",
                "trades": [],
                "corp_actions": [],
            }

            # 1. Hisse Tanımını Bul (Stock Repo)
            stock_repo = getattr(self._container, "stock_repo", None) if self._container else None
            stock_obj = None
            if stock_repo:
                stock_obj = stock_repo.get_stock_by_ticker(ticker)
                if not stock_obj:
                    stock_obj = stock_repo.get_stock_by_ticker(f"{ticker}.IS")
                if stock_obj:
                    data["stock_id"] = stock_obj.id
                    clean_name = (stock_obj.name or ticker).replace(".IS", "").strip()
                    data["company_name"] = clean_name
                    data["sector"] = getattr(stock_obj, "sector", "BIST") or "BIST"

            # 2. Güncel Fiyatı Çek (Önce Canlı SQLite latest_price_repo, sonra DuckDB/Fallback)
            cur_price, d_diff = self._get_latest_price(ticker, stock_id=data["stock_id"])
            data["current_price"] = cur_price
            data["daily_diff"] = d_diff

            # 3. Pozisyon ve İşlem Geçmişi
            if ctx_type == "model" and ctx_id > 0:
                self._load_model_position_data(data, ctx_id, stock_obj, cur_price)
            else:
                self._load_main_position_data(data, stock_obj, cur_price)

            # 4. Sermaye Artırımları (Corporate Actions)
            if stock_obj and stock_obj.id and self._container:
                corp_service = getattr(self._container, "corporate_action_service", None)
                if corp_service:
                    try:
                        actions = corp_service.get_by_stock(stock_obj.id)
                        actions = sorted(actions, key=lambda a: a.ex_date, reverse=True)
                        for a in actions:
                            data["corp_actions"].append({
                                "date": a.ex_date.strftime("%d.%m.%Y"),
                                "actionType": str(a.action_type.value if hasattr(a.action_type, "value") else a.action_type),
                                "ratioStr": f"%{float(a.ratio_percent):.1f}",
                                "applied": bool(a.applied),
                            })
                    except Exception as ca_exc:
                        logger.warning("Kurumsal islemleri okuma hatasi: %s", ca_exc)

            self._asyncDataReady.emit(data)

        except Exception as e:
            logger.exception("Hisse detay veri getirme hatası (%s): %s", ticker, e)
            self._asyncDataReady.emit({"error": str(e), "ticker": ticker})

    def _get_latest_price(self, ticker: str, stock_id: Optional[int] = None) -> tuple[float, float]:
        """En güncel fiyatı ve dünkü kapanışa göre yüzdesel farkı döndürür."""
        clean = _clean_ticker(ticker)
        cur_price = 0.0
        diff = 0.0

        # 1. Önce canlı portföy değerlendirme reposundan (latest_price_repo) fiyat çek
        if self._container and stock_id:
            if hasattr(self._container, "latest_price_repo"):
                try:
                    lp_map = self._container.latest_price_repo.get_latest_price_map([stock_id])
                    if lp_map and stock_id in lp_map and lp_map[stock_id] is not None:
                        cur_price = float(lp_map[stock_id])
                except Exception as lp_err:
                    logger.debug("latest_price_map alinamadi: %s", lp_err)

            if cur_price > 0 and hasattr(self._container, "price_repo"):
                try:
                    prev = self._container.price_repo.get_last_price_before(stock_id, date.today())
                    if prev and prev.close_price and float(prev.close_price) > 0:
                        p_close = float(prev.close_price)
                        diff = ((cur_price - p_close) / p_close) * 100.0
                        return cur_price, diff
                except Exception as p_err:
                    logger.debug("prev price alinamadi: %s", p_err)

        # 2. Eğer latest_price_repo'dan bulunamadıysa DuckDB analitik reposuna bak (SADECE NOT NULL ve > 0)
        duckdb_path = Path("data/market_history.duckdb")
        if duckdb_path.exists():
            try:
                conn = duckdb.connect(str(duckdb_path), read_only=False)
                rows = conn.execute(
                    "SELECT close_price FROM daily_prices WHERE ticker = ? AND close_price IS NOT NULL AND close_price > 0 ORDER BY price_date DESC LIMIT 2",
                    [clean]
                ).fetchall()
                conn.close()
                if rows:
                    p1 = float(rows[0][0])
                    p2 = float(rows[1][0]) if len(rows) > 1 and rows[1][0] is not None else p1
                    d = ((p1 - p2) / p2 * 100.0) if p2 > 0 else 0.0
                    if cur_price <= 0:
                        cur_price = p1
                    if diff == 0.0:
                        diff = d
                    return cur_price, diff
            except Exception as duck_err:
                logger.debug("DuckDB fiyat okuma atlandı: %s", duck_err)

        # 3. Fallback: SQLite price_repo
        if self._container and hasattr(self._container, "price_repo"):
            try:
                p_repo = self._container.price_repo
                if stock_id:
                    dp = p_repo.get_last_price_before(stock_id, date.today())
                    if dp and dp.close_price:
                        p = float(dp.close_price)
                        if cur_price <= 0:
                            cur_price = p
                        return cur_price, diff
                p_obj = p_repo.get_latest_price(clean) or p_repo.get_latest_price(f"{clean}.IS")
                if p_obj and p_obj.close_price:
                    p = float(p_obj.close_price)
                    if cur_price <= 0:
                        cur_price = p
                    return cur_price, diff
            except Exception:
                pass

        return cur_price, diff

    def _load_main_position_data(self, data: Dict[str, Any], stock_obj: Any, cur_price: float) -> None:
        """Ana portföyden bu hisseye ait pozisyon ve işlem listesini yükler."""
        if not self._container:
            return

        portfolio_service = getattr(self._container, "portfolio_service", None)
        if not portfolio_service:
            return

        portfolio = portfolio_service.get_current_portfolio()
        total_portfolio_val = Decimal("0")

        # Toplam portföy değerini hesapla (Tekil toplu sorgu)
        stock_ids = [sid for sid, pos in portfolio.positions.items() if pos.total_quantity > 0]
        lp_map = {}
        if hasattr(self._container, "latest_price_repo") and stock_ids:
            try:
                lp_map = self._container.latest_price_repo.get_latest_price_map(stock_ids)
            except Exception:
                pass

        for sid, pos in portfolio.positions.items():
            if pos.total_quantity > 0:
                p_val = lp_map.get(sid)
                if p_val is not None and p_val > 0:
                    pos_val = Decimal(str(pos.total_quantity)) * p_val
                else:
                    pos_val = pos.total_cost
                total_portfolio_val += pos_val

        cash = portfolio_service.get_cash_balance()
        if cash:
            total_portfolio_val += Decimal(str(cash))

        # Bu hissenin pozisyonunu çek
        if stock_obj and stock_obj.id in portfolio.positions:
            pos = portfolio.positions[stock_obj.id]
            qty = pos.total_quantity
            cost = float(pos.total_cost)
            avg = (cost / qty) if qty > 0 else 0.0
            mval = qty * cur_price if cur_price > 0 else cost
            pnl = mval - cost
            pnl_pct = ((pnl / cost) * 100.0) if cost > 0 else 0.0
            weight = ((Decimal(str(mval)) / total_portfolio_val) * 100) if total_portfolio_val > 0 else Decimal("0")

            data["quantity"] = qty
            data["avg_cost"] = avg
            data["market_value"] = mval
            data["unrealized_pnl"] = pnl
            data["unrealized_pnl_pct"] = pnl_pct
            data["portfolio_weight_pct"] = float(weight)

        # İşlem geçmişini çek
        if stock_obj and stock_obj.id:
            try:
                trades = portfolio_service.get_trades_for_stock(stock_obj.id)
                trades = sorted(
                    trades,
                    key=lambda t: (t.trade_date, getattr(t, "trade_time", None) or datetime.min.time()),
                    reverse=True,
                )
                for t in trades:
                    is_buy = t.side in (TradeSide.BUY, ModelTradeSide.BUY)
                    qty = t.quantity
                    price = float(t.price)
                    tot = float(t.total_amount)
                    orig_qty = getattr(t, "original_quantity", None)
                    orig_price = float(getattr(t, "original_price", 0.0) or 0.0)
                    has_split = (orig_qty is not None and orig_qty != qty)
                    t_time = getattr(t, "trade_time", None)
                    data["trades"].append({
                        "date": t.trade_date.strftime("%d.%m.%Y"),
                        "time": t_time.strftime("%H:%M") if t_time else "-",
                        "side": "ALIM" if is_buy else "SATIM",
                        "isBuy": is_buy,
                        "quantity": qty,
                        "quantityStr": f"{qty:,} Lot",
                        "price": price,
                        "priceStr": f"₺{price:,.2f}",
                        "total": tot,
                        "totalStr": f"₺{tot:,.2f}",
                        "hasSplit": has_split,
                        "origQuantity": orig_qty,
                        "origPrice": orig_price,
                        "splitNote": f"Bölünme Öncesi: {orig_qty:,} Lot @ ₺{orig_price:,.2f}" if has_split else "",
                    })
            except Exception as tr_exc:
                logger.warning("İşlem geçmişi okunamadı: %s", tr_exc)

    def _load_model_position_data(self, data: Dict[str, Any], port_id: int, stock_obj: Any, cur_price: float) -> None:
        """Model portföyden bu hisseye ait pozisyon ve işlem listesini yükler."""
        if not self._container:
            return

        model_service = getattr(self._container, "model_portfolio_service", None)
        if not model_service:
            return

        port = model_service.get_portfolio_by_id(port_id)
        if port:
            data["portfolio_name"] = port.name

        try:
            positions = model_service.get_positions(port_id)
            summary = model_service.get_portfolio_summary(port_id)
            total_val = float(summary.get("total_value", 0.0))

            if stock_obj and stock_obj.id in positions:
                pos = positions[stock_obj.id]
                qty = pos.quantity
                avg = float(pos.average_cost)
                cost = qty * avg
                mval = qty * cur_price if cur_price > 0 else cost
                pnl = mval - cost
                pnl_pct = (pnl / cost * 100.0) if cost > 0 else 0.0
                weight = (mval / total_val * 100.0) if total_val > 0 else 0.0

                data["quantity"] = qty
                data["avg_cost"] = avg
                data["market_value"] = mval
                data["unrealized_pnl"] = pnl
                data["unrealized_pnl_pct"] = pnl_pct
                data["portfolio_weight_pct"] = weight
        except Exception as me:
            logger.warning("Model portfoy pozisyonu okunamadi: %s", me)

        if stock_obj and stock_obj.id:
            try:
                trades = model_service.get_stock_trades(port_id, stock_obj.id)
                trades = sorted(trades, key=lambda t: t.trade_date, reverse=True)
                for t in trades:
                    is_buy = t.side in (TradeSide.BUY, ModelTradeSide.BUY)
                    qty = t.quantity
                    price = float(t.price)
                    tot = qty * price
                    data["trades"].append({
                        "date": t.trade_date.strftime("%d.%m.%Y"),
                        "time": "-",
                        "side": "ALIM" if is_buy else "SATIM",
                        "isBuy": is_buy,
                        "quantity": qty,
                        "quantityStr": f"{qty:,} Lot",
                        "price": price,
                        "priceStr": f"₺{price:,.2f}",
                        "total": tot,
                        "totalStr": f"₺{tot:,.2f}",
                        "hasSplit": False,
                        "splitNote": "",
                    })
            except Exception as me:
                logger.warning("Model portfoy islemleri okunamadi: %s", me)

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
        self._portfolio_name = data.get("portfolio_name", "Portföy")

        self._trades_list = data.get("trades", [])
        self._corp_actions_list = data.get("corp_actions", [])

        self._set_status(f"{self._ticker} hazır.")
        self.stockChanged.emit()
        self.tradesChanged.emit()
        self.corpActionsChanged.emit()

    def _execute_trade_worker(self, side: str, qty: int, price: float, date_str: str) -> None:
        """Alım/satım işlemini veritabanında kaydeder."""
        try:
            is_buy = side.upper() == "BUY" or side.upper() == "ALIM"
            tr_side = TradeSide.BUY if is_buy else TradeSide.SELL

            tr_date = date.today()
            if date_str:
                try:
                    tr_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                except Exception:
                    pass

            if self._context_type == "model" and self._context_id > 0:
                model_service = getattr(self._container, "model_portfolio_service", None) if self._container else None
                if not model_service:
                    raise RuntimeError("Model portföy servisi bulunamadı.")
                from src.application.services.planning.model_portfolio_trade_service import ModelTradeInput
                model_service.add_trade_by_ticker(
                    portfolio_id=self._context_id,
                    ticker=self._ticker,
                    trade_input=ModelTradeInput(
                        side="BUY" if is_buy else "SELL",
                        quantity=qty,
                        price=Decimal(str(price)),
                        trade_date=tr_date,
                        trade_time=datetime.now().time(),
                    ),
                )
                total_amount = qty * price
                action_tr = "satın alındı" if is_buy else "satıldı"
                msg = f"{qty} adet {self._ticker} model portföye {action_tr} (₺{total_amount:,.2f})."
                self._asyncTradeResult.emit(True, msg)
                return

            trade_entry_service = getattr(self._container, "trade_entry_service", None) if self._container else None
            if not trade_entry_service:
                raise RuntimeError("İşlem giriş servisi bulunamadı.")

            # Seans/nakit/lot doğrulamaları TradeEntryService içinde yapılır (Dashboard ile aynı yol).
            # Geçmiş tarihli işlemde saat bilgisi seçilemediği için seans içi sabit saat kullanılır.
            tr_time = datetime.now().time().replace(microsecond=0) if tr_date == date.today() else dt_time(12, 0)
            trade_entry_service.submit_trade(
                TradeRequest(
                    ticker=self._raw_ticker or self._ticker,
                    side=tr_side,
                    quantity=qty,
                    price=Decimal(str(price)),
                    trade_date=tr_date,
                    trade_time=tr_time,
                    name=self._company_name or None,
                )
            )
            total_amount = qty * price
            action_tr = "satın alındı" if is_buy else "satıldı"
            msg = f"{qty} adet {self._ticker} başarıyla {action_tr} (₺{total_amount:,.2f})."
            self._asyncTradeResult.emit(True, msg)

        except Exception as e:
            logger.exception("Emir iletim hatası (%s): %s", self._ticker, e)
            self._asyncTradeResult.emit(False, f"Emir iletilemedi: {e}")

    def _on_trade_result(self, success: bool, message: str) -> None:
        self._set_loading(False)
        self._set_status(message)
        self.tradeExecuted.emit(success, message)
        if success:
            self.refreshData()

    def _export_excel_worker(self) -> None:
        """Bu hissenin işlem dökümünü ve pozisyon özetini Excel olarak kaydeder."""
        try:
            import pandas as pd
            desktop = Path.home() / "Desktop"
            out_dir = desktop if desktop.exists() else Path("reports").resolve()
            out_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_file = out_dir / f"Hisse_Detay_{self._ticker}_{timestamp}.xlsx"

            # 1. Pozisyon Özeti DataFrame
            summary_data = [
                {"Metrik": "Hisse Kodu", "Değer": self._ticker},
                {"Metrik": "Şirket Adı", "Değer": self._company_name},
                {"Metrik": "Sektör", "Değer": self._sector},
                {"Metrik": "Portföy", "Değer": self._portfolio_name},
                {"Metrik": "Rapor Tarihi", "Değer": datetime.now().strftime("%d.%m.%Y %H:%M")},
                {"Metrik": "Mevcut Lot", "Değer": self._quantity},
                {"Metrik": "Ortalama Maliyet (TL)", "Değer": self._avg_cost},
                {"Metrik": "Son Kapanış Fiyatı (TL)", "Değer": self._current_price},
                {"Metrik": "Toplam Piyasa Değeri (TL)", "Değer": self._market_value},
                {"Metrik": "Net Kâr / Zarar (TL)", "Değer": self._unrealized_pnl},
                {"Metrik": "Kâr / Zarar Oranı (%)", "Değer": f"%{self._unrealized_pnl_pct:.2f}"},
                {"Metrik": "Portföy Ağırlığı (%)", "Değer": f"%{self._portfolio_weight_pct:.1f}"},
            ]
            df_summary = pd.DataFrame(summary_data)

            # 2. İşlem Geçmişi DataFrame
            trades_export = []
            for t in self._trades_list:
                trades_export.append({
                    "Tarih": t.get("date", "-"),
                    "Saat": t.get("time", "-"),
                    "İşlem Türü": t.get("side", "-"),
                    "Adet (Lot)": t.get("quantity", 0),
                    "Fiyat (TL)": t.get("price", 0.0),
                    "Toplam Tutar (TL)": t.get("total", 0.0),
                })
            df_trades = pd.DataFrame(trades_export) if trades_export else pd.DataFrame([{"Bilgi": "Kayıtlı işlem bulunamadı."}])

            # 3. Sermaye Artırımları DataFrame
            corp_export = []
            for c in self._corp_actions_list:
                corp_export.append({
                    "Tarih": c.get("date", "-"),
                    "İşlem Türü": c.get("actionType", "-"),
                    "Artırım Oranı": c.get("ratioStr", "-"),
                    "Uygulandı mı?": "Evet" if c.get("applied") else "Hayır",
                })
            df_corp = pd.DataFrame(corp_export) if corp_export else pd.DataFrame([{"Bilgi": "Kayıtlı sermaye artırımı bulunamadı."}])

            with pd.ExcelWriter(str(target_file), engine="openpyxl") as writer:
                df_summary.to_excel(writer, sheet_name="Pozisyon Özeti", index=False)
                df_trades.to_excel(writer, sheet_name="İşlem Geçmişi", index=False)
                df_corp.to_excel(writer, sheet_name="Sermaye Artırımları", index=False)

                # Formatter mevcutsa profesyonel stilleri uygula
                formatter = getattr(self._container, "excel_formatter", None) if self._container else None
                if formatter:
                    try:
                        formatter.apply_formatting(writer, "Pozisyon Özeti", df_summary)
                        formatter.apply_formatting(writer, "İşlem Geçmişi", df_trades)
                        formatter.apply_formatting(writer, "Sermaye Artırımları", df_corp)
                    except Exception as fe:
                        logger.debug("ExcelFormatter opsiyonel stil uygulanamadı: %s", fe)

            msg = f"{self._ticker} detay raporu başarıyla kaydedildi:\n{target_file.name}"
            self._asyncExportResult.emit(True, msg)

        except Exception as e:
            logger.exception("Excel hisse dökümü hatası: %s", e)
            self._asyncExportResult.emit(False, f"Excel raporu oluşturulamadı: {e}")

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
