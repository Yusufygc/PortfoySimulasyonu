# src/domain/services_interfaces/i_model_portfolio_repo.py

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.models.model_portfolio import ModelPortfolio, ModelPortfolioTrade


class IModelPortfolioRepository(ABC):
    """
    'model_portfolios' ve 'model_portfolio_trades' tablolarına erişim için soyut arayüz.
    """

    # ---------- ModelPortfolio READ operasyonları ---------- #

    @abstractmethod
    def get_all_model_portfolios(self) -> List[ModelPortfolio]:
        """Tüm model portföy kayıtlarını döner."""
        raise NotImplementedError

    @abstractmethod
    def get_model_portfolio_by_id(self, portfolio_id: int) -> Optional[ModelPortfolio]:
        """Tek bir model portföyü id üzerinden döner. Bulunamazsa None."""
        raise NotImplementedError

    # ---------- ModelPortfolio WRITE operasyonları ---------- #

    @abstractmethod
    def create_model_portfolio(self, portfolio: ModelPortfolio) -> ModelPortfolio:
        """
        Yeni bir model portföy oluşturur.
        Dönüş: DB'nin atadığı id ile birlikte ModelPortfolio objesi.
        """
        raise NotImplementedError

    @abstractmethod
    def update_model_portfolio(self, portfolio: ModelPortfolio) -> None:
        """Var olan bir model portföy kaydını günceller."""
        raise NotImplementedError

    @abstractmethod
    def delete_model_portfolio(self, portfolio_id: int) -> None:
        """
        Model portföyü siler.
        Not: CASCADE ayarı nedeniyle içindeki trade'ler de silinir.
        """
        raise NotImplementedError

    # ---------- ModelPortfolioTrade READ operasyonları ---------- #

    @abstractmethod
    def get_trades_by_portfolio_id(self, portfolio_id: int) -> List[ModelPortfolioTrade]:
        """Belirli bir model portföye ait tüm trade'leri döner."""
        raise NotImplementedError

    @abstractmethod
    def get_trade_by_id(self, trade_id: int) -> Optional[ModelPortfolioTrade]:
        """Tek bir trade'i id üzerinden döner. Bulunamazsa None."""
        raise NotImplementedError

    # ---------- ModelPortfolioTrade WRITE operasyonları ---------- #

    @abstractmethod
    def insert_trade(self, trade: ModelPortfolioTrade) -> ModelPortfolioTrade:
        """
        Model portföye yeni bir trade ekler.
        Dönüş: DB'nin atadığı id ile birlikte ModelPortfolioTrade objesi.
        """
        raise NotImplementedError

    @abstractmethod
    def delete_trade(self, trade_id: int) -> None:
        """Model portföyden bir trade'i siler."""
        raise NotImplementedError

    @abstractmethod
    def delete_all_trades_by_portfolio_id(self, portfolio_id: int) -> None:
        """Belirli bir portföye ait tüm trade'leri siler."""
        raise NotImplementedError
