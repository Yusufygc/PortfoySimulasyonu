# src/application/services/portfolio_service.py

from __future__ import annotations

from typing import Dict, List,Tuple
from datetime import date
from decimal import Decimal

from src.domain.models.trade import Trade
from src.domain.models.portfolio import Portfolio
from src.domain.models.position import Position
from src.domain.services_interfaces.i_portfolio_repo import IPortfolioRepository
from src.domain.services_interfaces.i_price_repo import IPriceRepository


class PortfolioService:
    """
    Portföy ile ilgili temel işlemleri yöneten application servisi.

    - Tüm trade'leri çekip Portfolio domain nesnesi oluşturur
    - Yeni trade ekler (alış/satış)
    - İstenirse belirli tarihteki fiyatlarla birlikte portföyü döner
    """

    def __init__(
        self,
        portfolio_repo: IPortfolioRepository,
        price_repo: IPriceRepository,
    ) -> None:
        self._portfolio_repo = portfolio_repo
        self._price_repo = price_repo

    # --------- Portföy görüntüleme --------- #

    def get_current_portfolio(self) -> Portfolio:
        """
        DB'deki tüm trade'leri okuyup portföyü oluşturur.
        """
        trades: List[Trade] = self._portfolio_repo.get_all_trades()
        return Portfolio.from_trades(trades)

    def get_portfolio_with_prices_for_date(
        self,
        value_date: date,
    ) -> Tuple[Portfolio, Dict[int, Decimal]]:
        """
        Verilen tarihteki fiyatlarla birlikte portföyü döner.
        """
        portfolio = self.get_current_portfolio()
        price_map = self._price_repo.get_prices_for_date(value_date)
        return portfolio, price_map

    # --------- Trade ekleme --------- #

    def add_trade(self, trade: Trade) -> Trade:
        """
        Yeni bir işlem (alış/satış) ekler.

        - Mevcut trade'lerden portföyü kurar
        - Yeni trade'i bu portföye uygular (VALIDASYON)
        - Eğer geçerliyse DB'ye yazar
        """

        # Mevcut portföyü oluştur
        trades: List[Trade] = self._portfolio_repo.get_all_trades()
        portfolio = Portfolio.from_trades(trades)

        # Domain kuralı: elindeki lottan fazla satamazsın vb.
        try:
            portfolio.apply_trade(trade)
        except ValueError as e:
            # Bu noktada trade HİÇBİR YERE yazılmadı
            # UI tarafı bu hatayı yakalayıp kullanıcıya mesaj gösterecek
            raise

        # Buraya gelebildiysek trade domain açısından geçerli demektir
        saved_trade = self._portfolio_repo.insert_trade(trade)
        return saved_trade


