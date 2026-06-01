import pytest
import pandas as pd
import plotly.graph_objects as go
from src.ui.pages.comparison.chart_factory import ComparisonChartFactory

def test_build_summary_table():
    # Arrange
    df = pd.DataFrame({
        "Varlık Adı": ["Portföy", "Altın"],
        "Başlangıç Değeri": [100.0, 100.0],
        "Dönem Sonu Değeri": [150.0, 90.0],
        "Toplam Getiri %": [50.0, -10.0]
    })
    
    # Act
    fig = ComparisonChartFactory.build_summary_table(df)
    
    # Assert
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert isinstance(fig.data[0], go.Table)

def test_build_drawdown_chart():
    # Arrange
    dates = pd.date_range("2026-01-01", periods=3)
    df = pd.DataFrame({
        "Portföy": [0.0, -5.0, -2.0]
    }, index=dates)
    
    # Act
    fig = ComparisonChartFactory.build_drawdown_chart(df)
    
    # Assert
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert fig.data[0].fill == "tozeroy"

def test_build_period_bar_chart():
    # Arrange
    dates = pd.date_range("2026-01-01", periods=2, freq="MS")
    df = pd.DataFrame({
        "Portföy": [5.0, 8.0]
    }, index=dates)
    
    # Act
    fig = ComparisonChartFactory.build_period_bar_chart(df)
    
    # Assert
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert fig.layout.barmode == "group"

def test_build_risk_return_scatter():
    # Arrange
    df = pd.DataFrame({
        "Volatilite %": [15.0, 20.0],
        "Getiri %": [25.0, -5.0]
    }, index=["Portföy", "BIST100"])
    
    # Act
    fig = ComparisonChartFactory.build_risk_return_scatter(df)
    
    # Assert
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2

def test_build_treemap():
    # Arrange
    df = pd.DataFrame({
        "Varlık Ağırlığı %": [60.0, 40.0],
        "Getiri %": [12.0, -2.5]
    }, index=["Hisse A", "Hisse B"])
    
    # Act
    fig = ComparisonChartFactory.build_treemap(df)
    
    # Assert
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert isinstance(fig.data[0], go.Treemap)
