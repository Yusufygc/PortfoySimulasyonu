"""Hisse detayı veri yükleme: ana ve model portföy pozisyonu, güncel fiyat, işlem ve sermaye artırımı listeleri (arka plan iş parçacığında çalışır)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import logging
from typing import Any, Dict, Optional

from src.domain.models.model_portfolio import ModelTradeSide
from src.domain.models.trade import TradeSide
from src.domain.ticker import clean_ticker
from src.ui_qml.messages import msg

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
        clean = clean_ticker(ticker)
        cur_price = 0.0
        diff = 0.0

        # 1. Güncel fiyat: canlı fiyat yalnızca son kapanıştan daha yeni bir güne aitse kullanılır
        resolver = getattr(self._container, "current_price_resolver", None) if self._container else None
        if resolver is not None and stock_id:
            try:
                resolved = resolver.resolve([stock_id]).get(stock_id)
                if resolved is not None:
                    cur_price = float(resolved.price)
                    change = resolver.daily_change_pct(stock_id, resolved)
                    return cur_price, float(change) if change is not None else 0.0
            except Exception as res_err:
                logger.debug("current_price_resolver başarısız: %s", res_err)

        lookup = getattr(self._container, "stock_lookup_service", None) if self._container else None

        # 1b. Eski yol: önce canlı fiyat önbelleği (latest_prices), önceki kapanışa göre günlük değişim
        if lookup is not None and stock_id:
            live = lookup.get_latest_price_map([stock_id]).get(stock_id)
            if live is not None:
                cur_price = float(live)
            if cur_price > 0:
                prev_close = lookup.get_previous_close(stock_id)
                if prev_close:
                    p_close = float(prev_close)
                    return cur_price, ((cur_price - p_close) / p_close) * 100.0

        # 2. DuckDB piyasa geçmişi (salt okunur depo; yalnızca geçerli kapanışlar)
        if lookup is not None:
            bars = lookup.get_last_market_bars(clean, 2)
            if bars:
                p1 = bars[0].close_price
                p2 = bars[1].close_price if len(bars) > 1 else p1
                d = ((p1 - p2) / p2 * 100.0) if p2 > 0 else 0.0
                if cur_price <= 0:
                    cur_price = p1
                if diff == 0.0:
                    diff = d
                return cur_price, diff

        # 3. Yedek: SQLite günlük kapanışı
        if lookup is not None:
            close = lookup.get_previous_close(stock_id) if stock_id else lookup.get_latest_close(clean)
            if close:
                if cur_price <= 0:
                    cur_price = float(close)
                return cur_price, diff

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
        lookup = getattr(self._container, "stock_lookup_service", None)
        lp_map = lookup.get_latest_price_map(stock_ids) if lookup is not None else {}

        for sid, pos in portfolio.positions.items():
            if pos.total_quantity > 0:
                p_val = lp_map.get(sid)
                if p_val is not None and p_val > 0:
                    pos_val = Decimal(str(pos.total_quantity)) * p_val
                else:
                    pos_val = pos.total_cost
                total_portfolio_val += pos_val

        cash = portfolio_service.get_cash_balance()
        data["cash"] = float(cash) if cash is not None else None
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
                        "splitNote": msg("stock_detail.bolunme_oncesi_lot", orig_qty=orig_qty, orig_price=orig_price) if has_split else "",
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
            if summary.get("remaining_cash") is not None:
                data["cash"] = float(summary["remaining_cash"])

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
