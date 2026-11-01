"""
Dashboard Controller — BIST işlemleri, sermaye hareketi, BIST dönemsel getirileri ve Excel raporu.

Fiyatları kendisi çekmez: `PriceRefreshController.pricesChanged` ile `reloadPrices` çağrılır ve görünüm yalnızca
veritabanından (`CurrentPriceResolver`) yeniden okunur.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Any, List, Optional

from PySide6.QtCore import QObject, Signal, Property, Slot
from src.ui_qml.last_update_store import LastUpdateStore, format_return_pct
from src.domain.market_clock import market_time, market_today

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
    """BIST işlemleri denetleyicisi (QML adı `dashboardController`, geriye uyumluluk için korunur).

    Portföy değerlemesi burada yapılmaz: Portföyüm sayfasının tüm rakamları `UnifiedPortfolioService`'ten gelir
    (`MyPortfolioController`). Bu denetleyici yalnızca BIST hızlı al/sat, sermaye hareketi, BIST haftalık/aylık
    getiri kartları, grafik hızlı seçicisinin portföy hisseleri ve tarihsel Excel raporunu sunar.
    """

    kpisChanged = Signal()
    tradeExecuted = Signal(bool, str)   # success, message
    capitalUpdated = Signal(bool, str)  # success, message
    excelExported = Signal(bool, str)   # success, message
    returnsChanged = Signal()

    _asyncExportFinished = Signal(bool, str)
    _asyncReturnsReady = Signal(object, object)    # weekly_pct, monthly_pct (None olabilir)

    def __init__(self, container=None, parent=None):
        super().__init__(parent)
        self._container = container
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="DashboardWorker")
        self._asyncExportFinished.connect(self._on_export_finished)
        self._asyncReturnsReady.connect(self._on_returns_ready)

        # Dönemsel getiriler (kayıtlı son değer anında gösterilir, sonra yeniden hesaplanır)
        self._store = LastUpdateStore()
        self._weekly_pct, self._monthly_pct = self._store.saved_returns()

        self._capital: Decimal = Decimal("0")
        self._tickers: List[str] = []

        self._load_portfolio_data()
        self._reload_returns()

    # --- Properties ---

    @Property(str, notify=kpisChanged)
    def cashBalance(self) -> str:
        return f"₺{self._capital:,.2f}"

    @Property(str, notify=returnsChanged)
    def weeklyReturnText(self) -> str:
        return format_return_pct(self._weekly_pct)

    @Property(str, notify=returnsChanged)
    def monthlyReturnText(self) -> str:
        return format_return_pct(self._monthly_pct)

    @Property(bool, notify=returnsChanged)
    def isWeeklyPositive(self) -> bool:
        return self._weekly_pct is None or self._weekly_pct >= 0

    @Property(bool, notify=returnsChanged)
    def isMonthlyPositive(self) -> bool:
        return self._monthly_pct is None or self._monthly_pct >= 0

    @Property(list, notify=kpisChanged)
    def quickTickers(self) -> List[str]:
        """Grafik üst çubuğu için portföy hisseleri (en çok 5) ve popüler semboller."""
        defaults = ["THYAO", "GARAN", "ASELS", "KCHOL"]
        res = list(self._tickers[:5])
        for d in defaults:
            if d not in res and len(res) < 6:
                res.append(d)
        return res or defaults

    # --- Veri Yükleme (değerleme yok: yalnızca nakit ve açık pozisyon kodları) ---

    def _load_portfolio_data(self) -> None:
        portfolio_service = getattr(self._container, "portfolio_service", None) if self._container else None
        lookup = getattr(self._container, "stock_lookup_service", None) if self._container else None
        if portfolio_service is None:
            return
        try:
            cash = portfolio_service.get_cash_balance()
            self._capital = Decimal(str(cash)) if cash is not None else Decimal("0")
            active = portfolio_service.get_current_portfolio().active_positions
            stocks = lookup.get_stocks(list(active)) if (lookup is not None and active) else {}
            self._tickers = [
                (stocks[sid].ticker or "").replace(".IS", "").strip().upper() for sid in active if sid in stocks
            ]
        except Exception as exc:
            logger.info("Portföy verisi okunamadı: %s", exc)
        self.kpisChanged.emit()

    @Slot()
    def reloadPortfolio(self) -> None:
        """Ağ çağrısı yapmadan portföyü veritabanından yeniden yükler (sermaye artırımı, fiyat güncellemesi sonrası)."""
        self._load_portfolio_data()

    @Slot()
    def reloadPrices(self) -> None:
        """Fiyatlar veritabanında değişti (`PriceRefreshController.pricesChanged`): görünüm ve getiriler yeniden okunur."""
        self._load_portfolio_data()
        self._reload_returns()

    def _reload_returns(self) -> None:
        service = getattr(self._container, "return_calc_service", None) if self._container else None
        if service is not None:
            self._executor.submit(self._compute_returns_worker, service)

    def _compute_returns_worker(self, service) -> None:
        today = market_today()
        try:
            weekly, _, _ = service.compute_weekly_return(today)
            monthly, _, _ = service.compute_monthly_return(today)
        except Exception as exc:
            logger.error("Getiri hesaplama hatası: %s", exc)
            return
        self._asyncReturnsReady.emit(
            float(weekly) * 100 if weekly is not None else None,
            float(monthly) * 100 if monthly is not None else None,
        )

    def _on_returns_ready(self, weekly_pct: Any, monthly_pct: Any) -> None:
        self._weekly_pct, self._monthly_pct = weekly_pct, monthly_pct
        self._store.save_returns(weekly_pct, monthly_pct)
        self.returnsChanged.emit()

    @Slot(str, result="QVariantMap")
    def lookupTicker(self, ticker: str) -> dict:
        """Hisse kodu için kayıtlı şirket adı ve son bilinen fiyatı (DB'den, ağ çağrısı yapmadan) döndürür."""
        clean = (ticker or "").replace(".IS", "").strip().upper()
        result = {"found": False, "ticker": clean, "name": "", "price": 0.0}
        lookup = getattr(self._container, "stock_lookup_service", None) if self._container else None
        if not clean or lookup is None:
            return result
        try:
            stock = lookup.find_stock(clean)
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
        trade_date = market_today()
        trade_time = market_time()
        if (date_text or "").strip():
            try:
                trade_date = datetime.strptime(date_text.strip(), "%d.%m.%Y").date()
            except ValueError:
                self.tradeExecuted.emit(False, "Tarih biçimi geçersiz. Biçim: GG.AA.YYYY")
                return
            if trade_date > market_today():
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
                    trade_date=trade_date or market_today(),
                    trade_time=trade_time or market_time(),
                )
                self._container.trade_entry_service.submit_trade(req)
                self._load_portfolio_data()
                self.tradeExecuted.emit(True, f"{quantity} adet {ticker} {side.upper()} işlemi başarıyla kaydedildi.")
                return
            except Exception as exc:
                logger.warning("TradeEntryService ile işlem kaydedilemedi: %s", exc)
                self.tradeExecuted.emit(False, str(exc))
                return

        self.tradeExecuted.emit(False, "İşlem servisi kullanılamıyor.")

    @Slot(str, float, str)
    def manageCapital(self, action: str, amount: float, note: str) -> None:
        """Sermaye yatırma veya çekme işlemi gerçekleştirir."""
        if amount <= 0:
            self.capitalUpdated.emit(False, "Tutar 0'dan büyük olmalıdır.")
            return

        dec_amount = Decimal(str(amount))

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

        self.capitalUpdated.emit(False, "Nakit servisi kullanılamıyor.")

    # -------------------------------------------------------------------------
    # EXCEL RAPOR DIŞA AKTARIMI
    # -------------------------------------------------------------------------

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
            s_date = date.fromisoformat(start_date_str) if start_date_str else None
            e_date = date.fromisoformat(end_date_str) if end_date_str else date.today()

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
                self._asyncExportFinished.emit(False, "Excel rapor servisi kullanılamıyor.")
        except Exception as exc:
            logger.exception("Dashboard Excel export hatası: %s", exc)
            self._asyncExportFinished.emit(False, f"Excel raporu oluşturulamadı: {exc}")

    def _on_export_finished(self, success: bool, message: str) -> None:
        self.excelExported.emit(success, message)

