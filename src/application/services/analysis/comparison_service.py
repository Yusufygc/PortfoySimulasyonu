import pandas as pd
import numpy as np
from typing import Dict, List, Union

class ComparisonService:
    @staticmethod
    def align_financial_series(series_dict: Dict[str, pd.Series]) -> pd.DataFrame:
        """
        Farklı tatil günlerine sahip varlıkları ortak bir tarih indeksinde birleştirir.
        Boşluklar forward-fill, başlangıçtaki boşluklar backward-fill ile doldurulur.
        """
        if not series_dict:
            return pd.DataFrame()
        
        # Concat and outer join
        df = pd.concat(series_dict, axis=1, join='outer')
        df = df.ffill().bfill()
        return df

    @staticmethod
    def calculate_asset_ratio(series_a: pd.Series, series_b: pd.Series) -> pd.Series:
        """
        İki serinin rasyosunu hesaplar: series_a / series_b.
        Sıfıra bölünme veya geçersiz/sonsuz durumlar NaN yapılır ve temizlenir.
        """
        # Align first
        df = pd.concat({"a": series_a, "b": series_b}, axis=1, join="outer").ffill().bfill()
        
        # Division
        with np.errstate(divide='ignore', invalid='ignore'):
            ratio = df["a"] / df["b"]
            
        ratio = ratio.replace([np.inf, -np.inf], np.nan)
        return ratio

    @staticmethod
    def calculate_drawdowns(df: pd.DataFrame) -> pd.DataFrame:
        """
        Her bir varlık (kolon) için tepe noktasından yüzde düşüşü (drawdown) hesaplar.
        """
        if df.empty:
            return pd.DataFrame(index=df.index)
            
        cum_max = df.cummax()
        with np.errstate(divide='ignore', invalid='ignore'):
            drawdown = (df - cum_max) / cum_max * 100.0
            
        # Drawdowns are always <= 0
        drawdown = drawdown.clip(upper=0.0)
        return drawdown

    @staticmethod
    def calculate_risk_return_metrics(df: pd.DataFrame, period: str = None) -> Dict[str, Dict[str, float]]:
        """
        Her bir varlık (kolon) için yıllıklandırılmış volatilite (%) ve toplam dönem getirisini (%) hesaplar.
        """
        metrics = {}
        for col in df.columns:
            series = df[col].dropna()
            if len(series) < 2:
                metrics[col] = {"annual_volatility_pct": 0.0, "total_return_pct": 0.0}
                continue
                
            # Returns
            daily_returns = series.pct_change().dropna()
            
            # Annualized Volatility
            if len(daily_returns) >= 2:
                vol = daily_returns.std() * np.sqrt(252) * 100.0
            else:
                vol = 0.0
                
            # Total Period Return
            start_val = series.iloc[0]
            end_val = series.iloc[-1]
            total_ret = 0.0
            if start_val != 0:
                total_ret = ((end_val - start_val) / start_val) * 100.0
                
            metrics[col] = {
                "annual_volatility_pct": float(vol) if not np.isnan(vol) else 0.0,
                "total_return_pct": float(total_ret) if not np.isnan(total_ret) else 0.0
            }
        return metrics

    @staticmethod
    def calculate_periodic_returns(df: pd.DataFrame, freq: str = "ME") -> pd.DataFrame:
        """
        Verilen frekansta (örn. 'ME' aylık, 'YE' yıllık) periyodik net getiri yüzdelerini hesaplar.
        """
        if df.empty:
            return pd.DataFrame()
            
        # Resample to get period-end values
        period_ends = df.resample(freq).last()
        
        # Calculate returns
        periodic_ret = period_ends.pct_change().dropna() * 100.0
        return periodic_ret
