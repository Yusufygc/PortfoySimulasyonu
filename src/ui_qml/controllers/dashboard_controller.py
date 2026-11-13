"""
Dashboard Controller — BIST işlemleri, sermaye hareketi, birleşik dönemsel getiriler ve Excel raporu.

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
from src.ui_qml.controllers.date_input import parse_date_text
from src.ui_qml.last_update_store import LastUpdateStore, format_return_pct
from src.domain.market_clock import market_time, market_today
from src.ui_qml.controllers.deps import ServiceView
from src.ui_qml.messages import msg
from src.ui_qml.presenters.formatting import tr_number

logger = logging.getLogger(__name__)


class DashboardController(QObject):
    """BIST işlemleri denetleyicisi (QML adı `dashboardController`, geriye uyumluluk için korunur).

    Portföy değerlemesi burada yapılmaz: Portföyüm sayfasının tüm rakamları `UnifiedPortfolioService`'ten gelir
    (`MyPortfolioController`). Bu denetleyici yalnızca BIST hızlı al/sat, sermaye hareketi, haftalık/aylık getiri
    kartları (Tüm Varlıklar TWR'si: `UnifiedReturnService`), grafik hızlı seçicisinin portföy hisseleri ve tarihsel Excel
    raporunu sunar.
    """
    REQUIRES = (
        "cash_movement_service", "current_price_resolver", "excel_export_service", "portfolio_service",
        "stock_lookup_service", "trade_entry_service", "unified_return_service",
    )

    kpisChanged = Signal()
    tradeExecuted = Signal(bool, str)   # success, message
    capitalUpdated = Signal(bool, str)  # success, message
    excelExported = Signal(bool, str)   # success, message
    returnsChanged = Signal()

    _asyncExportFinished = Signal(bool, str)
    _asyncTradeFinished = Signal(bool, str)
    _asyncReturnsReady = Signal(object, object)    # weekly_pct, monthly_pct (None olabilir)

    def __init__(self, container=None, parent=None):
        super().__init__(parent)
        self._deps = ServiceView(container, self.REQUIRES)
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="DashboardWorker")
        self._asyncExportFinished.connect(self._on_export_finished)
        self._asyncTradeFinished.connect(self._on_trade_finished)
        self._trade_pending = False  # emir işçide sürerken ikinci tıklamayı reddeder
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
        return f"₺{tr_number(self._capital)}"

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
        portfolio_service = self._deps.portfolio_service
        lookup = self._deps.stock_lookup_service
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
        service = self._deps.unified_return_service
        if service is not None:
            self._executor.submit(self._compute_returns_worker, service)

    def _compute_returns_worker(self, service) -> None:
        today = market_today()
        try:
            weekly, monthly = service.returns(today)
        except Exception as exc:
            logger.error("Getiri hesaplama hatası: %s", exc)
            return
        self._asyncReturnsReady.emit(weekly, monthly)

    def _on_returns_ready(self, weekly_pct: Any, monthly_pct: Any) -> None:
        self._weekly_pct, self._monthly_pct = weekly_pct, monthly_pct
        self._store.save_returns(weekly_pct, monthly_pct)
        self.returnsChanged.emit()

    @Slot(str, result="QVariantMap")
    def lookupTicker(self, ticker: str) -> dict:
        """Hisse kodu için kayıtlı şirket adı ve son bilinen fiyatı (DB'den, ağ çağrısı yapmadan) döndürür."""
        clean = (ticker or "").replace(".IS", "").strip().upper()
        result = {"found": False, "ticker": clean, "name": "", "price": 0.0}
        lookup = self._deps.stock_lookup_service
        if not clean or lookup is None:
            return result
        try:
            stock = lookup.find_stock(clean)
            if stock is None:
                return result
            result.update({"found": True, "name": (stock.name or clean).replace(".IS", "").strip()})
            resolver = self._deps.current_price_resolver
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
                self.tradeExecuted.emit(False, msg("dashboard.tarih_bicimi_gecersiz_bicim_gg_aa"))
                return
            if trade_date > market_today():
                self.tradeExecuted.emit(False, msg("dashboard.gelecek_tarihli_islem_girilemez"))
                return
        if (time_text or "").strip():
            try:
                trade_time = datetime.strptime(time_text.strip(), "%H:%M").time()
            except ValueError:
                self.tradeExecuted.emit(False, msg("dashboard.saat_bicimi_gecersiz_bicim_ss_dd"))
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
            self.tradeExecuted.emit(False, msg("dashboard.gecersiz_islem_parametreleri"))
            return

        if not (self._deps.trade_entry_service is not None):
            self.tradeExecuted.emit(False, msg("dashboard.islem_servisi_kullanilamiyor"))
            return
        if self._trade_pending:
            self.tradeExecuted.emit(False, msg("dashboard.onceki_islem_suruyor"))
            return

        from src.application.services.portfolio.trade_entry_service import TradeRequest
        from src.domain.models.trade import TradeSide

        req = TradeRequest(
            ticker=ticker,
            side=TradeSide.BUY if side.upper() == "BUY" else TradeSide.SELL,
            quantity=quantity,
            price=Decimal(str(price)),
            trade_date=trade_date or market_today(),
            trade_time=trade_time or market_time(),
        )
        done_text = msg("dashboard.adet_islemi_basariyla_kaydedildi", quantity=quantity, ticker=ticker, side=side.upper())
        self._trade_pending = True
        self._executor.submit(self._submit_trade_worker, req, done_text)

    def _submit_trade_worker(self, req, done_text: str) -> None:
        """İşlemi arka planda kaydeder (SQLite yazma kilidi beklerken arayüz donmaz)."""
        try:
            self._deps.trade_entry_service.submit_trade(req)
        except Exception as exc:
            logger.warning("TradeEntryService ile işlem kaydedilemedi: %s", exc, exc_info=not isinstance(exc, ValueError))
            # ValueError: kullanıcıya yönelik doğrulama iletisi; diğer istisna metinleri (SQL, yol) arayüze sızdırılmaz
            self._asyncTradeFinished.emit(False, str(exc) if isinstance(exc, ValueError) else msg("dashboard.islem_kaydedilemedi"))
            return
        self._asyncTradeFinished.emit(True, done_text)

    def _on_trade_finished(self, success: bool, text: str) -> None:
        self._trade_pending = False
        if success:
            self._load_portfolio_data()
        self.tradeExecuted.emit(success, text)

    @Slot(str, float, str)
    def manageCapital(self, action: str, amount: float, note: str) -> None:
        """Sermaye yatırma veya çekme işlemi gerçekleştirir."""
        if amount <= 0:
            self.capitalUpdated.emit(False, msg("dashboard.tutar_0_dan_buyuk_olmalidir"))
            return

        dec_amount = Decimal(str(amount))

        if self._deps.cash_movement_service is not None:
            try:
                if action.upper() == "DEPOSIT":
                    self._deps.cash_movement_service.add_deposit(dec_amount, notes=note or msg("dashboard.qml_sermaye_girisi"))
                    text = msg("dashboard.nakit_portfoye_yatirildi", dec_amount=tr_number(dec_amount))
                else:
                    self._deps.cash_movement_service.add_withdraw(dec_amount, notes=note or msg("dashboard.qml_sermaye_cikisi"))
                    text = msg("dashboard.nakit_portfoyden_cekildi", dec_amount=tr_number(dec_amount))
                self._load_portfolio_data()
                self.capitalUpdated.emit(True, text)
                return
            except Exception as exc:
                logger.warning("CashMovementService ile sermaye güncellenemedi: %s", exc)
                self.capitalUpdated.emit(False, str(exc))
                return

        self.capitalUpdated.emit(False, msg("dashboard.nakit_servisi_kullanilamiyor"))

    # -------------------------------------------------------------------------
    # EXCEL RAPOR DIŞA AKTARIMI
    # -------------------------------------------------------------------------

    @Slot(result=str)
    def firstTradeDateText(self) -> str:
        """Rapor aralığı için varsayılan başlangıç: ilk işlem tarihi (GG.AA.YYYY), yoksa boş."""
        service = self._deps.portfolio_service
        try:
            first = service.get_first_trade_date() if service else None
        except Exception:
            first = None
        return first.strftime("%d.%m.%Y") if first else ""

    @Slot(str, str, str, bool)
    def exportToExcelFile(self, start_text: str, end_text: str, file_path: str, append: bool = False) -> None:
        """Seçilen tarih aralığı ve hedef dosya için Excel raporu üretir (boş tarih = ilk işlemden bugüne).

        append=True mevcut dosyaya yeni günleri ekler (dosya yoksa yeni oluşturulur)."""
        start = parse_date_text(start_text)
        end = parse_date_text(end_text)
        if (start_text.strip() and start is None) or (end_text.strip() and end is None):
            self.excelExported.emit(False, msg("dashboard.tarih_bicimi_gecersiz_bicim_gg_aa"))
            return
        if start and end and start > end:
            self.excelExported.emit(False, msg("dashboard.baslangic_tarihi_bitis_tarihinden_buyuk_olam"))
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
            e_date = date.fromisoformat(end_date_str) if end_date_str else market_today()

            portfolio_service = self._deps.portfolio_service
            excel_service = self._deps.excel_export_service

            if s_date is None and portfolio_service:
                s_date = portfolio_service.get_first_trade_date()
            if s_date is None:
                s_date = market_today()

            if excel_service:
                excel_service.export_history(
                    start_date=s_date,
                    end_date=e_date,
                    file_path=target_file,
                    mode=ExportMode.APPEND if append else ExportMode.OVERWRITE,
                )
                self._asyncExportFinished.emit(True, msg("dashboard.excel_portfoy_raporu_kaydedildi", name=target_file.name))
            else:
                self._asyncExportFinished.emit(False, msg("dashboard.excel_rapor_servisi_kullanilamiyor"))
        except Exception as exc:
            logger.exception("Dashboard Excel export hatası: %s", exc)
            self._asyncExportFinished.emit(False, msg("dashboard.excel_raporu_olusturulamadi", exc=exc))

    def _on_export_finished(self, success: bool, message: str) -> None:
        self.excelExported.emit(success, message)

