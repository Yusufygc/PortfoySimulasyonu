"""Hisse detayı veri yükleme: ana ve model portföy pozisyonu, güncel fiyat, işlem ve sermaye artırımı listeleri (arka plan iş parçacığında çalışır)."""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any, Dict, Optional

from src.domain.models.model_portfolio import ModelTradeSide
from src.domain.models.trade import TradeSide
from src.ui_qml.messages import msg
from src.ui_qml.presenters.formatting import tr_number

logger = logging.getLogger(__name__)


class StockDetailLoaderMixin:
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
                "portfolio_name": msg("stock_detail.ana_portfoy") if ctx_type == "main" else msg("stock_detail.model_portfoy", ctx_id=ctx_id),
                "trades": [],
                "corp_actions": [],
            }

            # 1. Hisse Tanımını Bul
            lookup = getattr(self._container, "stock_lookup_service", None) if self._container else None
            stock_obj = lookup.find_stock(ticker) if lookup else None
            if stock_obj:
                data["stock_id"] = stock_obj.id
                clean_name = (stock_obj.name or ticker).replace(".IS", "").strip()
                data["company_name"] = clean_name
                data["sector"] = getattr(stock_obj, "sector", "BIST") or "BIST"

            # 2. Güncel Fiyatı Çek (Önce canlı fiyat önbelleği, sonra DuckDB/yedek)
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
                                "ratioStr": f"%{tr_number(float(a.ratio_percent), 1)}",
                                "applied": bool(a.applied),
                            })
                    except Exception as ca_exc:
                        logger.warning("Kurumsal islemleri okuma hatasi: %s", ca_exc)

            self._asyncDataReady.emit(data)

        except Exception as e:
            logger.exception("Hisse detay veri getirme hatası (%s): %s", ticker, e)
            self._asyncDataReady.emit({"error": str(e), "ticker": ticker})

    def _get_latest_price(self, ticker: str, stock_id: Optional[int] = None) -> tuple[float, float]:
        """En güncel fiyatı ve dünkü kapanışa göre yüzdesel farkı döndürür (`PositionQueryService.quote`)."""
        service = getattr(self._container, "position_query_service", None) if self._container else None
        if service is None:
            return 0.0, 0.0
        quote = service.quote(ticker, stock_id)
        return float(quote.price), float(quote.daily_change_pct)

    @staticmethod
    def _apply_snapshot(data: Dict[str, Any], snapshot: Any) -> None:
        """Pozisyon özetini görünüm sözlüğüne yazar (rakamlar `PositionSnapshot`'tan, hesap yok)."""
        pl_pct = snapshot.unrealized_pl_pct
        data["quantity"] = snapshot.quantity
        data["avg_cost"] = float(snapshot.avg_cost)
        data["market_value"] = float(snapshot.market_value)
        data["unrealized_pnl"] = float(snapshot.unrealized_pl)
        data["unrealized_pnl_pct"] = float(pl_pct) if pl_pct is not None else 0.0
        data["portfolio_weight_pct"] = float(snapshot.weight_pct)

    def _load_main_position_data(self, data: Dict[str, Any], stock_obj: Any, cur_price: float) -> None:
        """Ana portföyden bu hisseye ait pozisyon ve işlem listesini yükler."""
        if not self._container:
            return

        portfolio_service = getattr(self._container, "portfolio_service", None)
        if not portfolio_service:
            return

        query = getattr(self._container, "position_query_service", None)
        if query is not None:
            positions = query.main_positions()
            data["cash"] = float(positions.cash)
            snapshot = positions.find(stock_obj.id) if stock_obj and stock_obj.id else None
            if snapshot is not None:
                self._apply_snapshot(data, snapshot)

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
                        "quantityStr": f"{tr_number(qty, 0)} Lot",
                        "price": price,
                        "priceStr": f"₺{tr_number(price)}",
                        "total": tot,
                        "totalStr": f"₺{tr_number(tot)}",
                        "hasSplit": has_split,
                        "origQuantity": orig_qty,
                        "origPrice": orig_price,
                        "splitNote": msg("stock_detail.bolunme_oncesi_lot", orig_qty=tr_number(orig_qty, 0), orig_price=tr_number(orig_price)) if has_split else "",
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

        query = getattr(self._container, "position_query_service", None)
        try:
            if query is not None:
                positions = query.model_positions(port_id)
                data["cash"] = float(positions.cash)
                snapshot = positions.find(stock_obj.id) if stock_obj and stock_obj.id else None
                if snapshot is not None:
                    self._apply_snapshot(data, snapshot)
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
                        "quantityStr": f"{tr_number(qty, 0)} Lot",
                        "price": price,
                        "priceStr": f"₺{tr_number(price)}",
                        "total": tot,
                        "totalStr": f"₺{tr_number(tot)}",
                        "hasSplit": False,
                        "splitNote": "",
                    })
            except Exception as me:
                logger.warning("Model portfoy islemleri okunamadi: %s", me)
