"""
PortfolioController — Portföy özeti için ilk QML controller (bkz. plan §7.1, d1
Controller/Model Temel Katman). DashboardView'un asıl görsel/etkileşim katmanı
d2'de kurulur; bu controller o katmanın üzerine bineceği veri köprüsüdür.

Backend: mevcut `ReturnCalcService.compute_portfolio_value_on()` (carry-forward
fiyat doldurma dahil, mevcut QtWidgets Dashboard'un da kullandığı hesap — bkz.
`dashboard_presenter.py`) + `latest_price_repo` ile canlı fiyat üstüne yazma +
`stock_repo` ile ticker çözümleme. Hesap mantığı burada yeniden yazılmadı.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List

from src.qt_compat.qtcore import Property, QObject, Signal, Slot
from src.ui_qml.models.base_table_model import ColumnSpec, ListTableModel

_POSITION_COLUMNS = (
    ColumnSpec("Hisse", lambda row: row["ticker"]),
    ColumnSpec("Lot", lambda row: row["quantity"]),
    ColumnSpec("Ort. Maliyet", lambda row: row["average_cost"]),
    ColumnSpec("Güncel Fiyat", lambda row: row["current_price"]),
    ColumnSpec("K/Z", lambda row: row["unrealized_pl"]),
    ColumnSpec("Ağırlık %", lambda row: row["weight_pct"]),
)


def _to_float(value: Any) -> float:
    return float(value) if value is not None else 0.0


class PortfolioController(QObject):
    """Portföy toplam değeri/maliyeti/K-Z'si ve pozisyon tablosunu QML'e sunar."""

    totalValueChanged = Signal()
    totalCostChanged = Signal()
    unrealizedPlChanged = Signal()

    def __init__(self, container, parent=None) -> None:
        super().__init__(parent)
        self._container = container
        self._total_value = 0.0
        self._total_cost = 0.0
        self._unrealized_pl = 0.0
        self._positions_model = ListTableModel(columns=_POSITION_COLUMNS, parent=self)
        self.refresh()

    # ------------------------------------------------------------------
    # QML'e açılan property'ler
    # ------------------------------------------------------------------

    @Property(float, notify=totalValueChanged)
    def totalValue(self) -> float:
        return self._total_value

    @Property(float, notify=totalCostChanged)
    def totalCost(self) -> float:
        return self._total_cost

    @Property(float, notify=unrealizedPlChanged)
    def unrealizedPl(self) -> float:
        return self._unrealized_pl

    @Property(QObject, constant=True)
    def positionsModel(self) -> ListTableModel:
        return self._positions_model

    # ------------------------------------------------------------------
    # Veri yenileme
    # ------------------------------------------------------------------

    @Slot()
    def refresh(self) -> None:
        rows, total_value, total_cost, unrealized_pl = self._load_snapshot()
        self._positions_model.set_rows(rows)
        self._set_total_value(total_value)
        self._set_total_cost(total_cost)
        self._set_unrealized_pl(unrealized_pl)

    def _set_total_value(self, value: float) -> None:
        if value != self._total_value:
            self._total_value = value
            self.totalValueChanged.emit()

    def _set_total_cost(self, value: float) -> None:
        if value != self._total_cost:
            self._total_cost = value
            self.totalCostChanged.emit()

    def _set_unrealized_pl(self, value: float) -> None:
        if value != self._unrealized_pl:
            self._unrealized_pl = value
            self.unrealizedPlChanged.emit()

    def _load_snapshot(self) -> tuple[List[Dict[str, Any]], float, float, float]:
        today = date.today()
        snapshot = self._container.return_calc_service.compute_portfolio_value_on(today)
        portfolio = self._container.portfolio_service.get_current_portfolio()
        positions = list(portfolio.active_positions.values())
        stock_ids = [p.stock_id for p in positions]

        # `snapshot.total_value`/`total_unrealized_pl`, canlı fiyat üstüne yazılmadan ÖNCEKİ
        # `snapshot.price_map`'e göre hesaplanmıştır — üst-toplamlar satır verisiyle tutarsız
        # kalmasın diye overlay'li `price_map` üzerinden Portfolio metodlarıyla yeniden hesaplanır
        # (bkz. `dashboard_presenter.on_prices_updated_event`'teki aynı desen).
        price_map: Dict[int, Decimal] = dict(snapshot.price_map)
        price_map.update(self._latest_price_overlay(stock_ids))
        ticker_map = self._container.stock_repo.get_ticker_map_for_stock_ids(stock_ids)

        total_value = portfolio.total_market_value(price_map)
        total_unrealized_pl = portfolio.total_unrealized_pl(price_map)
        rows = [
            self._position_row(position, ticker_map, price_map, total_value)
            for position in positions
        ]
        return rows, _to_float(total_value), _to_float(snapshot.total_cost), _to_float(total_unrealized_pl)

    @staticmethod
    def _position_row(
        position, ticker_map: Dict[int, str], price_map: Dict[int, Decimal], total_value: Decimal,
    ) -> Dict[str, Any]:
        price = price_map.get(position.stock_id)
        market_value = position.market_value(price) if price is not None else Decimal("0")
        weight_pct = round(_to_float(market_value / total_value * 100), 2) if total_value else 0.0
        return {
            "ticker": ticker_map.get(position.stock_id, "?"),
            "quantity": position.total_quantity,
            "average_cost": _to_float(position.average_cost),
            "current_price": _to_float(price),
            "unrealized_pl": _to_float(position.unrealized_pl(price)) if price is not None else 0.0,
            "weight_pct": weight_pct,
        }

    def _latest_price_overlay(self, stock_ids: List[int]) -> Dict[int, Decimal]:
        latest_price_repo = getattr(self._container, "latest_price_repo", None)
        if latest_price_repo is None or not stock_ids:
            return {}
        return latest_price_repo.get_latest_price_map(stock_ids)
