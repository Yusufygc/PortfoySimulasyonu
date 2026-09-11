"""
SimulationController — SimulationView'un veri köprüsü (bkz. plan §7.3 madde 6, d5).

Backend: `DCABacktestService` (Faz 2 b5, `container.dca_backtest_service`) —
"her ay X TL hisse alsaydım" senaryosunu yerel DB fiyat geçmişiyle çalıştırır.
Hesap mantığı burada yeniden yazılmadı, sadece QML-bindable şekle çevrildi.

Kapsam notu (plan aslıyla karşılaştırıldığında dürüstçe belirtilen fark):
* Plan'ın "Periyodik yeniden dengeleme (Rebalance) karşılaştırması" maddesi
  BU GÖRÜNÜMDE YOK — backend'in kendisi bunu v1 kapsamı dışında bırakmıştı
  (bkz. plan §9.12: `OptimizationService` şu an yalnızca CANLI portföyü
  optimize edebiliyor, tarihsel bir noktada değil; bu refactor ayrı bir
  alt-faz). İcat edilmiş bir karşılaştırma eklenmedi.

Diğer d-view'lerden fark: bu görünümün karşılığı olan bir QtWidgets sayfası
HİÇ yok (`DCABacktestService` Faz 2'den beri hiçbir UI'ya bağlı değildi) —
bu nedenle başlangıçta boş bir form durumu vardır (ticker girilip "Çalıştır"a
basılana kadar `hasResult=False`), diğer controller'ların aksine constructor'da
otomatik bir simülasyon ÇALIŞTIRILMAZ (henüz girdi yok).
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, List

from src.qt_compat.qtcore import Property, QObject, Signal, Slot

_RANGE_KEYS = ("1Y", "3Y", "5Y", "MAX")
_RANGE_LABELS = {"1Y": "1 Yıl", "3Y": "3 Yıl", "5Y": "5 Yıl", "MAX": "Tümü"}
_RANGE_LOOKBACK_DAYS = {"1Y": 365, "3Y": 1095, "5Y": 1825}
_MAX_RANGE_START = date(2000, 1, 1)
_DEFAULT_MONTHLY_CONTRIBUTION = 1000.0


def _to_float(value: Any) -> float:
    return float(value) if value is not None else 0.0


class SimulationController(QObject):
    """DCA (Düzenli Katkı) backtest formu + sonuç serisi/özeti."""

    inputsChanged = Signal()
    resultChanged = Signal()

    def __init__(self, container, parent=None) -> None:
        super().__init__(parent)
        self._container = container

        self._tickers_text = ""
        self._monthly_contribution = _DEFAULT_MONTHLY_CONTRIBUTION
        self._selected_range_key = "3Y"

        self._has_result = False
        self._error_message = ""
        self._total_invested = 0.0
        self._final_value = 0.0
        self._total_return_pct = 0.0
        self._contribution_count = 0
        self._portfolio_value_series: List[float] = []
        self._breakdown_tickers: List[str] = []
        self._breakdown_shares: List[float] = []

    # ------------------------------------------------------------------
    # Form girdileri
    # ------------------------------------------------------------------

    @Property(str, notify=inputsChanged)
    def tickersText(self) -> str:
        return self._tickers_text

    @Slot(str)
    def setTickersText(self, value: str) -> None:
        if value != self._tickers_text:
            self._tickers_text = value
            self.inputsChanged.emit()

    @Property(float, notify=inputsChanged)
    def monthlyContribution(self) -> float:
        return self._monthly_contribution

    @Slot(float)
    def setMonthlyContribution(self, value: float) -> None:
        if value != self._monthly_contribution:
            self._monthly_contribution = value
            self.inputsChanged.emit()

    @Property("QVariantList", constant=True)
    def rangeKeys(self) -> List[str]:
        return list(_RANGE_KEYS)

    @Property("QVariantList", constant=True)
    def rangeLabels(self) -> List[str]:
        return [_RANGE_LABELS[key] for key in _RANGE_KEYS]

    @Property(str, notify=inputsChanged)
    def selectedRangeKey(self) -> str:
        return self._selected_range_key

    @Slot(str)
    def setSelectedRangeKey(self, key: str) -> None:
        if key in _RANGE_KEYS and key != self._selected_range_key:
            self._selected_range_key = key
            self.inputsChanged.emit()

    # ------------------------------------------------------------------
    # Sonuç: hata / boş durum
    # ------------------------------------------------------------------

    @Property(bool, notify=resultChanged)
    def hasResult(self) -> bool:
        return self._has_result

    @Property(str, notify=resultChanged)
    def errorMessage(self) -> str:
        return self._error_message

    # ------------------------------------------------------------------
    # Özet + Seri
    # ------------------------------------------------------------------

    @Property(float, notify=resultChanged)
    def totalInvested(self) -> float:
        return self._total_invested

    @Property(float, notify=resultChanged)
    def finalValue(self) -> float:
        return self._final_value

    @Property(float, notify=resultChanged)
    def totalReturnPct(self) -> float:
        return self._total_return_pct

    @Property(int, notify=resultChanged)
    def contributionCount(self) -> int:
        return self._contribution_count

    @Property("QVariantList", notify=resultChanged)
    def portfolioValueSeries(self) -> List[float]:
        return list(self._portfolio_value_series)

    @Property("QVariantList", notify=resultChanged)
    def breakdownTickers(self) -> List[str]:
        return list(self._breakdown_tickers)

    @Property("QVariantList", notify=resultChanged)
    def breakdownShares(self) -> List[float]:
        return list(self._breakdown_shares)

    # ------------------------------------------------------------------
    # Simülasyonu çalıştır
    # ------------------------------------------------------------------

    @Slot()
    def runSimulation(self) -> None:
        tickers = [t.strip().upper() for t in self._tickers_text.split(",") if t.strip()]
        if len(tickers) < 1:
            self._fail("En az bir hisse ticker'ı girin (örn. AKBNK, FROTO).")
            return
        if self._monthly_contribution <= 0:
            self._fail("Aylık katkı tutarı sıfırdan büyük olmalıdır.")
            return

        try:
            contribution_amount = Decimal(str(self._monthly_contribution))
        except InvalidOperation:
            self._fail("Geçersiz aylık katkı tutarı.")
            return

        end_date = date.today()
        start_date = self._resolve_start_date()

        try:
            result = self._container.dca_backtest_service.run(
                tickers=tickers,
                monthly_contribution=contribution_amount,
                start_date=start_date,
                end_date=end_date,
            )
        except Exception as exc:
            self._fail(str(exc))
            return

        if not result.portfolio_value_series:
            self._fail("Seçilen dönemde/hisselerde yeterli fiyat verisi bulunamadı.")
            return

        self._total_invested = _to_float(result.total_invested)
        self._final_value = _to_float(result.final_value)
        self._total_return_pct = _to_float(result.total_return_pct)
        self._contribution_count = result.contribution_count

        sorted_dates = sorted(result.portfolio_value_series.keys())
        self._portfolio_value_series = [_to_float(result.portfolio_value_series[d]) for d in sorted_dates]

        self._breakdown_tickers = list(result.shares_by_ticker.keys())
        self._breakdown_shares = [_to_float(v) for v in result.shares_by_ticker.values()]

        self._has_result = True
        self._error_message = ""
        self.resultChanged.emit()

    def _resolve_start_date(self) -> date:
        if self._selected_range_key == "MAX":
            return _MAX_RANGE_START
        lookback_days = _RANGE_LOOKBACK_DAYS.get(self._selected_range_key, _RANGE_LOOKBACK_DAYS["3Y"])
        return date.today() - timedelta(days=lookback_days)

    def _fail(self, message: str) -> None:
        self._has_result = False
        self._error_message = message
        self.resultChanged.emit()
