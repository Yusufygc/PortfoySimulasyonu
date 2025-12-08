# src/application/services/return_calc_service.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Optional, Tuple

from src.domain.models.portfolio import Portfolio
from src.domain.services_interfaces.i_portfolio_repo import IPortfolioRepository
from src.domain.services_interfaces.i_price_repo import IPriceRepository


@dataclass
class PortfolioValueSnapshot:
    """
    Belirli bir tarihte portföyün durumunun özeti.
    UI tarafına göndermek için elverişli bir DTO.
    """
    as_of_date: date
    total_cost: Decimal
    total_value: Decimal
    total_unrealized_pl: Decimal
    total_realized_pl: Decimal
    price_map: Dict[int, Decimal]  # { stock_id: close_price }


class ReturnCalcService:
    """
    Portföyün toplam değerini ve getiri oranlarını hesaplayan application servisi.

    Bu servis:
      - IPortfolioRepository üzerinden trade'leri çeker, Portfolio domain'ini oluşturur
      - IPriceRepository üzerinden fiyatları çeker
      - Toplam değer, kar/zarar, haftalık/aylık getiri oranlarını hesaplar
    """

    def __init__(
        self,
        portfolio_repo: IPortfolioRepository,
        price_repo: IPriceRepository,
    ) -> None:
        self._portfolio_repo = portfolio_repo
        self._price_repo = price_repo

    # ---------- Yardımcı: Belirli tarihte portföy değeri ---------- #

    def compute_portfolio_value_on(self, value_date: date) -> PortfolioValueSnapshot:
        """
        Belirtilen tarihte portföyün değerini hesaplar.

        Adımlar:
          1) Tüm trade'leri repo'dan çek
          2) Portfolio.from_trades(...) ile domain portföyünü oluştur
          3) value_date için fiyat map'ini repo'dan al
          4) Portfolio metodları ile toplam değer ve P&L hesaplarını yap
        """
        # 1) Tüm trade'ler
        trades = self._portfolio_repo.get_all_trades()
        portfolio = Portfolio.from_trades(trades)

        # 2) Fiyatlar
        price_map = self._price_repo.get_prices_for_date(value_date)
        # price_map: { stock_id: Decimal(close_price) }

        # 3) Toplam değerler
        total_cost = portfolio.total_cost()
        total_value = portfolio.total_market_value(price_map)
        total_unrealized = portfolio.total_unrealized_pl(price_map)
        total_realized = portfolio.total_realized_pl()

        return PortfolioValueSnapshot(
            as_of_date=value_date,
            total_cost=total_cost,
            total_value=total_value,
            total_unrealized_pl=total_unrealized,
            total_realized_pl=total_realized,
            price_map=price_map,
        )

    # ---------- Yardımcı: Basit getiri oranı ---------- #

    def _compute_return_rate(
        self,
        start_value: Decimal,
        end_value: Decimal,
    ) -> Optional[Decimal]:
        """
        Basit getiri oranını hesaplar:
            (end_value - start_value) / start_value

        start_value = 0 ise None döner (tanımsız).
        """
        if start_value == 0:
            return None
        return (end_value - start_value) / start_value

    # ---------- İki tarih arası portföy getirisi ---------- #

    def compute_return_between(
        self,
        start_date: date,
        end_date: date,
    ) -> Tuple[Optional[Decimal], PortfolioValueSnapshot, PortfolioValueSnapshot]:
        """
        İki tarih arasındaki portföy getirisini hesaplar.

        Dönüş:
          (return_rate, start_snapshot, end_snapshot)

        return_rate:
          - None: başlangıç değeri 0 ise (ör: hiç pozisyon yok)
          - Decimal: örneğin 0.12 = %12 getiri
        """
        if start_date > end_date:
            raise ValueError("start_date end_date'ten büyük olamaz.")

        start_snapshot = self.compute_portfolio_value_on(start_date)
        end_snapshot = self.compute_portfolio_value_on(end_date)

        rate = self._compute_return_rate(
            start_value=start_snapshot.total_value,
            end_value=end_snapshot.total_value,
        )

        return rate, start_snapshot, end_snapshot

    # ---------- Haftalık getiri ---------- #

    def compute_weekly_return(
        self,
        end_date: date,
    ) -> Tuple[Optional[Decimal], PortfolioValueSnapshot, PortfolioValueSnapshot]:
        """
        Haftalık getiri:
          - end_date dahil,
          - start_date = end_date - 7 gün varsayıyoruz (yaklaşık son 1 hafta).
        """
        start_date = end_date - timedelta(days=7)
        return self.compute_return_between(start_date, end_date)

    # ---------- Aylık getiri ---------- #

    def compute_monthly_return(
        self,
        end_date: date,
        days: int = 30,
    ) -> Tuple[Optional[Decimal], PortfolioValueSnapshot, PortfolioValueSnapshot]:
        """
        Aylık getiri:
          - end_date dahil,
          - varsayılan olarak son 30 gün (days parametresiyle oynanabilir).
        """
        start_date = end_date - timedelta(days=days)
        return self.compute_return_between(start_date, end_date)
