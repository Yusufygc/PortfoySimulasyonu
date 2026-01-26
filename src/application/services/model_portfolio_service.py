# src/application/services/model_portfolio_service.py

from __future__ import annotations

from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import date, time
from collections import defaultdict

from src.domain.models.model_portfolio import ModelPortfolio, ModelPortfolioTrade, ModelTradeSide
from src.domain.models.stock import Stock
from src.domain.services_interfaces.i_model_portfolio_repo import IModelPortfolioRepository
from src.domain.services_interfaces.i_stock_repo import IStockRepository


class ModelPortfolioService:
    """
    Model Portföy iş mantığı servisi.
    Portföy CRUD işlemleri ve hisse alım/satım işlemlerini yönetir.
    """

    def __init__(
        self,
        model_portfolio_repo: IModelPortfolioRepository,
        stock_repo: IStockRepository,
    ) -> None:
        self._portfolio_repo = model_portfolio_repo
        self._stock_repo = stock_repo

    # ---------- ModelPortfolio operasyonları ---------- #

    def get_all_portfolios(self) -> List[ModelPortfolio]:
        """Tüm model portföyleri döner."""
        return self._portfolio_repo.get_all_model_portfolios()

    def get_portfolio_by_id(self, portfolio_id: int) -> Optional[ModelPortfolio]:
        """Belirli bir model portföyü id ile getirir."""
        return self._portfolio_repo.get_model_portfolio_by_id(portfolio_id)

    def create_portfolio(
        self,
        name: str,
        description: Optional[str] = None,
        initial_cash: Decimal = Decimal("100000.00"),
    ) -> ModelPortfolio:
        """
        Yeni bir model portföy oluşturur.
        
        Args:
            name: Portföy adı
            description: Opsiyonel açıklama
            initial_cash: Başlangıç sermayesi (varsayılan 100.000 TL)
            
        Returns:
            Oluşturulan ModelPortfolio objesi
        """
        if not name or not name.strip():
            raise ValueError("Portföy adı boş olamaz")

        if initial_cash <= 0:
            raise ValueError("Başlangıç sermayesi pozitif olmalıdır")

        portfolio = ModelPortfolio(
            id=None,
            name=name.strip(),
            description=description.strip() if description else None,
            initial_cash=initial_cash,
        )
        return self._portfolio_repo.create_model_portfolio(portfolio)

    def update_portfolio(
        self,
        portfolio_id: int,
        name: str,
        description: Optional[str] = None,
        initial_cash: Optional[Decimal] = None,
    ) -> None:
        """
        Var olan bir model portföyü günceller.
        
        Args:
            portfolio_id: Güncellenecek portföy id
            name: Yeni ad
            description: Yeni açıklama
            initial_cash: Yeni başlangıç sermayesi (None ise değişmez)
        """
        if not name or not name.strip():
            raise ValueError("Portföy adı boş olamaz")

        existing = self._portfolio_repo.get_model_portfolio_by_id(portfolio_id)
        if existing is None:
            raise ValueError(f"Portföy bulunamadı: {portfolio_id}")

        updated_portfolio = ModelPortfolio(
            id=portfolio_id,
            name=name.strip(),
            description=description.strip() if description else None,
            initial_cash=initial_cash if initial_cash is not None else existing.initial_cash,
            created_at=existing.created_at,
            updated_at=existing.updated_at,
        )
        self._portfolio_repo.update_model_portfolio(updated_portfolio)

    def delete_portfolio(self, portfolio_id: int) -> None:
        """
        Model portföyü siler. İçindeki tüm trade'ler de silinir (CASCADE).
        
        Args:
            portfolio_id: Silinecek portföy id
        """
        self._portfolio_repo.delete_model_portfolio(portfolio_id)

    # ---------- Trade operasyonları ---------- #

    def get_portfolio_trades(self, portfolio_id: int) -> List[ModelPortfolioTrade]:
        """Portföydeki tüm trade'leri döner."""
        return self._portfolio_repo.get_trades_by_portfolio_id(portfolio_id)

    def add_trade(
        self,
        portfolio_id: int,
        stock_id: int,
        side: str,  # "BUY" veya "SELL"
        quantity: int,
        price: Decimal,
        trade_date: date,
        trade_time: Optional[time] = None,
    ) -> ModelPortfolioTrade:
        """
        Portföye yeni bir trade ekler.
        
        Args:
            portfolio_id: Portföy id
            stock_id: Hisse id
            side: İşlem yönü ("BUY" veya "SELL")
            quantity: Lot sayısı
            price: Birim fiyat
            trade_date: İşlem tarihi
            trade_time: İşlem saati (opsiyonel)
            
        Returns:
            Oluşturulan ModelPortfolioTrade
            
        Raises:
            ValueError: Yetersiz bakiye veya pozisyon varsa
        """
        # Portföy var mı kontrol et
        portfolio = self._portfolio_repo.get_model_portfolio_by_id(portfolio_id)
        if portfolio is None:
            raise ValueError(f"Portföy bulunamadı: {portfolio_id}")

        # Stock var mı kontrol et
        stock = self._stock_repo.get_stock_by_id(stock_id)
        if stock is None:
            raise ValueError(f"Hisse bulunamadı: {stock_id}")

        trade_side = ModelTradeSide(side)
        total_cost = price * Decimal(quantity)

        if trade_side == ModelTradeSide.BUY:
            # Alış için yeterli nakit var mı?
            remaining_cash = self.get_remaining_cash(portfolio_id)
            if total_cost > remaining_cash:
                raise ValueError(
                    f"Yetersiz bakiye. Gerekli: {total_cost:.2f} TL, Mevcut: {remaining_cash:.2f} TL"
                )
            
            trade = ModelPortfolioTrade.create_buy(
                portfolio_id=portfolio_id,
                stock_id=stock_id,
                trade_date=trade_date,
                quantity=quantity,
                price=price,
                trade_time=trade_time,
            )
        else:
            # Satış için yeterli pozisyon var mı?
            positions = self.get_positions(portfolio_id)
            current_qty = positions.get(stock_id, 0)
            if quantity > current_qty:
                raise ValueError(
                    f"Yetersiz pozisyon. Satmak istediğiniz: {quantity}, Mevcut: {current_qty}"
                )
            
            trade = ModelPortfolioTrade.create_sell(
                portfolio_id=portfolio_id,
                stock_id=stock_id,
                trade_date=trade_date,
                quantity=quantity,
                price=price,
                trade_time=trade_time,
            )

        return self._portfolio_repo.insert_trade(trade)

    def add_trade_by_ticker(
        self,
        portfolio_id: int,
        ticker: str,
        side: str,
        quantity: int,
        price: Decimal,
        trade_date: date,
        trade_time: Optional[time] = None,
    ) -> ModelPortfolioTrade:
        """
        Ticker ile trade ekler. Hisse yoksa önce oluşturur.
        """
        if not ticker or not ticker.strip():
            raise ValueError("Ticker boş olamaz")

        ticker = ticker.strip().upper()
        if "." not in ticker:
            ticker = ticker + ".IS"

        # Stock'u bul veya oluştur
        stock = self._stock_repo.get_stock_by_ticker(ticker)
        if stock is None:
            new_stock = Stock(
                id=None,
                ticker=ticker,
                name=ticker,
                currency_code="TRY",
            )
            stock = self._stock_repo.insert_stock(new_stock)

        return self.add_trade(
            portfolio_id=portfolio_id,
            stock_id=stock.id,
            side=side,
            quantity=quantity,
            price=price,
            trade_date=trade_date,
            trade_time=trade_time,
        )

    def delete_trade(self, trade_id: int) -> None:
        """Trade'i siler."""
        self._portfolio_repo.delete_trade(trade_id)

    # ---------- Hesaplama operasyonları ---------- #

    def get_positions(self, portfolio_id: int) -> Dict[int, int]:
        """
        Portföydeki pozisyonları hesaplar.
        
        Returns:
            Dict[stock_id, quantity]: Her hisse için eldeki lot sayısı
        """
        trades = self._portfolio_repo.get_trades_by_portfolio_id(portfolio_id)
        positions: Dict[int, int] = defaultdict(int)

        for trade in trades:
            if trade.side == ModelTradeSide.BUY:
                positions[trade.stock_id] += trade.quantity
            else:
                positions[trade.stock_id] -= trade.quantity

        # Sıfır pozisyonları kaldır
        return {k: v for k, v in positions.items() if v > 0}

    def get_remaining_cash(self, portfolio_id: int) -> Decimal:
        """
        Portföyde kalan nakiti hesaplar.
        
        Returns:
            Kalan nakit tutarı
        """
        portfolio = self._portfolio_repo.get_model_portfolio_by_id(portfolio_id)
        if portfolio is None:
            raise ValueError(f"Portföy bulunamadı: {portfolio_id}")

        trades = self._portfolio_repo.get_trades_by_portfolio_id(portfolio_id)
        
        cash = portfolio.initial_cash
        for trade in trades:
            if trade.side == ModelTradeSide.BUY:
                cash -= trade.total_amount
            else:
                cash += trade.total_amount

        return cash

    def get_portfolio_summary(
        self,
        portfolio_id: int,
        price_map: Optional[Dict[int, Decimal]] = None,
    ) -> Dict[str, Any]:
        """
        Portföy özeti döner.
        
        Args:
            portfolio_id: Portföy id
            price_map: Güncel hisse fiyatları {stock_id: price}
            
        Returns:
            Dict: {
                'initial_cash': Başlangıç sermayesi,
                'remaining_cash': Kalan nakit,
                'positions_value': Pozisyonların toplam değeri,
                'total_value': Toplam portföy değeri,
                'profit_loss': Kar/zarar,
                'profit_loss_pct': Kar/zarar yüzdesi,
            }
        """
        portfolio = self._portfolio_repo.get_model_portfolio_by_id(portfolio_id)
        if portfolio is None:
            raise ValueError(f"Portföy bulunamadı: {portfolio_id}")

        remaining_cash = self.get_remaining_cash(portfolio_id)
        positions = self.get_positions(portfolio_id)

        # Pozisyonların değerini hesapla
        positions_value = Decimal("0")
        if price_map:
            for stock_id, qty in positions.items():
                if stock_id in price_map:
                    positions_value += price_map[stock_id] * Decimal(qty)

        total_value = remaining_cash + positions_value
        profit_loss = total_value - portfolio.initial_cash
        profit_loss_pct = (profit_loss / portfolio.initial_cash * 100) if portfolio.initial_cash > 0 else Decimal("0")

        return {
            "initial_cash": portfolio.initial_cash,
            "remaining_cash": remaining_cash,
            "positions_value": positions_value,
            "total_value": total_value,
            "profit_loss": profit_loss,
            "profit_loss_pct": profit_loss_pct,
        }

    def get_positions_with_details(
        self,
        portfolio_id: int,
        price_map: Optional[Dict[int, Decimal]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Pozisyonları detaylı bilgileriyle döner.
        
        Returns:
            List[Dict]: Her pozisyon için:
                - stock_id, ticker, name
                - quantity: Lot sayısı
                - avg_cost: Ortalama maliyet
                - total_cost: Toplam maliyet
                - current_price: Güncel fiyat (varsa)
                - current_value: Güncel değer (varsa)
                - profit_loss: Kar/zarar (varsa)
        """
        trades = self._portfolio_repo.get_trades_by_portfolio_id(portfolio_id)
        positions = self.get_positions(portfolio_id)

        if not positions:
            return []

        # Stock bilgilerini al
        stock_ids = list(positions.keys())
        stocks = self._stock_repo.get_stocks_by_ids(stock_ids)
        stock_map = {s.id: s for s in stocks}

        # Her hisse için ortalama maliyet hesapla
        cost_data: Dict[int, Dict[str, Any]] = defaultdict(lambda: {"qty": 0, "cost": Decimal("0")})
        
        for trade in trades:
            if trade.side == ModelTradeSide.BUY:
                cost_data[trade.stock_id]["qty"] += trade.quantity
                cost_data[trade.stock_id]["cost"] += trade.total_amount
            else:
                # Satışlarda ortalama maliyet düşer
                if cost_data[trade.stock_id]["qty"] > 0:
                    avg = cost_data[trade.stock_id]["cost"] / Decimal(cost_data[trade.stock_id]["qty"])
                    cost_data[trade.stock_id]["qty"] -= trade.quantity
                    cost_data[trade.stock_id]["cost"] -= avg * Decimal(trade.quantity)

        result = []
        for stock_id, qty in positions.items():
            stock = stock_map.get(stock_id)
            total_cost = cost_data[stock_id]["cost"]
            avg_cost = total_cost / Decimal(qty) if qty > 0 else Decimal("0")

            current_price = price_map.get(stock_id) if price_map else None
            current_value = current_price * Decimal(qty) if current_price else None
            profit_loss = current_value - total_cost if current_value else None

            result.append({
                "stock_id": stock_id,
                "ticker": stock.ticker if stock else "?",
                "name": stock.name if stock else "Bilinmeyen",
                "quantity": qty,
                "avg_cost": avg_cost,
                "total_cost": total_cost,
                "current_price": current_price,
                "current_value": current_value,
                "profit_loss": profit_loss,
            })

        return result

    def get_trade_count(self, portfolio_id: int) -> int:
        """Portföydeki trade sayısını döner."""
        trades = self._portfolio_repo.get_trades_by_portfolio_id(portfolio_id)
        return len(trades)
