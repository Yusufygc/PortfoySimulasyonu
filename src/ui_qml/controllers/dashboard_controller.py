"""
Dashboard Controller — Portföy KPI'ları, varlık dağılımı, canlı fiyat akışı ve işlem yönetimini sağlar.
"""
from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional

from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer
from src.ui_qml.models.positions_table_model import PositionsTableModel

logger = logging.getLogger(__name__)


def _parse_report_date(text: str):
    """GG.AA.YYYY veya YYYY-AA-GG biçimindeki metni tarihe çevirir; boş/geçersizse None."""
    from datetime import datetime as _dt

    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return _dt.strptime((text or "").strip(), fmt).date()
        except ValueError:
            continue
    return None


class DashboardController(QObject):
    kpisChanged = Signal()
    refreshStateChanged = Signal(bool)
    tradeExecuted = Signal(bool, str)   # success, message
    capitalUpdated = Signal(bool, str)  # success, message
    excelExported = Signal(bool, str)   # success, message

    _asyncExportFinished = Signal(bool, str)

    def __init__(self, container=None, parent=None):
        super().__init__(parent)
        self._container = container
        self._positions_model = PositionsTableModel(self)
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="DashboardWorker")
        self._asyncExportFinished.connect(self._on_export_finished)

        # Temel Portföy Durum Değişkenleri
        self._capital: Decimal = Decimal("185000.00")
        self._total_value: Decimal = Decimal("0")
        self._total_cost: Decimal = Decimal("0")
        self._total_pl: Decimal = Decimal("0")
        self._daily_pl: Decimal = Decimal("0")
        self._is_refreshing: bool = False

        # Hazır/Gerçekçi başlangıç pozisyon havuzu
        self._initial_positions = [
            {"ticker": "THYAO", "companyName": "Türk Hava Yolları",   "quantity": 1250, "avgCost": 264.50, "currentPrice": 294.25, "dailyDiff": 2.15},
            {"ticker": "GARAN", "companyName": "Garanti Bankası",     "quantity": 2800, "avgCost": 98.20,  "currentPrice": 118.40, "dailyDiff": 1.45},
            {"ticker": "ASELS", "companyName": "Aselsan Elektronik",  "quantity": 3500, "avgCost": 62.10,  "currentPrice": 59.80,  "dailyDiff": -0.80},
            {"ticker": "KCHOL", "companyName": "Koç Holding",         "quantity": 1500, "avgCost": 182.00, "currentPrice": 215.50, "dailyDiff": 3.10},
            {"ticker": "TUPRS", "companyName": "Tüpraş Rafinerileri", "quantity": 1800, "avgCost": 142.50, "currentPrice": 164.20, "dailyDiff": 0.90},
            {"ticker": "SISE",  "companyName": "Şişecam Cam Sanayi",  "quantity": 4200, "avgCost": 48.30,  "currentPrice": 46.90,  "dailyDiff": -1.20},
            {"ticker": "BIMAS", "companyName": "BİM Mağazalar",       "quantity": 600,  "avgCost": 440.00, "currentPrice": 512.00, "dailyDiff": 1.80},
            {"ticker": "FROTO", "companyName": "Ford Otomotiv",       "quantity": 300,  "avgCost": 920.00, "currentPrice": 1045.00,"dailyDiff": 2.45},
        ]

        # Event bus bağlantısı
        if self._container and hasattr(self._container, "event_bus") and self._container.event_bus:
            try:
                self._container.event_bus.prices_updated.connect(self._on_eventbus_prices_updated)
            except Exception as exc:
                logger.warning("EventBus bağlantı hatası: %s", exc)

        self._load_portfolio_data()

    # --- Properties ---

    @Property(QObject, constant=True)
    def positionsModel(self) -> PositionsTableModel:
        return self._positions_model

    @Property(str, notify=kpisChanged)
    def totalValue(self) -> str:
        return f"₺{self._total_value:,.2f}"

    @Property(str, notify=kpisChanged)
    def totalCost(self) -> str:
        return f"₺{self._total_cost:,.2f}"

    @Property(str, notify=kpisChanged)
    def cashBalance(self) -> str:
        return f"₺{self._capital:,.2f}"

    @Property(str, notify=kpisChanged)
    def cashRatio(self) -> str:
        if self._total_value > 0:
            ratio = (self._capital / self._total_value) * 100
            return f"%{ratio:.1f}"
        return "%0.0"

    @Property(str, notify=kpisChanged)
    def dailyGainLoss(self) -> str:
        sign = "+" if self._daily_pl >= 0 else ""
        return f"{sign}₺{self._daily_pl:,.2f}"

    @Property(str, notify=kpisChanged)
    def dailyGainLossPct(self) -> str:
        if self._total_value > 0:
            pct = (self._daily_pl / self._total_value) * 100
            sign = "+" if pct >= 0 else ""
            return f"{sign}%{pct:.2f}"
        return "%0.00"

    @Property(bool, notify=kpisChanged)
    def isDailyPositive(self) -> bool:
        return self._daily_pl >= 0

    @Property(str, notify=kpisChanged)
    def totalGainLoss(self) -> str:
        sign = "+" if self._total_pl >= 0 else ""
        return f"{sign}₺{self._total_pl:,.2f}"

    @Property(str, notify=kpisChanged)
    def totalGainLossPct(self) -> str:
        if self._total_cost > 0:
            pct = (self._total_pl / self._total_cost) * 100
            sign = "+" if pct >= 0 else ""
            return f"{sign}%{pct:.2f}"
        return "%0.00"

    @Property(bool, notify=kpisChanged)
    def isTotalPositive(self) -> bool:
        return self._total_pl >= 0

    @Property(int, notify=kpisChanged)
    def holdingsCount(self) -> int:
        return self._positions_model.rowCount()

    @Property(bool, notify=refreshStateChanged)
    def isRefreshing(self) -> bool:
        return self._is_refreshing

    @Property(list, notify=kpisChanged)
    def quickTickers(self) -> List[str]:
        """Grafik üst çubuğu için portföy hisseleri ve popüler semboller."""
        portfolio_tickers = [p["ticker"].replace(".IS", "").strip().upper() for p in self._positions_model._positions][:5]
        defaults = ["THYAO", "GARAN", "ASELS", "KCHOL"]
        res = list(portfolio_tickers)
        for d in defaults:
            if d not in res and len(res) < 6:
                res.append(d)
        return res or defaults

    @Property(list, notify=kpisChanged)
    def allocationSlices(self) -> List[Dict[str, Any]]:
        """Portföyün gerçek varlık ve hisse ağırlık dağılım dilimlerini döner."""
        slices = []
        palette = ["#2962ff", "#089981", "#ff9800", "#e91e63", "#9c27b0", "#00bcd4", "#ff5722"]

        positions = self._positions_model._positions
        if positions:
            sorted_pos = sorted(positions, key=lambda x: float(x.get("marketValue", 0.0)), reverse=True)
            top_4 = sorted_pos[:4]
            other = sorted_pos[4:]

            for i, p in enumerate(top_4):
                weight_val = float(p.get("weight", 0.0))
                pct = weight_val / 100.0
                m_val = float(p.get("marketValue", 0.0))
                raw_label = str(p.get("ticker", "")).replace(".IS", "").strip().upper()
                slices.append({
                    "label": raw_label,
                    "pct": float(round(pct, 4)),
                    "color": palette[i % len(palette)],
                    "amount": f"₺{m_val:,.0f}",
                })

            if other:
                other_val = sum(float(p.get("marketValue", 0.0)) for p in other)
                tot_val = float(self._total_value) if self._total_value > 0 else 1.0
                other_pct = other_val / tot_val if tot_val > 0 else 0.0
                slices.append({
                    "label": f"Diğer ({len(other)} Hisse)",
                    "pct": float(round(other_pct, 4)),
                    "color": "#787b86",
                    "amount": f"₺{other_val:,.0f}",
                })

        # Nakit varsa dilime ekle
        if self._capital > 0 and self._total_value > 0:
            cash_pct = float(self._capital) / float(self._total_value)
            slices.append({
                "label": "Nakit Bakiye",
                "pct": float(round(cash_pct, 4)),
                "color": "#ff9800",
                "amount": f"₺{float(self._capital):,.0f}",
            })

        return slices

    # --- Veri Yükleme ve Hesaplama ---

    def _load_portfolio_data(self) -> None:
        """Gerçek servislerden veya gerçekçi simülasyondan verileri yükler."""
        pos_list = []
        stocks_market_val = Decimal("0")
        total_cost = Decimal("0")
        daily_gain = Decimal("0")

        if self._container:
            try:
                if hasattr(self._container, "portfolio_service") and hasattr(self._container, "stock_repo"):
                    cash = self._container.portfolio_service.get_cash_balance()
                    if cash is not None:
                        self._capital = Decimal(str(cash))

                    portfolio = self._container.portfolio_service.get_current_portfolio()
                    active = portfolio.active_positions
                    if active:
                        stock_ids = list(active.keys())
                        latest_prices = {}
                        # Güncel fiyat: canlı fiyat yalnızca son kapanıştan daha yeni bir güne aitse kullanılır
                        resolver = getattr(self._container, "current_price_resolver", None)
                        resolved_prices = {}
                        if resolver is not None:
                            try:
                                resolved_prices = resolver.resolve(stock_ids)
                            except Exception as e:
                                logger.debug("Güncel fiyatlar çözümlenemedi: %s", e)
                        elif hasattr(self._container, "latest_price_repo"):
                            try:
                                latest_prices = self._container.latest_price_repo.get_latest_price_map(stock_ids)
                            except Exception as e:
                                logger.debug("latest_prices alınamadı: %s", e)

                        # N+1 Önleme: Hisseleri toplu sorguyla tek seferde çek
                        stocks_map = {}
                        if hasattr(self._container, "stock_repo"):
                            try:
                                stocks_list = self._container.stock_repo.get_stocks_by_ids(stock_ids)
                                stocks_map = {s.id: s for s in stocks_list}
                            except Exception as exc:
                                logger.debug("Toplu hisse bilgisi alinamadi: %s", exc)

                        for sid, pos in active.items():
                            stock = stocks_map.get(sid) or (self._container.stock_repo.get_stock_by_id(sid) if hasattr(self._container, "stock_repo") else None)
                            raw_ticker = stock.ticker if stock else f"STOCK_{sid}"
                            ticker = raw_ticker.replace(".IS", "").strip().upper()
                            raw_company = stock.name if (stock and stock.name) else ticker
                            company = raw_company.replace(".IS", "").strip()
                            qty = pos.total_quantity
                            cost = pos.average_cost if pos.average_cost is not None else Decimal("0")
                            resolved = resolved_prices.get(sid)
                            price = resolved.price if resolved is not None else latest_prices.get(sid, cost)

                            diff_pct = Decimal("0")
                            if resolved is not None:
                                change = resolver.daily_change_pct(sid, resolved)
                                diff_pct = change if change is not None else Decimal("0")
                            elif hasattr(self._container, "price_repo"):
                                try:
                                    prev = self._container.price_repo.get_last_price_before(sid, date.today())
                                    if prev and prev.close_price and prev.close_price > 0:
                                        diff_pct = ((price - prev.close_price) / prev.close_price) * 100
                                except Exception as exc:
                                    logger.debug("Önceki gün kapanış fiyatı alınamadı (sid=%s): %s", sid, exc)

                            m_val = pos.market_value(price)
                            tot_c = pos.total_cost
                            pl = pos.unrealized_pl(price)
                            pl_pct = (pl / tot_c * 100) if tot_c > 0 else Decimal("0")
                            day_gain = m_val * (diff_pct / Decimal("100"))

                            stocks_market_val += m_val
                            total_cost += tot_c
                            daily_gain += day_gain

                            pos_list.append({
                                "ticker": ticker,
                                "companyName": company,
                                "quantity": int(qty),
                                "avgCost": float(cost),
                                "currentPrice": float(price),
                                "dailyDiff": float(diff_pct),
                                "marketValue": float(m_val),
                                "unrealizedPL": float(pl),
                                "unrealizedPLPct": float(pl_pct),
                                "weight": 0.0,
                                "isUp": pl >= 0,
                                "flashState": 0,
                            })
            except Exception as exc:
                logger.info("Canlı DB erişimi sağlanamadı, offline mod aktif: %s", exc)

        # Demo pozisyonlar yalnızca konteynersiz (offline) modda gösterilir; gerçek DB'de boş portföy boş kalır
        if not pos_list and self._container is None:
            for item in self._initial_positions:
                qty = Decimal(str(item["quantity"]))
                cost = Decimal(str(item["avgCost"]))
                price = Decimal(str(item["currentPrice"]))
                diff_pct = Decimal(str(item["dailyDiff"]))

                m_val = qty * price
                tot_c = qty * cost
                pl = m_val - tot_c
                pl_pct = (pl / tot_c * 100) if tot_c > 0 else Decimal("0")
                day_gain = m_val * (diff_pct / Decimal("100"))

                stocks_market_val += m_val
                total_cost += tot_c
                daily_gain += day_gain

                pos_list.append({
                    "ticker": item["ticker"],
                    "companyName": item["companyName"],
                    "quantity": int(qty),
                    "avgCost": float(cost),
                    "currentPrice": float(price),
                    "dailyDiff": float(diff_pct),
                    "marketValue": float(m_val),
                    "unrealizedPL": float(pl),
                    "unrealizedPLPct": float(pl_pct),
                    "weight": 0.0,  # aşağıda hesaplanacak
                    "isUp": pl >= 0,
                    "flashState": 0,
                })

        self._total_value = stocks_market_val + self._capital
        self._total_cost = total_cost
        self._total_pl = stocks_market_val - total_cost
        self._daily_pl = daily_gain

        # Ağırlıkları normalize et
        for p in pos_list:
            if self._total_value > 0:
                p["weight"] = (Decimal(str(p["marketValue"])) / self._total_value) * 100

        self._positions_model.set_positions(pos_list)
        self.kpisChanged.emit()

    # --- Slots ---

    @Slot()
    def reloadPortfolio(self) -> None:
        """Ağ çağrısı yapmadan portföyü veritabanından yeniden yükler (sermaye artırımı, fiyat güncellemesi sonrası)."""
        self._load_portfolio_data()

    @Slot()
    def refreshMetrics(self) -> None:
        """Piyasa fiyatlarını gerçek servis üzerinden arka planda yeniler."""
        self._is_refreshing = True
        self.refreshStateChanged.emit(True)

        def do_refresh():
            try:
                live_service = None
                if self._container:
                    services = getattr(self._container, "services", None)
                    live_service = getattr(services, "live_price_refresh_service", None) if services else None
                    if not live_service:
                        live_service = getattr(self._container, "live_price_refresh_service", None)

                if live_service:
                    live_service.refresh_active_prices()
                else:
                    logger.debug("Canlı fiyat yenileme servisi bulunamadı, mevcut veriler korunuyor.")
            except Exception as exc:
                logger.warning("Canlı fiyat yenileme sırasında hata oluştu: %s", exc)
            finally:
                QTimer.singleShot(0, self._on_refresh_finished)

        threading.Thread(target=do_refresh, daemon=True).start()

    @Slot()
    def _on_refresh_finished(self) -> None:
        self._load_portfolio_data()
        self._is_refreshing = False
        self.refreshStateChanged.emit(False)

    @Slot(str, result="QVariantMap")
    def lookupTicker(self, ticker: str) -> dict:
        """Hisse kodu için kayıtlı şirket adı ve son bilinen fiyatı (DB'den, ağ çağrısı yapmadan) döndürür."""
        clean = (ticker or "").replace(".IS", "").strip().upper()
        result = {"found": False, "ticker": clean, "name": "", "price": 0.0}
        stock_repo = getattr(self._container, "stock_repo", None) if self._container else None
        if not clean or stock_repo is None:
            return result
        try:
            stock = stock_repo.get_stock_by_ticker(f"{clean}.IS") or stock_repo.get_stock_by_ticker(clean)
            if stock is None:
                return result
            result.update({"found": True, "name": (stock.name or clean).replace(".IS", "").strip()})
            resolver = getattr(self._container, "current_price_resolver", None)
            price = resolver.price_map([stock.id]).get(stock.id) if resolver is not None else None
            if price:
                result["price"] = float(price)
        except Exception as exc:
            logger.debug("Hisse arama başarısız (%s): %s", clean, exc)
        return result

    @Slot(str, str, int, float, str, str, str)
    def submitTradeAt(
        self, ticker: str, side: str, quantity: int, price: float, notes: str, date_text: str, time_text: str
    ) -> None:
        """Belirtilen tarih (GG.AA.YYYY) ve saat (SS:DD) ile Al/Sat işlemi kaydeder."""
        trade_date = date.today()
        trade_time = datetime.now().time().replace(microsecond=0)
        if (date_text or "").strip():
            try:
                trade_date = datetime.strptime(date_text.strip(), "%d.%m.%Y").date()
            except ValueError:
                self.tradeExecuted.emit(False, "Tarih biçimi geçersiz. Biçim: GG.AA.YYYY")
                return
            if trade_date > date.today():
                self.tradeExecuted.emit(False, "Gelecek tarihli işlem girilemez.")
                return
        if (time_text or "").strip():
            try:
                trade_time = datetime.strptime(time_text.strip(), "%H:%M").time()
            except ValueError:
                self.tradeExecuted.emit(False, "Saat biçimi geçersiz. Biçim: SS:DD")
                return
        self._submit_trade_impl(ticker, side, quantity, price, notes, trade_date, trade_time)

    @Slot(str, str, int, float, str)
    def submitTrade(self, ticker: str, side: str, quantity: int, price: float, notes: str) -> None:
        """Al/Sat işlemini bugünün tarihi ve şu anki saatle kaydeder ve portföyü günceller."""
        self._submit_trade_impl(ticker, side, quantity, price, notes, None, None)

    def _submit_trade_impl(
        self,
        ticker: str,
        side: str,
        quantity: int,
        price: float,
        notes: str,
        trade_date: Optional[date],
        trade_time: Optional[Any],
    ) -> None:
        ticker = ticker.strip().upper()
        if not ticker or quantity <= 0 or price <= 0:
            self.tradeExecuted.emit(False, "Geçersiz işlem parametreleri.")
            return

        # 1. Gerçek veritabanı servisi varsa kullan
        if self._container and hasattr(self._container, "trade_entry_service"):
            try:
                from src.application.services.portfolio.trade_entry_service import TradeRequest
                from src.domain.models.trade import TradeSide

                trade_side = TradeSide.BUY if side.upper() == "BUY" else TradeSide.SELL
                req = TradeRequest(
                    ticker=ticker,
                    side=trade_side,
                    quantity=quantity,
                    price=Decimal(str(price)),
                    trade_date=trade_date or date.today(),
                    trade_time=trade_time or datetime.now().time().replace(microsecond=0),
                )
                self._container.trade_entry_service.submit_trade(req)
                self._load_portfolio_data()
                self.tradeExecuted.emit(True, f"{quantity} adet {ticker} {side.upper()} işlemi başarıyla kaydedildi.")
                return
            except Exception as exc:
                logger.warning("TradeEntryService ile işlem kaydedilemedi: %s", exc)
                self.tradeExecuted.emit(False, str(exc))
                return

        # 2. Offline / Mock fallback
        total_amount = Decimal(str(quantity)) * Decimal(str(price))

        if side.upper() == "BUY":
            if self._capital < total_amount:
                self.tradeExecuted.emit(False, f"Yetersiz nakit! Gerekli: ₺{total_amount:,.2f}, Mevcut: ₺{self._capital:,.2f}")
                return
            self._capital -= total_amount
            found = False
            for p in self._initial_positions:
                if p["ticker"] == ticker:
                    curr_qty = Decimal(str(p["quantity"]))
                    curr_cost = Decimal(str(p["avgCost"]))
                    new_qty = curr_qty + Decimal(str(quantity))
                    new_cost = ((curr_qty * curr_cost) + total_amount) / new_qty
                    p["quantity"] = int(new_qty)
                    p["avgCost"] = float(round(new_cost, 2))
                    p["currentPrice"] = price
                    found = True
                    break
            if not found:
                self._initial_positions.append({
                    "ticker": ticker,
                    "companyName": f"{ticker} Hissesi",
                    "quantity": quantity,
                    "avgCost": price,
                    "currentPrice": price,
                    "dailyDiff": 0.0,
                })
            msg = f"{quantity} adet {ticker} başarıyla satın alındı (₺{total_amount:,.2f})."
        else: # SELL
            target = next((p for p in self._initial_positions if p["ticker"] == ticker), None)
            if not target or target["quantity"] < quantity:
                self.tradeExecuted.emit(False, f"Satış için yetersiz lot! Mevcut: {target['quantity'] if target else 0}")
                return
            target["quantity"] -= quantity
            self._capital += total_amount
            if target["quantity"] == 0:
                self._initial_positions.remove(target)
            msg = f"{quantity} adet {ticker} başarıyla satıldı (₺{total_amount:,.2f})."

        self._load_portfolio_data()
        self.tradeExecuted.emit(True, msg)

    @Slot(str, float, str)
    def manageCapital(self, action: str, amount: float, note: str) -> None:
        """Sermaye yatırma veya çekme işlemi gerçekleştirir."""
        if amount <= 0:
            self.capitalUpdated.emit(False, "Tutar 0'dan büyük olmalıdır.")
            return

        dec_amount = Decimal(str(amount))

        # 1. Gerçek veritabanı servisi varsa kullan
        if self._container and hasattr(self._container, "cash_movement_service"):
            try:
                if action.upper() == "DEPOSIT":
                    self._container.cash_movement_service.add_deposit(dec_amount, notes=note or "QML Sermaye Girişi")
                    msg = f"₺{dec_amount:,.2f} nakit portföye yatırıldı."
                else:
                    self._container.cash_movement_service.add_withdraw(dec_amount, notes=note or "QML Sermaye Çıkışı")
                    msg = f"₺{dec_amount:,.2f} nakit portföyden çekildi."
                self._load_portfolio_data()
                self.capitalUpdated.emit(True, msg)
                return
            except Exception as exc:
                logger.warning("CashMovementService ile sermaye güncellenemedi: %s", exc)
                self.capitalUpdated.emit(False, str(exc))
                return

        # 2. Offline / Mock fallback
        if action.lower() == "deposit":
            self._capital += dec_amount
            msg = f"₺{dec_amount:,.2f} nakit portföye yatırıldı."
        else:
            if self._capital < dec_amount:
                self.capitalUpdated.emit(False, "Yetersiz nakit bakiye.")
                return
            self._capital -= dec_amount
            msg = f"₺{dec_amount:,.2f} nakit portföyden çekildi."

        self._load_portfolio_data()
        self.capitalUpdated.emit(True, msg)

    def _on_eventbus_prices_updated(self, prices_dict: Dict[int, Decimal]) -> None:
        """EventBus'tan gelen fiyat güncellemesini işler."""
        logger.info("EventBus fiyat guncellemesi alindi: %d hisse", len(prices_dict))
        self.refreshMetrics()

    # -------------------------------------------------------------------------
    # EXCEL RAPOR DIŞA AKTARIMI
    # -------------------------------------------------------------------------

    @Slot()
    def exportToExcel(self) -> None:
        """Portföyün günlük simülasyonunu ve özetini profesyonel Excel raporu olarak kaydeder."""
        self._executor.submit(self._run_excel_export_worker, None, None)

    @Slot(str, str)
    def exportToExcelRange(self, start_date_str: str, end_date_str: str) -> None:
        """Belirtilen tarih aralığında Excel raporu oluşturur."""
        self._executor.submit(self._run_excel_export_worker, start_date_str, end_date_str)

    @Slot(result=str)
    def firstTradeDateText(self) -> str:
        """Rapor aralığı için varsayılan başlangıç: ilk işlem tarihi (GG.AA.YYYY), yoksa boş."""
        service = getattr(self._container, "portfolio_service", None) if self._container else None
        try:
            first = service.get_first_trade_date() if service else None
        except Exception:
            first = None
        return first.strftime("%d.%m.%Y") if first else ""

    @Slot(str, str, str, bool)
    def exportToExcelFile(self, start_text: str, end_text: str, file_path: str, append: bool = False) -> None:
        """Seçilen tarih aralığı ve hedef dosya için Excel raporu üretir (boş tarih = ilk işlemden bugüne).

        append=True mevcut dosyaya yeni günleri ekler (dosya yoksa yeni oluşturulur)."""
        start = _parse_report_date(start_text)
        end = _parse_report_date(end_text)
        if (start_text.strip() and start is None) or (end_text.strip() and end is None):
            self.excelExported.emit(False, "Tarih biçimi geçersiz. Biçim: GG.AA.YYYY")
            return
        if start and end and start > end:
            self.excelExported.emit(False, "Başlangıç tarihi bitiş tarihinden büyük olamaz.")
            return
        self._executor.submit(
            self._run_excel_export_worker,
            start.isoformat() if start else None,
            end.isoformat() if end else None,
            file_path.strip() or None,
            bool(append),
        )

    def _run_excel_export_worker(
        self,
        start_date_str: Optional[str],
        end_date_str: Optional[str],
        target_path: Optional[str] = None,
        append: bool = False,
    ) -> None:
        try:
            from datetime import date, datetime
            from pathlib import Path
            from src.application.services.reporting.daily_history_models import ExportMode

            desktop = Path.home() / "Desktop"
            out_dir = desktop if desktop.exists() else Path("reports").resolve()
            out_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_file = out_dir / f"Portfoy_Raporu_{timestamp}.xlsx"
            if target_path:
                target_file = Path(target_path)
                if target_file.suffix.lower() != ".xlsx":
                    target_file = target_file.with_suffix(".xlsx")
                target_file.parent.mkdir(parents=True, exist_ok=True)

            # Tarih aralığını belirle
            s_date = None
            e_date = date.today()
            if start_date_str:
                try:
                    s_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                except Exception:
                    pass
            if end_date_str:
                try:
                    e_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                except Exception:
                    pass

            portfolio_service = getattr(self._container, "portfolio_service", None) if self._container else None
            excel_service = getattr(self._container, "excel_export_service", None) if self._container else None

            if s_date is None and portfolio_service:
                s_date = portfolio_service.get_first_trade_date()
            if s_date is None:
                s_date = date.today()

            if excel_service:
                excel_service.export_history(
                    start_date=s_date,
                    end_date=e_date,
                    file_path=target_file,
                    mode=ExportMode.APPEND if append else ExportMode.OVERWRITE,
                )
                self._asyncExportFinished.emit(True, f"Excel portföy raporu kaydedildi:\n{target_file.name}")
            else:
                import pandas as pd
                positions_data = [
                    {
                        "Hisse": p.get("ticker", ""),
                        "Şirket": p.get("companyName", ""),
                        "Lot": p.get("quantity", 0),
                        "Maliyet": p.get("avgCost", 0.0),
                        "Son Fiyat": p.get("currentPrice", 0.0),
                    }
                    for p in self._initial_positions
                ]
                df = pd.DataFrame(positions_data)
                df.to_excel(str(target_file), index=False)
                self._asyncExportFinished.emit(True, f"Excel tablosu kaydedildi:\n{target_file.name}")
        except Exception as exc:
            logger.exception("Dashboard Excel export hatası: %s", exc)
            self._asyncExportFinished.emit(False, f"Excel raporu oluşturulamadı: {exc}")

    def _on_export_finished(self, success: bool, message: str) -> None:
        self.excelExported.emit(success, message)

