import pytest
import pandas as pd
import numpy as np
from src.application.services.analysis.comparison_service import ComparisonService

def test_align_financial_series():
    # Arrange
    idx_a = pd.date_range("2026-01-01", periods=3, freq="D")
    idx_b = pd.date_range("2026-01-02", periods=3, freq="D")
    
    series_a = pd.Series([10.0, 11.0, 12.0], index=idx_a)
    series_b = pd.Series([20.0, 21.0, 22.0], index=idx_b)
    
    # Act
    aligned = ComparisonService.align_financial_series({"var_a": series_a, "var_b": series_b})
    
    # Assert
    assert aligned.shape == (4, 2)
    # Check forward fill and backward fill
    assert aligned.loc["2026-01-01", "var_b"] == 20.0  # bfill
    assert aligned.loc["2026-01-04", "var_a"] == 12.0  # ffill
    assert aligned.loc["2026-01-03", "var_b"] == 21.0

def test_calculate_asset_ratio():
    # Arrange
    dates = pd.date_range("2026-01-01", periods=3)
    series_a = pd.Series([100.0, 120.0, 150.0], index=dates)
    series_b = pd.Series([50.0, 0.0, 75.0], index=dates)
    
    # Act
    ratio = ComparisonService.calculate_asset_ratio(series_a, series_b)
    
    # Assert
    assert ratio.iloc[0] == 2.0  # 100 / 50
    assert np.isnan(ratio.iloc[1])  # 120 / 0 should be NaN or inf (handled as NaN)
    assert ratio.iloc[2] == 2.0  # 150 / 75

def test_calculate_drawdowns():
    # Arrange
    dates = pd.date_range("2026-01-01", periods=4)
    df = pd.DataFrame({
        "var": [100.0, 120.0, 90.0, 150.0]
    }, index=dates)
    
    # Act
    dd = ComparisonService.calculate_drawdowns(df)
    
    # Assert
    assert dd.loc["2026-01-01", "var"] == 0.0
    assert dd.loc["2026-01-02", "var"] == 0.0
    assert dd.loc["2026-01-03", "var"] == -25.0  # (90 - 120) / 120 * 100
    assert dd.loc["2026-01-04", "var"] == 0.0    # New peak

def test_calculate_risk_return_metrics():
    # Arrange
    dates = pd.date_range("2026-01-01", periods=3)
    df = pd.DataFrame({
        "var": [10.0, 10.5, 11.0]
    }, index=dates)
    
    # Act
    metrics = ComparisonService.calculate_risk_return_metrics(df)
    
    # Assert
    assert "var" in metrics
    assert metrics["var"]["total_return_pct"] == pytest.approx(10.0) # (11 - 10) / 10 * 100
    assert metrics["var"]["annual_volatility_pct"] > 0.0

def test_calculate_periodic_returns():
    # Arrange
    dates = pd.date_range("2026-01-01", periods=60, freq="D")
    df = pd.DataFrame({
        "var": [100.0 + i for i in range(60)]
    }, index=dates)
    
    # Act
    periodic = ComparisonService.calculate_periodic_returns(df, freq="ME")
    
    # Assert
    assert len(periodic) >= 1
    assert periodic.columns == ["var"]
