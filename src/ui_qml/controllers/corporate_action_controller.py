"""
CorporateActionController — Bedelli/bedelsiz sermaye artırımı girişi ve KAP/MKK aday inceleme paneli (QML).

Sorumluluklar:
1. Pozisyon için sermaye artırımı ön izlemesi (yeni lot, yeni ortalama maliyet, teorik baz fiyat)
2. Sermaye artırımını kaydetme + portföye uygulama + geçmiş fiyatları yeniden indirme
3. KAP/MKK aday keşfi, düzenleme, onaylayıp uygulama ve yoksayma

Tüm veri erişimi application servisleri üzerinden yapılır; ağır işler arka planda çalışır.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from src.domain.models.corporate_action import ActionType, BedelliSpec
from src.domain.models.corporate_action_candidate import (
    CorporateActionCandidate,
    CorporateActionCandidateStatus,
)

logger = logging.getLogger(__name__)

_ZERO = Decimal("0")
_ONE = Decimal("1")
_HUNDRED = Decimal("100")


def _clean_ticker(ticker: str) -> str:
    return (ticker or "").replace(".IS", "").strip().upper()


def _to_decimal(value: Any, default: Decimal = _ZERO) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return default


def _fmt_tr(value: Decimal, decimals: int) -> str:
    """1234.5 -> '1.234,50' (Türkçe sayı biçimi)."""
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def _parse_date(text: str) -> Optional[date]:
    text = (text or "").strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def compute_preview(
    current_qty: int,
    total_cost: Decimal,
    current_price: Optional[Decimal],
    action_type: str,
    ratio_pct: Decimal,
    subscription_price: Decimal,
) -> Dict[str, Any]:
    """Sermaye artırımı etkisini hesaplar (BIST kuralı: yeni lotlar aşağı yuvarlanır)."""
    ratio = ratio_pct / _HUNDRED
    is_bedelli = action_type.upper() == "BEDELLI"
    new_shares = int(Decimal(current_qty) * ratio)
    total_qty = current_qty + new_shares

    capital_spent = subscription_price * Decimal(new_shares) if is_bedelli else _ZERO
    new_avg: Optional[Decimal] = None
    if total_qty > 0:
        new_avg = (total_cost + capital_spent) / Decimal(total_qty)

    theoretical: Optional[Decimal] = None
    if current_price and current_price > 0:
        if is_bedelli:
            theoretical = (current_price + ratio * subscription_price) / (_ONE + ratio)
        else:
            theoretical = current_price / (_ONE + ratio)

    return {
        "valid": new_shares > 0,
        "newShares": new_shares,
        "totalQty": total_qty,
        "newShareText": f"+ {new_shares:,} lot".replace(",", "."),
        "totalQtyText": f"{total_qty:,} lot".replace(",", "."),
        "newAvgText": f"{_fmt_tr(new_avg, 4)} ₺" if new_avg is not None else "-",
        "capitalText": f"{_fmt_tr(capital_spent, 2)} ₺",
        "theoreticalText": f"{_fmt_tr(theoretical, 4)} ₺" if theoretical is not None else "-",
    }


class CorporateActionController(QObject):
    """QML context property: corporateActionController"""

    candidatesChanged = Signal()
    busyChanged = Signal()
    detailChanged = Signal()
    # (success, message) — Ayarlar paneli ve diyalog toast'ları için
    notification = Signal(bool, str, arguments=["success", "message"])
    # Sermaye artırımı portföye uygulandı; Dashboard/Model ekranları yenilenmeli
    portfolioChanged = Signal()

    # Worker thread -> Qt ana thread köprüleri
    _applyFinished = Signal(bool, str)
    _discoverFinished = Signal(object, str)
    _candidateActionFinished = Signal(bool, str)

    def __init__(self, container=None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._candidates: List[Dict[str, Any]] = []
        self._candidate_objects: Dict[int, CorporateActionCandidate] = {}
        self._is_busy = False
        self._detail_text = ""

        self._applyFinished.connect(self._on_apply_finished)
        self._discoverFinished.connect(self._on_discover_finished)
        self._candidateActionFinished.connect(self._on_candidate_action_finished)

        if self._review_service is not None:
            self.refreshCandidates()

    # ------------------------------------------------------------------ servisler

    def _svc(self, name: str):
        return getattr(self._container, name, None) if self._container else None

    @property
    def _action_service(self):
        return self._svc("corporate_action_service")

    @property
    def _discovery_service(self):
        return self._svc("corporate_action_discovery_service")

    @property
    def _review_service(self):
        return self._svc("corporate_action_candidate_review_service")

    # ------------------------------------------------------------------ properties

    @Property("QVariantList", notify=candidatesChanged)
    def candidates(self) -> list:
        return self._candidates

    @Property(bool, notify=busyChanged)
    def isBusy(self) -> bool:
        return self._is_busy

    @Property(str, notify=detailChanged)
    def detailText(self) -> str:
        return self._detail_text

    @Property(bool, constant=True)
    def candidateServicesAvailable(self) -> bool:
        return self._discovery_service is not None and self._review_service is not None

    def _set_busy(self, busy: bool) -> None:
        if self._is_busy != busy:
            self._is_busy = busy
            self.busyChanged.emit()

    def _set_detail(self, text: str) -> None:
        self._detail_text = text
        self.detailChanged.emit()

    # ------------------------------------------------------------------ pozisyon bağlamı / ön izleme

    @Slot(str, result="QVariantMap")
    def loadContext(self, ticker: str) -> Dict[str, Any]:
        """Hissenin ana portföydeki pozisyon bilgisini döndürür (diyalog başlığı ve ön izleme için)."""
        empty = {"found": False, "ticker": _clean_ticker(ticker), "quantity": 0,
                 "avgCost": 0.0, "totalCost": 0.0, "currentPrice": 0.0}
        portfolio_service = self._svc("portfolio_service")
        stock_repo = self._svc("stock_repo")
        if portfolio_service is None or stock_repo is None:
            return empty
        try:
            stock = self._resolve_stock(stock_repo, ticker)
            if stock is None:
                return empty
            position = portfolio_service.get_current_portfolio().active_positions.get(stock.id)
            if position is None:
                return empty
            price = 0.0
            resolver = self._svc("current_price_resolver")
            if resolver is not None:
                try:
                    price = float(resolver.price_map([stock.id]).get(stock.id) or 0)
                except Exception as exc:
                    logger.debug("Güncel fiyat okunamadı: %s", exc)
            return {
                "found": True,
                "ticker": _clean_ticker(stock.ticker),
                "stockId": stock.id,
                "quantity": int(position.total_quantity),
                "avgCost": float(position.average_cost or 0),
                "totalCost": float(position.total_cost),
                "currentPrice": price,
            }
        except Exception as exc:
            logger.warning("Sermaye artırımı bağlamı okunamadı (%s): %s", ticker, exc)
            return empty

    @Slot(int, float, float, str, float, float, result="QVariantMap")
    def computePreview(
        self,
        quantity: int,
        total_cost: float,
        current_price: float,
        action_type: str,
        ratio_pct: float,
        subscription_price: float,
    ) -> Dict[str, Any]:
        return compute_preview(
            quantity,
            _to_decimal(total_cost),
            _to_decimal(current_price) if current_price > 0 else None,
            action_type,
            _to_decimal(ratio_pct),
            _to_decimal(subscription_price),
        )

    # ------------------------------------------------------------------ sermaye artırımı uygulama

    @Slot(str, str, float, str, float, str)
    def applyAction(
        self,
        ticker: str,
        action_type: str,
        ratio_pct: float,
        ex_date_text: str,
        subscription_price: float,
        notes: str,
    ) -> None:
        """Kaydet + portföye uygula + geçmiş fiyatları yeniden indir (arka planda)."""
        if self._action_service is None:
            self.notification.emit(False, "Kurumsal aksiyon servisi kullanılamıyor.")
            return
        ex_date = _parse_date(ex_date_text)
        if ex_date is None:
            self.notification.emit(False, "Ex-date geçersiz. Biçim: YYYY-AA-GG")
            return
        if ratio_pct <= 0:
            self.notification.emit(False, "Artırım oranı 0'dan büyük olmalıdır.")
            return
        if action_type.upper() == "BEDELLI" and subscription_price <= 0:
            self.notification.emit(False, "Bedelli işlem için kullanım fiyatı zorunludur.")
            return
        self._set_busy(True)
        self._executor.submit(
            self._apply_worker, ticker, action_type.upper(), _to_decimal(ratio_pct),
            ex_date, _to_decimal(subscription_price), (notes or "").strip() or None,
        )

    def _apply_worker(
        self,
        ticker: str,
        action_type: str,
        ratio_pct: Decimal,
        ex_date: date,
        subscription_price: Decimal,
        notes: Optional[str],
    ) -> None:
        action_id: Optional[int] = None
        try:
            stock_repo = self._svc("stock_repo")
            stock = self._resolve_stock(stock_repo, ticker) if stock_repo else None
            if stock is None:
                raise ValueError(f"Hisse bilgisi bulunamadı: {_clean_ticker(ticker)}")

            service = self._action_service
            ratio = ratio_pct / _HUNDRED
            if action_type == "BEDELSIZ":
                action = service.register_bedelsiz(
                    stock_id=stock.id, ex_date=ex_date, ratio=ratio, notes=notes,
                )
            else:
                action = service.register_bedelli(BedelliSpec(
                    stock_id=stock.id, ex_date=ex_date, ratio=ratio,
                    subscription_price=subscription_price, notes=notes,
                ))
            action_id = action.id

            current_price = None
            resolver = self._svc("current_price_resolver")
            if resolver is not None:
                try:
                    current_price = resolver.price_map([stock.id]).get(stock.id)
                except Exception:
                    current_price = None
            try:
                result = service.apply_action(action_id=action_id, current_price=current_price)
            except Exception:
                # Uygulanamayan kayıt beklemede kalıp yeniden denemeyi engellemesin
                try:
                    service.delete_action(action_id)
                except Exception:
                    logger.warning("Uygulanamayan sermaye artırımı kaydı silinemedi: %s", action_id, exc_info=True)
                raise

            type_label = "Bedelsiz" if result.action_type == ActionType.BEDELSIZ else "Bedelli"
            message = (
                f"{type_label} sermaye artırımı uygulandı: {result.shares_before:,} lot -> "
                f"{result.shares_after:,} lot."
            ).replace(",", ".")
            message += self._refresh_prices_after_action(stock)
            self._applyFinished.emit(True, message)
        except Exception as exc:
            logger.exception("Sermaye artırımı uygulanamadı (%s): %s", ticker, exc)
            self._applyFinished.emit(False, f"Sermaye artırımı uygulanamadı: {exc}")

    def _refresh_prices_after_action(self, stock) -> str:
        """Retroaktif fiyat düzeltmesi sonrası geçmiş fiyatları yeniden indirir; sonuç mesaj eki döner."""
        backfill = self._svc("backfill_service")
        portfolio_service = self._svc("portfolio_service")
        if backfill is None:
            return ""
        try:
            first_date = portfolio_service.get_first_trade_date() if portfolio_service else None
            if first_date is None:
                first_date = date.today() - timedelta(days=365)
            count = backfill.backfill_for_single_stock(
                stock_id=stock.id, ticker=stock.ticker, start_date=first_date, end_date=date.today(),
            )
            return f" {count} günlük fiyat güncellendi."
        except Exception as exc:
            logger.warning("Sermaye artırımı sonrası fiyat güncellemesi başarısız: %s", exc)
            return f" Uyarı: geçmiş fiyatlar güncellenemedi ({exc}); Fiyat Verisi sekmesinden elle güncelleyin."

    def _on_apply_finished(self, success: bool, message: str) -> None:
        self._set_busy(False)
        self.notification.emit(success, message)
        if success:
            self.portfolioChanged.emit()
            self.refreshCandidates()

    @staticmethod
    def _resolve_stock(stock_repo, ticker: str):
        clean = _clean_ticker(ticker)
        if not clean:
            return None
        return stock_repo.get_stock_by_ticker(f"{clean}.IS") or stock_repo.get_stock_by_ticker(clean)

    # ------------------------------------------------------------------ adaylar

    @Slot()
    def refreshCandidates(self) -> None:
        review = self._review_service
        if review is None:
            self._set_detail("Kurumsal aksiyon aday servisleri kullanılamıyor.")
            return
        try:
            items = list(review.list_reviewable())
            candidate_objects = {c.id: c for c in items if c.id is not None}
            candidate_dicts = [self._candidate_to_dict(c) for c in items if c.id is not None]
        except Exception as exc:
            logger.warning("Aday listesi okunamadı: %s", exc)
            self._candidates = []
            self._candidate_objects = {}
            self.candidatesChanged.emit()
            self._set_detail(
                "Aday tablosu okunamadı. Mevcut DB için scripts/apply_corporate_action_candidate_schema.py "
                f"çalıştırılmalıdır.\nHata: {exc}"
            )
            return
        self._candidate_objects = candidate_objects
        self._candidates = candidate_dicts
        self.candidatesChanged.emit()
        if not self._candidates:
            self._set_detail("")

    @Slot()
    def discoverCandidates(self) -> None:
        """KAP/MKK kaynağından yeni adayları arka planda tarar."""
        service = self._discovery_service
        if service is None:
            self.notification.emit(False, "Kurumsal aksiyon aday servisleri kullanılamıyor.")
            return
        if self._is_busy:
            return
        self._set_busy(True)

        def run() -> None:
            try:
                self._discoverFinished.emit(service.discover(), "")
            except Exception as exc:
                logger.exception("Kurumsal aksiyon taraması başarısız: %s", exc)
                self._discoverFinished.emit(None, str(exc))

        self._executor.submit(run)

    def _on_discover_finished(self, result: Any, error: str) -> None:
        self._set_busy(False)
        if result is None:
            self.notification.emit(False, f"Kurumsal aksiyon taraması çalıştırılamadı: {error}")
            return
        self.refreshCandidates()
        if getattr(result, "source_unavailable", False):
            errors = getattr(result, "errors", []) or []
            detail = "\n".join(str(e) for e in errors) or "KAP/MKK kaynağı geçici olarak okunamadı."
            self._set_detail(f"KAP/MKK kaynağı geçici olarak okunamadı.\n\nTeknik detay:\n{detail}")
            self.notification.emit(False, "KAP/MKK kaynağı geçici olarak okunamadı.")
            return
        self.notification.emit(True, f"Kurumsal aksiyon taraması tamamlandı: {result.saved_count} aday.")

    @Slot(int)
    def applyCandidate(self, candidate_id: int) -> None:
        review = self._review_service
        if review is None or self._is_busy:
            return
        self._set_busy(True)

        def run() -> None:
            try:
                outcome = review.approve_and_apply(candidate_id)
                message = outcome.result.description
                stock = self._stock_by_id(outcome.candidate.stock_id)
                if stock is not None:
                    message += self._refresh_prices_after_action(stock)
                self._candidateActionFinished.emit(True, message)
            except Exception as exc:
                logger.warning("Aday uygulanamadı (%s): %s", candidate_id, exc)
                self._candidateActionFinished.emit(False, f"Aday uygulanamadı: {exc}")

        self._executor.submit(run)

    def _on_candidate_action_finished(self, success: bool, message: str) -> None:
        self._set_busy(False)
        self.refreshCandidates()
        self.notification.emit(success, message)
        if success:
            self.portfolioChanged.emit()

    def _stock_by_id(self, stock_id: Optional[int]):
        stock_repo = self._svc("stock_repo")
        if stock_repo is None or stock_id is None:
            return None
        return stock_repo.get_stock_by_id(stock_id)

    @Slot(int)
    def ignoreCandidate(self, candidate_id: int) -> None:
        review = self._review_service
        if review is None:
            return
        try:
            review.ignore(candidate_id)
            self.notification.emit(True, "Aday yoksayıldı.")
        except Exception as exc:
            self.notification.emit(False, f"Aday yoksayılamadı: {exc}")
        self.refreshCandidates()

    @Slot(int, str, str, float, float, str, str)
    def updateCandidate(
        self,
        candidate_id: int,
        ticker: str,
        action_type: str,
        ratio_pct: float,
        subscription_price: float,
        ex_date_text: str,
        notes: str,
    ) -> None:
        review = self._review_service
        current = self._candidate_objects.get(candidate_id)
        if review is None or current is None:
            return
        ex_date = _parse_date(ex_date_text)
        if ex_date is None:
            self.notification.emit(False, "Ex-date geçersiz. Biçim: YYYY-AA-GG")
            return
        try:
            clean = _clean_ticker(ticker)
            stock_repo = self._svc("stock_repo")
            stock = self._resolve_stock(stock_repo, clean) if stock_repo else None
            kind = ActionType(action_type.upper())
            sub_price = _to_decimal(subscription_price)
            updated = CorporateActionCandidate(
                id=current.id,
                ticker=clean,
                stock_id=stock.id if stock is not None else current.stock_id,
                source=current.source,
                source_disclosure_id=current.source_disclosure_id,
                source_url=current.source_url,
                action_type=kind,
                status=current.status,
                ratio=_to_decimal(ratio_pct) / _HUNDRED,
                subscription_price=sub_price if kind == ActionType.BEDELLI and sub_price > 0 else None,
                announcement_date=current.announcement_date,
                ex_date=ex_date,
                confidence=current.confidence,
                raw_payload_json=current.raw_payload_json,
                parse_notes=(notes or "").strip() or None,
                created_at=current.created_at,
                updated_at=current.updated_at,
            )
            review.update_candidate(updated)
            self.notification.emit(True, "Aday güncellendi.")
        except Exception as exc:
            self.notification.emit(False, f"Aday güncellenemedi: {exc}")
        self.refreshCandidates()

    @Slot(int)
    def openCandidateSource(self, candidate_id: int) -> None:
        candidate = self._candidate_objects.get(candidate_id)
        if candidate is not None and candidate.source_url:
            QDesktopServices.openUrl(QUrl(candidate.source_url))

    @Slot(int)
    def selectCandidate(self, candidate_id: int) -> None:
        candidate = self._candidate_objects.get(candidate_id)
        self._set_detail(self._candidate_detail(candidate) if candidate else "")

    # ------------------------------------------------------------------ yardımcılar

    @staticmethod
    def _candidate_to_dict(c: CorporateActionCandidate) -> Dict[str, Any]:
        ratio_pct = float(c.ratio * _HUNDRED) if c.ratio is not None else 0.0
        return {
            "id": c.id,
            "ticker": _clean_ticker(c.ticker),
            "actionType": c.action_type.value,
            "status": c.status.value,
            "ratioPct": ratio_pct,
            "ratioText": f"%{_fmt_tr(_to_decimal(ratio_pct), 2)}" if c.ratio is not None else "-",
            "subscriptionPrice": float(c.subscription_price) if c.subscription_price is not None else 0.0,
            "subscriptionText": f"{_fmt_tr(c.subscription_price, 4)} ₺" if c.subscription_price is not None else "-",
            "exDate": c.ex_date.isoformat() if c.ex_date else "",
            "exDateText": c.ex_date.strftime("%d.%m.%Y") if c.ex_date else "-",
            "confidenceText": f"%{int(c.confidence * _HUNDRED)}",
            "source": c.source,
            "sourceUrl": c.source_url or "",
            "notes": c.parse_notes or "",
            "canApply": c.status in (
                CorporateActionCandidateStatus.READY,
                CorporateActionCandidateStatus.APPROVED,
            ),
        }

    @staticmethod
    def _candidate_detail(c: CorporateActionCandidate) -> str:
        lines = [
            f"Hisse: {_clean_ticker(c.ticker)}",
            f"Tip: {c.action_type.value}",
            f"Durum: {c.status.value}",
            f"Kaynak: {c.source}:{c.source_disclosure_id}",
        ]
        if c.parse_notes:
            lines.append(f"Not: {c.parse_notes}")
        if c.source_url:
            lines.append(f"Kaynak linki: {c.source_url}")
        return "\n".join(lines)
