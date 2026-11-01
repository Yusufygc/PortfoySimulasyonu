"""
AssetsController — BIST dışı varlık defterinin arayüz köprüsü (Portföyüm: varlık ekleme, işlem, fiyat yenileme).

Ağ gerektiren işler (sembol doğrulama, geçmiş doldurma, fiyat/kur yenileme) arka plan iş parçacığında çalışır ve
sonuç Qt sinyaliyle ana iş parçacığına döner. İşlem kaydı ve silme yalnızca veritabanıdır (eşzamanlı).
`dataChanged` sinyali, Portföyüm özetinin yeniden okunması için `MyPortfolioController.reload`'a bağlanır.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, time
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from src.domain.market_clock import market_time, market_today
from src.domain.models.asset import AssetClass, AssetUnit
from src.domain.models.trade import TradeSide
from src.ui_qml.controllers.number_input import parse_decimal_text
from src.ui_qml.messages import msg

logger = logging.getLogger(__name__)

REFRESH_INTERVAL_MS = 5 * 60 * 1000
_STARTUP_DELAY_MS = 3000
_DATE_FORMATS = ("%d.%m.%Y", "%Y-%m-%d")


def parse_date_text(text: str) -> Optional[date]:
    """GG.AA.YYYY veya YYYY-AA-GG; boşsa bugün (piyasa saati), geçersizse None."""
    from datetime import datetime

    raw = (text or "").strip()
    if not raw:
        return market_today()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def parse_time_text(text: str) -> Optional[time]:
    """SS:DD veya SS:DD:SS; boşsa şimdi (piyasa saati), geçersizse None."""
    from datetime import datetime

    raw = (text or "").strip()
    if not raw:
        return market_time()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).time()
        except ValueError:
            continue
    return None


def _parse_amounts(form: Dict[str, Any]) -> Tuple[Optional[str], Optional[tuple]]:
    side = str(form.get("side", "")).upper()
    if side not in ("BUY", "SELL"):
        return msg("assets.islem_yonu_gecersiz"), None
    qty, unit_price = parse_decimal_text(form.get("quantity", "")), parse_decimal_text(form.get("price", ""))
    if qty is None or qty <= 0:
        return msg("assets.miktar_sifirdan_buyuk_bir_sayi_olmali"), None
    if unit_price is None or unit_price <= 0:
        return msg("assets.fiyat_sifirdan_buyuk_bir_sayi_olmali"), None
    return None, (TradeSide(side), qty, unit_price)


def _parse_moment(form: Dict[str, Any]) -> Tuple[Optional[str], Optional[tuple]]:
    trade_date, trade_time = parse_date_text(form.get("date", "")), parse_time_text(form.get("time", ""))
    if trade_date is None:
        return msg("assets.tarih_gg_aa_yyyy_biciminde_olmali"), None
    if trade_time is None:
        return msg("assets.saat_ss_dd_biciminde_olmali"), None
    return None, (trade_date, trade_time)


def _parse_fx(form: Dict[str, Any]) -> Tuple[Optional[str], Optional[Decimal]]:
    text = str(form.get("fx", "") or "").strip()
    if not text:
        return None, None
    rate = parse_decimal_text(text)
    if rate is None or rate <= 0:
        return msg("assets.kur_sifirdan_buyuk_bir_sayi_olmali"), None
    return None, rate


def parse_trade_form(form: Dict[str, Any]) -> Tuple[Optional[str], Optional[tuple]]:
    """İşlem penceresi alanlarını doğrular: `(hata, (yön, miktar, fiyat, tarih, saat, kur))`."""
    parts: list = []
    for parse in (_parse_amounts, _parse_moment, _parse_fx):
        error, value = parse(form)
        if error:
            return error, None
        parts.append(value)
    side, qty, unit_price = parts[0]
    trade_date, trade_time = parts[1]
    return None, (side, qty, unit_price, trade_date, trade_time, parts[2])


class AssetsController(QObject):
    """QML context property: assetsController"""

    assetsChanged = Signal()
    busyChanged = Signal()
    dataChanged = Signal()                 # varlık/işlem/fiyat değişti: Portföyüm özeti yeniden okunmalı
    assetAdded = Signal(bool, str)         # success, message
    tradeRecorded = Signal(bool, str)
    assetRemoved = Signal(bool, str)
    pricesRefreshed = Signal(bool, str)

    _asyncDone = Signal(str, bool, str)    # tür, success, message (arka plan -> ana iş parçacığı)

    def __init__(self, container=None, parent: QObject | None = None, autostart: bool = False) -> None:
        super().__init__(parent)
        self._ledger = getattr(container, "asset_ledger_service", None) if container is not None else None
        self._refresh = getattr(container, "asset_price_refresh_service", None) if container is not None else None
        self._fx = getattr(container, "fx_rate_service", None) if container is not None else None
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="AssetsWorker")
        self._busy = False
        self._asyncDone.connect(self._on_async_done)
        self._timer = QTimer(self)
        self._timer.timeout.connect(lambda: self.refreshPrices(True))
        if self._refresh is not None and autostart:
            self._timer.start(REFRESH_INTERVAL_MS)
            QTimer.singleShot(_STARTUP_DELAY_MS, lambda: self.refreshPrices(True))

    # --- Özellikler ---

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Property("QVariantList", constant=True)
    def catalog(self) -> List[Dict[str, Any]]:
        if self._ledger is None:
            return []
        return [
            {"key": e.key, "name": e.name, "classKey": e.asset_class.value, "currency": e.quote_currency}
            for e in self._ledger.catalog
        ]

    @Property("QVariantList", notify=assetsChanged)
    def assets(self) -> List[Dict[str, Any]]:
        if self._ledger is None:
            return []
        return [
            {
                "id": a.id, "symbol": a.symbol, "name": a.name, "classKey": a.asset_class.value,
                "currency": a.quote_currency, "isTry": a.is_try_quoted, "unit": a.unit.value,
            }
            for a in self._ledger.list_assets()
        ]

    # --- Arka plan işleri ---

    def _start(self, kind: str, work: Callable[[], str]) -> None:
        """`work` başarı mesajı döner ya da istisna fırlatır; sonuç `_asyncDone` ile ana iş parçacığına döner."""
        if self._busy:
            self._result_signal(kind).emit(False, msg("assets.baska_bir_islem_suruyor_bitmesini_bekleyin"))
            return
        self._busy = True
        self.busyChanged.emit()

        def run() -> None:
            try:
                self._asyncDone.emit(kind, True, work())
            except Exception as exc:
                logger.info("Varlık işlemi başarısız (%s): %s", kind, exc)
                self._asyncDone.emit(kind, False, str(exc))

        self._executor.submit(run)

    def _result_signal(self, kind: str):
        return {"assetAdded": self.assetAdded, "pricesRefreshed": self.pricesRefreshed}[kind]

    def _on_async_done(self, kind: str, success: bool, message: str) -> None:
        self._busy = False
        self.busyChanged.emit()
        self._result_signal(kind).emit(success, message)
        if success:
            self.assetsChanged.emit()
            self.dataChanged.emit()

    def _after_add(self, asset) -> str:
        """Yeni varlık için geçmiş fiyat, son fiyat ve kur yüklemesi (her adım en iyi çabayla)."""
        notes: List[str] = []
        for step, action in (
            (msg("assets.gecmis"), lambda: self._refresh.backfill_history(asset.id)),
            ("fiyat", lambda: self._refresh.refresh_latest(only_open=False)),
            ("kur", lambda: self._ensure_fx(asset.quote_currency)),
        ):
            try:
                action()
            except Exception as exc:
                logger.info("%s yüklenemedi (%s): %s", step, asset.symbol, exc)
                notes.append(step)
        suffix = msg("assets.yuklenemedi_daha_sonra_yenilenecek", items=', '.join(notes)) if notes else ""
        return f"{asset.symbol} eklendi.{suffix}"

    def _ensure_fx(self, currency: str) -> None:
        if self._fx is None or currency.upper() == "TRY":
            return
        if self._fx.get_rate(currency, "TRY") is None:
            self._fx.backfill(currency, "TRY")
        self._fx.refresh_latest([currency])

    # --- Slotlar ---

    @Slot(str)
    def addCatalogAsset(self, key: str) -> None:
        if self._ledger is None:
            self.assetAdded.emit(False, msg("assets.varlik_servisi_kullanilamiyor"))
            return
        self._start("assetAdded", lambda: self._after_add(self._ledger.add_catalog_asset(key)))

    @Slot(str, str, str, str)
    def addAsset(self, symbol: str, name: str, class_key: str, currency: str) -> None:
        if self._ledger is None:
            self.assetAdded.emit(False, msg("assets.varlik_servisi_kullanilamiyor"))
            return
        try:
            asset_class = AssetClass(class_key)
        except ValueError:
            self.assetAdded.emit(False, msg("assets.varlik_sinifi_gecersiz"))
            return
        label = (name or "").strip() or (symbol or "").strip().upper()
        self._start(
            "assetAdded",
            lambda: self._after_add(
                self._ledger.add_asset(symbol, label, asset_class, currency or "USD", unit=AssetUnit.UNIT)
            ),
        )

    @Slot()
    @Slot(bool)
    def refreshPrices(self, only_open: bool = False) -> None:
        if self._refresh is None:
            return

        def work() -> str:
            currencies = {a["currency"] for a in self.assets if not a["isTry"]}
            if self._fx is not None and currencies:
                self._fx.refresh_latest(currencies)
            result = self._refresh.refresh_latest(only_open=only_open)
            return msg("assets.varlik_fiyati_guncellendi", count=len(result.updated))

        self._start("pricesRefreshed", work)

    @Slot(int, result="QVariantMap")
    def suggest(self, asset_id: int) -> Dict[str, Any]:
        """İşlem penceresi için önerilen fiyat ve kur (veritabanındaki en yeni değerler; ağ çağrısı yok)."""
        asset = self._ledger.get_asset(asset_id) if self._ledger is not None else None
        if asset is None:
            return {}
        price = self._refresh.cached_price(asset_id) if self._refresh is not None else None
        rate = self._fx.get_rate(asset.quote_currency, "TRY") if self._fx is not None else None
        return {
            "currency": asset.quote_currency,
            "isTry": asset.is_try_quoted,
            "price": format(asset.unit_price(price).normalize(), "f") if price is not None else "",
            "fxRate": f"{rate:.4f}" if rate is not None and not asset.is_try_quoted else "",
        }

    @Slot(int, "QVariantMap")
    def recordTrade(self, asset_id: int, form: Dict[str, Any]) -> None:
        """`form`: side (BUY/SELL), quantity, price, date (GG.AA.YYYY), time (SS:DD), fx (boş olabilir) metinleri."""
        if self._ledger is None:
            self.tradeRecorded.emit(False, msg("assets.varlik_servisi_kullanilamiyor"))
            return
        error, parsed = parse_trade_form(form)
        if error:
            self.tradeRecorded.emit(False, error)
            return
        trade_side, qty, unit_price, trade_date, trade_time, fx_rate = parsed
        try:
            trade = self._ledger.record_trade(
                asset_id, trade_side, qty, unit_price, trade_date=trade_date, trade_time=trade_time, fx_rate_to_try=fx_rate
            )
        except ValueError as exc:
            self.tradeRecorded.emit(False, str(exc))
            return
        asset = self._ledger.get_asset(asset_id)
        label = "ALIM" if trade.side == TradeSide.BUY else "SATIM"
        self.tradeRecorded.emit(True, msg("assets.islemi_kaydedildi", symbol=asset.symbol, label=label))
        self.dataChanged.emit()

    @Slot(int)
    def removeAsset(self, asset_id: int) -> None:
        if self._ledger is None:
            self.assetRemoved.emit(False, msg("assets.varlik_servisi_kullanilamiyor"))
            return
        try:
            self._ledger.remove_asset(asset_id)
        except ValueError as exc:
            self.assetRemoved.emit(False, str(exc))
            return
        self.assetRemoved.emit(True, msg("assets.varlik_kaldirildi"))
        self.assetsChanged.emit()
        self.dataChanged.emit()
