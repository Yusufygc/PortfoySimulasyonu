# src/application/services/optimization_service.py

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.optimize import minimize

from src.domain.models.optimization_result import (
    OptimizationMetrics,
    OptimizationResult,
    OptimizationSuggestion,
)


class OptimizationService:
    """
    Markowitz Modern Portföy Teorisi (MPT) tabanlı portföy optimizasyon servisi.

    Mevcut portföy ağırlıklarını analiz eder ve Sharpe Oranını maksimize eden
    optimal ağırlıkları hesaplar. İki farklı kaynak üzerinden çalışır:
        - Dashboard (ana) portföyü
        - Model portföyler

    Bağımlılıklar:
        - portfolio_service: Ana portföy pozisyonları için
        - model_portfolio_service: Model portföy pozisyonları için
        - stock_repo: Hisse ticker bilgisi için
    """

    # BIST için yıllık işlem günü sayısı
    TRADING_DAYS_PER_YEAR = 252

    # Türkiye risksiz faiz oranı (temsili)
    DEFAULT_RISK_FREE_RATE = 0.30

    def __init__(
        self,
        portfolio_service,
        model_portfolio_service,
        stock_repo,
        risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
    ) -> None:
        self._portfolio_service = portfolio_service
        self._model_portfolio_service = model_portfolio_service
        self._stock_repo = stock_repo
        self._risk_free_rate = risk_free_rate

    # ==================== Public API ==================== #

    def optimize_dashboard_portfolio(self) -> OptimizationResult:
        """
        Dashboard (ana) portföyünü optimize eder.

        Returns:
            OptimizationResult: Mevcut ve optimize edilmiş metrikler + öneriler

        Raises:
            ValueError: Portföyde yetersiz hisse varsa
        """
        # Ana portföyün pozisyonlarını al
        portfolio = self._portfolio_service.get_current_portfolio()
        positions = portfolio.positions

        if len(positions) < 2:
            raise ValueError(
                "Optimizasyon için portföyde en az 2 farklı hisse olmalıdır."
            )

        # Ticker bilgilerini al
        stock_ids = list(positions.keys())
        stocks = self._stock_repo.get_stocks_by_ids(stock_ids)
        stock_map = {s.id: s for s in stocks}

        tickers = [stock_map[sid].ticker for sid in stock_ids]

        # Mevcut ağırlıkları hesapla (market value bazlı, anlık fiyat ile)
        current_weights = self._calculate_weights_from_positions(positions, tickers)

        return self._optimize(tickers, current_weights)

    def optimize_model_portfolio(
        self,
        portfolio_id: int,
        price_lookup_func=None,
    ) -> OptimizationResult:
        """
        Seçili model portföyü optimize eder.

        Args:
            portfolio_id: Optimize edilecek model portföy ID'si
            price_lookup_func: Fiyat sorgulama fonksiyonu (MainWindow.lookup_price_for_ticker)

        Returns:
            OptimizationResult

        Raises:
            ValueError: Portföyde yetersiz hisse varsa
        """
        positions = self._model_portfolio_service.get_positions(portfolio_id)

        if len(positions) < 2:
            raise ValueError(
                "Optimizasyon için portföyde en az 2 farklı hisse olmalıdır."
            )

        # Stock bilgilerini al
        stock_ids = list(positions.keys())
        stocks = self._stock_repo.get_stocks_by_ids(stock_ids)
        stock_map = {s.id: s for s in stocks}

        tickers = [stock_map[sid].ticker for sid in stock_ids]
        quantities = [positions[sid] for sid in stock_ids]

        # Mevcut ağırlıkları piyasa değeri bazlı hesapla
        current_weights = self._calculate_weights_with_prices(
            tickers, quantities, price_lookup_func
        )

        return self._optimize(tickers, current_weights)

    def get_model_portfolios(self) -> list:
        """Model portföy listesini döner."""
        return self._model_portfolio_service.get_all_portfolios()

    # ==================== Optimizasyon Motoru ==================== #

    def _optimize(
        self,
        tickers: List[str],
        current_weights: np.ndarray,
    ) -> OptimizationResult:
        """
        Markowitz MPT optimizasyon motorunu çalıştırır.
        """
        # 1. Geçmiş fiyat verisi
        price_df = self._get_historical_prices(tickers, days=365)
        if price_df.empty or len(price_df) < 30:
            raise ValueError("Yeterli fiyat geçmişi bulunamadı (en az 30 gün gerekli).")

        # 2. Logaritmik getiriler
        log_returns = np.log(price_df / price_df.shift(1)).dropna()

        # 3. Yıllıklandırılmış ortalama getiri ve kovaryans matrisi
        mean_returns = log_returns.mean() * self.TRADING_DAYS_PER_YEAR
        cov_matrix = log_returns.cov() * self.TRADING_DAYS_PER_YEAR

        num_assets = len(tickers)

        # 4. Optimizasyon
        initial_weights = np.array([1.0 / num_assets] * num_assets)

        constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1}
        bounds = tuple((0.0, 1.0) for _ in range(num_assets))

        result = minimize(
            self._negative_sharpe_ratio,
            initial_weights,
            args=(mean_returns.values, cov_matrix.values, self._risk_free_rate),
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        if not result.success:
            raise ValueError("Optimizasyon hesaplanamadı. Lütfen tekrar deneyin.")

        optimal_weights = result.x

        # 5. Metrikleri hesapla
        current_metrics = self._calculate_metrics(
            current_weights, mean_returns.values, cov_matrix.values
        )
        optimized_metrics = self._calculate_metrics(
            optimal_weights, mean_returns.values, cov_matrix.values
        )

        # 6. Hisse bazlı öneriler
        suggestions = self._build_suggestions(tickers, current_weights, optimal_weights)

        return OptimizationResult(
            current_metrics=current_metrics,
            optimized_metrics=optimized_metrics,
            suggestions=suggestions,
        )

    # ==================== Yardımcı Metodlar ==================== #

    @staticmethod
    def _negative_sharpe_ratio(
        weights: np.ndarray,
        mean_returns: np.ndarray,
        cov_matrix: np.ndarray,
        risk_free_rate: float,
    ) -> float:
        """
        Negatif Sharpe oranı (minimizasyon fonksiyonu).
        Sharpe = (Beklenen Getiri - Risksiz Faiz) / Volatilite
        """
        portfolio_return = np.sum(mean_returns * weights)
        portfolio_volatility = np.sqrt(weights.T @ cov_matrix @ weights)
        return -(portfolio_return - risk_free_rate) / portfolio_volatility

    def _calculate_metrics(
        self,
        weights: np.ndarray,
        mean_returns: np.ndarray,
        cov_matrix: np.ndarray,
    ) -> OptimizationMetrics:
        """Verilen ağırlıklar için metrik hesaplar."""
        portfolio_return = float(np.sum(mean_returns * weights))
        portfolio_volatility = float(np.sqrt(weights.T @ cov_matrix @ weights))
        sharpe = (portfolio_return - self._risk_free_rate) / portfolio_volatility

        return OptimizationMetrics(
            expected_return=portfolio_return,
            volatility=portfolio_volatility,
            sharpe_ratio=float(sharpe),
        )

    @staticmethod
    def _build_suggestions(
        tickers: List[str],
        current_weights: np.ndarray,
        optimal_weights: np.ndarray,
    ) -> List[OptimizationSuggestion]:
        """Hisse bazlı öneri listesi oluşturur."""
        suggestions = []

        for i, ticker in enumerate(tickers):
            curr_w = current_weights[i] * 100
            opt_w = optimal_weights[i] * 100
            diff = opt_w - curr_w

            if diff > 1.0:
                action = "EKLE"
            elif diff < -1.0:
                action = "AZALT"
            else:
                action = "TUT"

            suggestions.append(
                OptimizationSuggestion(
                    symbol=ticker,
                    current_weight=curr_w,
                    optimal_weight=opt_w,
                    change=diff,
                    action=action,
                )
            )

        # Optimal ağırlığa göre büyükten küçüğe sırala
        suggestions.sort(key=lambda s: s.optimal_weight, reverse=True)
        return suggestions

    def _get_historical_prices(self, tickers: List[str], days: int = 365) -> pd.DataFrame:
        """
        yfinance üzerinden son N günlük kapanış fiyat verisi çeker.

        Args:
            tickers: Hisse sembolü listesi
            days: Geriye dönük gün sayısı

        Returns:
            pd.DataFrame: Tarih indeksli, her hisse için kapanış fiyatı sütunları
        """
        try:
            df = yf.download(
                tickers=tickers,
                period=f"{days}d",
                interval="1d",
                progress=False,
                auto_adjust=False,
                timeout=15,
            )
        except Exception as exc:
            raise ValueError(f"Fiyat verisi çekilemedi: {exc}") from exc

        if df.empty:
            return pd.DataFrame()

        # Tek ticker: düz Index; çoklu: MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            close_df = df["Close"]
        else:
            close_df = df[["Close"]].rename(columns={"Close": tickers[0]})

        return close_df.dropna()

    def _calculate_weights_from_positions(
        self,
        positions: dict,
        tickers: List[str],
    ) -> np.ndarray:
        """
        Ana portföy pozisyonlarının piyasa değeri bazlı ağırlıklarını hesaplar.
        Anlık fiyat yoksa ortalama maliyeti kullanır.
        """
        values = []
        for ticker, (stock_id, position) in zip(tickers, positions.items()):
            price = self._get_last_price(ticker)
            if price is None and position.average_cost is not None:
                price = float(position.average_cost)
            elif price is None:
                price = 1.0
            values.append(position.total_quantity * price)

        total = sum(values)
        if total == 0:
            n = len(values)
            return np.array([1.0 / n] * n)

        return np.array([v / total for v in values])

    def _calculate_weights_with_prices(
        self,
        tickers: List[str],
        quantities: List[int],
        price_lookup_func=None,
    ) -> np.ndarray:
        """
        Model portföy pozisyonlarının fiyat bazlı ağırlıklarını hesaplar.
        """
        values = []
        for ticker, qty in zip(tickers, quantities):
            price = None
            if price_lookup_func:
                try:
                    result = price_lookup_func(ticker)
                    if result:
                        price = float(result.price)
                except Exception:
                    pass

            if price is None:
                price = self._get_last_price(ticker) or 1.0

            values.append(qty * price)

        total = sum(values)
        if total == 0:
            n = len(values)
            return np.array([1.0 / n] * n)

        return np.array([v / total for v in values])

    @staticmethod
    def _get_last_price(ticker: str) -> Optional[float]:
        """yfinance üzerinden son kapanış fiyatını hızlıca alır."""
        try:
            yt = yf.Ticker(ticker)
            info = getattr(yt, "fast_info", None) or yt.info
            if isinstance(info, dict):
                for key in ("lastPrice", "last_price", "regularMarketPrice", "currentPrice"):
                    val = info.get(key)
                    if val is not None:
                        return float(val)

            hist = yt.history(period="5d", auto_adjust=False)
            if hist is not None and not hist.empty and "Close" in hist:
                close_series = hist["Close"].dropna()
                if not close_series.empty:
                    return float(close_series.iloc[-1])
        except Exception:
            pass
        return None
