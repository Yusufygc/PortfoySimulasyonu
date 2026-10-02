"""Piyasa geçmişi (DuckDB) için sermaye artırımı/bölünme tespiti, onayı ve doğrulaması.

Akış:
1. `scan`: ham seride büyük günlük kırılmaları bulur, veri hatası (tek barlık sıçrama) ve piyasa genelindeki
   hareketi ayıklar, kalanları ADAY olarak kaydeder.
2. Kullanıcı `confirm` (faktör düzenlenebilir) veya `ignore` der. Yalnızca ONAYLI olaylar fiyatları düzeltir.
3. `verify_actions`: ham veride kırılma artık görünmüyorsa (kaynak sonradan düzeltmiş) olay NO_BREAK olur;
   böylece aynı bölünme iki kez uygulanmaz.
Ham barlara asla dokunulmaz.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from typing import Dict, List, Optional

from src.domain.models.market_corporate_action import (
    MarketActionSource,
    MarketActionStatus,
    MarketActionType,
    MarketCorporateAction,
    PriceBreak,
)
from src.domain.ports.repositories.i_market_corporate_action_repo import IMarketCorporateActionRepository
from src.domain.ports.repositories.i_market_history_repo import IMarketHistoryRepository

logger = logging.getLogger(__name__)

DEFAULT_MIN_DATE = date(2006, 1, 1)  # 2005 TL redenominasyonu öncesi bozuk Yahoo geçmişi taranmaz
DROP_RATIO = 1.25  # BIST günlük limiti %10; bunun üstü piyasa hareketi değil kurumsal aksiyon/veri hatasıdır
RISE_RATIO = 2.0  # birleştirme (ters bölünme) adayı: tek günde >= 2 kat
_IDIOSYNCRATIC_DROP = 1.2  # piyasadan arındırılmış önceki/yeni kapanış en az bu kadar olmalı
_IDIOSYNCRATIC_RISE = 1.8
_REVERT_TOLERANCE = 0.12
_DUPLICATE_WINDOW_DAYS = 5
_MARKET_RATIO_BOUNDS = (0.6, 1.6)  # kriz günlerinde piyasa medyanı %15+ oynayabilir; bunun ötesi veri hatasıdır


@dataclass
class ScanResult:
    new_candidates: List[MarketCorporateAction] = field(default_factory=list)
    glitches: int = 0
    already_known: int = 0


def _is_glitch(brk: PriceBreak) -> bool:
    """Fiyat kısa sürede önceki seviyeye dönüyorsa (veya önceki bar tek barlık sıçramaysa) veri hatasıdır."""
    for nxt in brk.next_closes:
        if brk.prev_close > 0 and abs(nxt / brk.prev_close - 1.0) < _REVERT_TOLERANCE:
            return True
    if brk.prev2_close and brk.close > 0 and abs(brk.prev2_close / brk.close - 1.0) < _REVERT_TOLERANCE:
        return True
    return False


def classify_break(brk: PriceBreak) -> Optional[MarketCorporateAction]:
    """Kırılmayı ADAY olaya çevirir; veri hatasıysa None. Faktör, aynı günkü piyasa hareketinden arındırılır."""
    if _is_glitch(brk):
        return None
    market_ratio = brk.market_ratio or 1.0
    low, high = _MARKET_RATIO_BOUNDS
    if not (low <= market_ratio <= high):
        market_ratio = 1.0
    observed = brk.observed_ratio
    factor = (brk.close / brk.prev_close) * market_ratio
    if factor <= 0:
        return None
    # Piyasa genelindeki sert düşüş/yükseliş (kriz günleri) hisseye özgü bir olay değildir
    if 1.0 / _IDIOSYNCRATIC_DROP < factor < _IDIOSYNCRATIC_RISE:
        return None
    confidence = 0.5
    if factor > 0.67 and factor < 1.0:
        confidence -= 0.2  # küçük kırılma: gerçek bir piyasa düşüşü de olabilir
    if (brk.volume or 0) > 0 and (brk.prev_volume or 0) > 0:
        confidence += 0.2
    if (brk.price_date - brk.prev_date).days <= 5:
        confidence += 0.2
    if brk.market_ratio is None:
        confidence -= 0.2
    return MarketCorporateAction(
        ticker=brk.ticker,
        effective_date=brk.price_date,
        factor=factor,
        action_type=MarketActionType.REVERSE_SPLIT if factor > 1 else MarketActionType.OTHER,
        status=MarketActionStatus.CANDIDATE,
        source=MarketActionSource.DETECTED,
        observed_ratio=observed,
        confidence=round(min(max(confidence, 0.1), 0.95), 2),
        note=f"Veriden tespit: önceki/yeni kapanış {observed:.3f}, piyasa medyanı {brk.market_ratio or 1.0:.3f}",
    )


class MarketCorporateActionService:
    def __init__(
        self,
        history_repo: IMarketHistoryRepository,
        action_repo: IMarketCorporateActionRepository,
    ) -> None:
        self._history = history_repo
        self._actions = action_repo

    # ---- tespit ------------------------------------------------------------------------
    def scan(self, min_date: date = DEFAULT_MIN_DATE) -> ScanResult:
        result = ScanResult()
        known: dict[str, list[date]] = {}
        for action in self._actions.list_actions():
            known.setdefault(action.ticker, []).append(action.effective_date)

        for brk in self._history.find_price_breaks(min_date, DROP_RATIO, RISE_RATIO):
            window = timedelta(days=_DUPLICATE_WINDOW_DAYS)
            if any(abs(d - brk.price_date) <= window for d in known.get(brk.ticker, [])):
                result.already_known += 1
                continue
            candidate = classify_break(brk)
            if candidate is None:
                result.glitches += 1
                continue
            self._actions.upsert(candidate)
            known.setdefault(brk.ticker, []).append(brk.price_date)
            result.new_candidates.append(candidate)
        logger.info(
            "Kurumsal aksiyon taraması: %d yeni aday, %d veri hatası, %d zaten kayıtlı",
            len(result.new_candidates), result.glitches, result.already_known,
        )
        return result

    # ---- kullanıcı kararları -----------------------------------------------------------
    def confirm(self, ticker: str, effective_date: date, factor: Optional[float] = None) -> MarketCorporateAction:
        action = self._require(ticker, effective_date)
        updated = replace(action, status=MarketActionStatus.CONFIRMED, factor=factor or action.factor)
        self._actions.upsert(updated)
        return updated

    def ignore(self, ticker: str, effective_date: date) -> None:
        self._require(ticker, effective_date)
        self._actions.set_status(ticker, effective_date, MarketActionStatus.IGNORED)

    def register(self, action: MarketCorporateAction) -> MarketCorporateAction:
        """Dış kaynaktan (KAP aday onayı, portföy akışı, elle giriş) gelen olayı kaydeder ve doğrular."""
        self._actions.upsert(action)
        if action.status == MarketActionStatus.CONFIRMED:
            self.verify_actions(action.ticker)
        return self._require(action.ticker, action.effective_date)

    # ---- portföy akışıyla köprü --------------------------------------------------------
    def locate_effective_date(self, ticker: str, ex_date: date, factor: float) -> Optional[date]:
        """Ham seride, beklenen kırılmaya (1/faktör) en yakın ardışık bar çiftinin ikinci günü (ex-date +-10 gün)."""
        bars = self._history.get_price_series(
            ticker, ex_date - timedelta(days=10), ex_date + timedelta(days=10), adjusted=False
        )
        target = 1.0 / factor
        best: Optional[tuple[float, date]] = None
        for prev, cur in zip(bars, bars[1:]):
            if cur.close_price <= 0:
                continue
            error = abs(prev.close_price / cur.close_price - target) / target
            if error < 0.15 and (best is None or error < best[0]):
                best = (error, cur.price_date)
        return best[1] if best else None

    def register_portfolio_action(self, ticker: str, action) -> Optional[MarketCorporateAction]:
        """Portföye uygulanmış `CorporateAction` (SQLite) olayını DuckDB'ye ONAYLI olarak aktarır.

        `before_date` bilinmiyorsa etkin gün ham veriden bulunur; kırılma bulunamazsa (kaynak zaten
        düzeltmiş) kayıt NO_BREAK olarak tutulur ve fiyatları değiştirmez.
        """
        if action.price_adjustment_factor is None:
            return None
        factor = float(action.price_adjustment_factor)
        effective = self.locate_effective_date(ticker, action.ex_date, factor)
        status = MarketActionStatus.CONFIRMED if effective else MarketActionStatus.NO_BREAK
        stored = MarketCorporateAction(
            ticker=ticker.replace(".IS", "").strip().upper(),
            effective_date=effective or action.ex_date,
            factor=factor,
            action_type=MarketActionType(action.action_type.value),
            status=status,
            source=MarketActionSource.PORTFOLIO,
            ex_date=action.ex_date,
            ratio=float(action.ratio),
            rights_price=None if action.subscription_price is None else float(action.subscription_price),
            note="Portföy kurumsal aksiyon akışından aktarıldı",
        )
        self._actions.upsert(stored)
        return stored

    def import_actions_from_adjusted_history(
        self, ticker: str, adjusted_closes: Dict[date, float]
    ) -> List[MarketCorporateAction]:
        """Bir hissenin DÜZELTİLMİŞ kapanış geçmişi (örn. SQLite) ile DuckDB HAM geçmişi arasındaki baz farkından
        geçmiş sermaye artırımlarını türetir ve ONAYLI olarak kaydeder.

        Düzeltilmiş/ham oranı bir olay gününde basamak yapar; basamak oranı faktördür. Yalnızca kalıcı
        (önceki ve sonraki 3 barda sabit kalan), >= %20 büyüklükte basamaklar alınır (temettü düzeltmesi ve
        veri hatası elenir) VE ham serinin kendisi aynı kırılmayı göstermelidir (ham seri zaten düzeltilmişse
        fark düzeltilmiş kaynağın hatasıdır). Zaten kayıtlı bir olayın +-5 günündeki basamak atlanır.
        """
        if len(adjusted_closes) < 8:
            return []
        raw = {
            b.price_date: b.close_price
            for b in self._history.get_price_series(
                ticker, min(adjusted_closes), max(adjusted_closes), adjusted=False
            )
        }
        dates = sorted(d for d, v in adjusted_closes.items() if v and v > 0 and raw.get(d, 0) > 0)
        if len(dates) < 8:
            return []
        ratios = [adjusted_closes[d] / raw[d] for d in dates]
        known = list(self._actions.list_actions(ticker=ticker))
        window = timedelta(days=_DUPLICATE_WINDOW_DAYS)
        created: List[MarketCorporateAction] = []
        for i in range(3, len(dates) - 2):
            before = sorted(ratios[i - 3:i])[1]
            after = sorted(ratios[i:i + 3])[1]
            if after <= 0:
                continue
            factor = before / after
            if 1.0 / _IDIOSYNCRATIC_DROP < factor < _IDIOSYNCRATIC_RISE:
                continue
            # kalıcılık: pencerenin her iki yanı kendi içinde tutarlı olmalı
            if any(abs(r / before - 1.0) > 0.05 for r in ratios[i - 3:i]) or any(
                abs(r / after - 1.0) > 0.05 for r in ratios[i:i + 3]
            ):
                continue
            # DuckDB ham serisinin KENDİSİ bu kırılmayı göstermiyorsa (kaynak zaten düzeltmiş; fark SQLite'ın
            # hatasından kaynaklanıyor) olay üretilmez: aksi halde doğru DuckDB serisi bozulurdu.
            effective = self.locate_effective_date(ticker, dates[i], factor)
            if effective is None:
                continue
            near = next((a for a in known if abs(effective - a.effective_date) <= window), None)
            if near is not None:
                if near.status != MarketActionStatus.CANDIDATE:
                    continue
                # Veriden tespit edilmiş aday: kesin faktörle onayla
                confirmed = replace(
                    near, factor=factor, status=MarketActionStatus.CONFIRMED, source=MarketActionSource.MIGRATION,
                    confidence=0.9, note="Aday, SQLite düzeltilmiş geçmişinden türetilen kesin faktörle onaylandı",
                )
                self._actions.upsert(confirmed)
                known[known.index(near)] = confirmed
                created.append(confirmed)
                continue
            action = MarketCorporateAction(
                ticker=ticker.replace(".IS", "").strip().upper(),
                effective_date=effective,
                factor=factor,
                action_type=MarketActionType.REVERSE_SPLIT if factor > 1 else MarketActionType.OTHER,
                status=MarketActionStatus.CONFIRMED,
                source=MarketActionSource.MIGRATION,
                observed_ratio=1.0 / factor,
                confidence=0.9,
                note="SQLite düzeltilmiş geçmişi ile DuckDB ham geçmişinin farkından türetildi",
            )
            self._actions.upsert(action)
            known.append(action)
            created.append(action)
        return created

    def import_portfolio_actions(self, portfolio_action_repo, stock_repo) -> int:
        """Uygulanmış tüm portföy aksiyonlarını aktarır (idempotent: aynı olay üzerine yazılır)."""
        count = 0
        tickers = {s.id: s.ticker for s in stock_repo.get_all_stocks() if s.id is not None}
        for action in portfolio_action_repo.get_all():
            ticker = tickers.get(action.stock_id)
            if ticker and action.applied and action.prices_adjusted:
                try:
                    if self.register_portfolio_action(ticker, action) is not None:
                        count += 1
                except Exception as exc:
                    logger.warning("Portföy aksiyonu DuckDB'ye aktarılamadı (%s): %s", ticker, exc)
        return count

    # ---- doğrulama ---------------------------------------------------------------------
    def verify_actions(self, ticker: Optional[str] = None) -> List[MarketCorporateAction]:
        """ONAYLI olayların ham veride hâlâ kırılma gösterip göstermediğini denetler; göstermeyenleri NO_BREAK yapar."""
        changed: List[MarketCorporateAction] = []
        for action in self._actions.list_actions(ticker=ticker, status=MarketActionStatus.CONFIRMED):
            if self._break_present(action) is False:
                self._actions.set_status(action.ticker, action.effective_date, MarketActionStatus.NO_BREAK)
                changed.append(replace(action, status=MarketActionStatus.NO_BREAK))
                logger.warning(
                    "%s %s: ham veride kırılma yok (kaynak düzeltmiş olabilir); olay NO_BREAK yapıldı",
                    action.ticker, action.effective_date,
                )
        return changed

    def _break_present(self, action: MarketCorporateAction) -> Optional[bool]:
        """True/False; veri yoksa (karar verilemiyorsa) None."""
        bars = self._history.get_price_series(
            action.ticker, action.effective_date - timedelta(days=15), action.effective_date + timedelta(days=3),
            adjusted=False,
        )
        at = next((b for b in bars if b.price_date == action.effective_date), None)
        before = [b for b in bars if b.price_date < action.effective_date]
        if at is None or not before:
            return None
        observed = before[-1].close_price / at.close_price
        expected = 1.0 / action.factor
        if expected >= 1.0:
            return observed >= 1.0 + 0.5 * (expected - 1.0)
        return observed <= 1.0 - 0.5 * (1.0 - expected)

    def _require(self, ticker: str, effective_date: date) -> MarketCorporateAction:
        for action in self._actions.list_actions(ticker=ticker):
            if action.effective_date == effective_date:
                return action
        raise ValueError(f"Kurumsal aksiyon bulunamadı: {ticker} {effective_date}")
