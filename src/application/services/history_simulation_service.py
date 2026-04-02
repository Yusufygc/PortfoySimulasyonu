# src/application/services/history_simulation_service.py

from datetime import date, timedelta
from decimal import Decimal
from typing import Tuple, List

from src.domain.models.daily_price import DailyPrice
from src.domain.repositories.portfolio_repository import IPortfolioRepository
from src.domain.repositories.price_repository import IPriceRepository
from src.domain.repositories.stock_repository import IStockRepository
from src.domain.services_interfaces.i_market_data_client import IMarketDataClient
from src.application.services.daily_history_models import DailyPosition, DailyPortfolioSnapshot
from src.domain.models.portfolio import Portfolio

class HistorySimulationService:
    def __init__(
        self,
        portfolio_repo: IPortfolioRepository,
        price_repo: IPriceRepository,
        stock_repo: IStockRepository,
        market_data_client: IMarketDataClient,
    ) -> None:
        self.portfolio_repo = portfolio_repo
        self.price_repo = price_repo
        self.stock_repo = stock_repo
        self.market_data_client = market_data_client

    def simulate_history(self, start_date: date, end_date: date) -> Tuple[List[DailyPosition], List[DailyPortfolioSnapshot]]:
        if end_date < start_date:
            start_date, end_date = end_date, start_date

        all_trades = self.portfolio_repo.get_all_trades()
        relevant_trades = [t for t in all_trades if t.trade_date <= end_date]

        if not relevant_trades:
            return [], []

        from datetime import time as dt_time
        relevant_trades.sort(key=lambda t: (t.trade_date, getattr(t, "trade_time", None) or dt_time.min))

        stocks = self.stock_repo.get_all_stocks()
        ticker_map = {s.id: s.ticker for s in stocks}

        trade_idx = 0
        n_trades = len(relevant_trades)

        daily_positions = []
        daily_snapshots = []
        last_close_by_stock = {}
        last_portfolio_value = None
        base_portfolio_value = None

        portfolio = Portfolio()

        cur = start_date
        while cur <= end_date:
            while trade_idx < n_trades and relevant_trades[trade_idx].trade_date <= cur:
                portfolio.apply_trade(relevant_trades[trade_idx])
                trade_idx += 1

            active_stock_ids = [sid for sid, p in portfolio.positions.items() if p.total_quantity > 0]
            prices_for_day = self.price_repo.get_prices_for_date(cur)
            
            is_weekend = cur.weekday() >= 5
            if not is_weekend and active_stock_ids:
                missing_ids = [sid for sid in active_stock_ids if sid not in prices_for_day]
                if missing_ids:
                    missing_tickers = [ticker_map.get(sid) for sid in missing_ids if sid in ticker_map]
                    if missing_tickers:
                        try:
                            fetched_prices = self.market_data_client.get_closing_prices(
                                stock_ids=missing_ids, tickers=missing_tickers, price_date=cur
                            )
                            new_daily_prices = []
                            for sid, p in fetched_prices.items():
                                prices_for_day[sid] = p
                                new_daily_prices.append(DailyPrice(
                                    id=None, stock_id=sid, price_date=cur, close_price=p
                                ))
                            if new_daily_prices:
                                self.price_repo.upsert_daily_prices_bulk(new_daily_prices)
                        except Exception:
                            pass

            has_prices = bool(prices_for_day)
            day_positions_list = []
            portfolio_value = None
            total_cost_basis = Decimal("0")

            if has_prices:
                total_value = portfolio.total_market_value(prices_for_day)
                total_cost_basis = portfolio.total_cost()
                
                for stock_id, position in portfolio.positions.items():
                    qty = position.total_quantity
                    if qty <= 0: continue

                    avg_cost = position.average_cost or Decimal("0")
                    cost_basis = position.total_cost
                    close_price = prices_for_day.get(stock_id)

                    if close_price:
                        pos_val = position.market_value(close_price)
                        
                        last_c = last_close_by_stock.get(stock_id)
                        daily_chg = ((close_price / last_c) - 1) if (last_c and last_c != 0) else None
                        
                        unrealized_tl = position.unrealized_pl(close_price)
                        unrealized_pct = (unrealized_tl / cost_basis) if cost_basis != 0 else None

                        if last_c and last_c != 0:
                            daily_pnl_stock = (close_price - last_c) * Decimal(qty)
                        else:
                            daily_pnl_stock = unrealized_tl
                    else:
                        pos_val, daily_chg, daily_pnl_stock, unrealized_tl, unrealized_pct = None, None, None, None, None

                    w_pct = (pos_val / total_value) if (pos_val and total_value) else None
                    
                    day_positions_list.append(DailyPosition(
                        date=cur,
                        ticker=ticker_map.get(stock_id, f"ID_{stock_id}"),
                        quantity=qty,
                        avg_cost=avg_cost,
                        cost_basis=cost_basis,
                        close_price=close_price,
                        position_value=pos_val,
                        daily_price_change_pct=daily_chg,
                        daily_pnl_tl=daily_pnl_stock,
                        unrealized_pnl_tl=unrealized_tl,
                        unrealized_pnl_pct=unrealized_pct,
                        weight_pct=w_pct
                    ))
                
                if total_value > 0:
                    portfolio_value = total_value
                    last_close_by_stock = prices_for_day.copy()
            else:
                portfolio_value = last_portfolio_value if last_portfolio_value else None

            daily_pnl, daily_ret, cum_pnl, cum_ret = None, None, None, None
            if portfolio_value:
                if not base_portfolio_value: 
                    base_portfolio_value = portfolio_value
                
                if last_portfolio_value:
                    daily_pnl = portfolio_value - last_portfolio_value
                    daily_ret = (daily_pnl / last_portfolio_value)
                elif total_cost_basis > 0:
                    daily_pnl = portfolio_value - total_cost_basis
                    daily_ret = (daily_pnl / total_cost_basis)
                
                if base_portfolio_value:
                    if portfolio_value == base_portfolio_value and total_cost_basis > 0:
                        cum_pnl = portfolio_value - total_cost_basis
                        cum_ret = (cum_pnl / total_cost_basis)
                    else:
                        if total_cost_basis > 0:
                            cum_pnl = portfolio_value - total_cost_basis
                            cum_ret = (cum_pnl / total_cost_basis)
                        else:
                            cum_pnl = portfolio_value - base_portfolio_value
                            cum_ret = (cum_pnl / base_portfolio_value)

            status = "Piyasa Açık" if has_prices else ("Hafta Sonu" if is_weekend else "Veri Yok")
            
            if day_positions_list:
                daily_positions.extend(day_positions_list)
            
            daily_snapshots.append(DailyPortfolioSnapshot(
                total_cost_basis=total_cost_basis,
                date=cur, total_value=portfolio_value, 
                daily_return_pct=daily_ret, cumulative_return_pct=cum_ret,
                daily_pnl=daily_pnl, cumulative_pnl=cum_pnl, status=status
            ))

            if portfolio_value: last_portfolio_value = portfolio_value
            cur += timedelta(days=1)

        return daily_positions, daily_snapshots

