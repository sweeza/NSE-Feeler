"""
Unit tests for Market Breadth Engine, Indicators, and Sector Rotation module.
"""

import numpy as np
import pandas as pd
import pytest

from market_breadth import MarketBreadthEngine
from market_breadth.sector_rotation import SectorRotationEngine, compute_sector_returns


def test_breadth_engine_initialization():
    engine = MarketBreadthEngine(universe="nifty500")
    assert engine.universe == "nifty500"


def test_breadth_computation_mock_data():
    """Test breadth indicators calculation with small synthetic mock data."""
    dates = pd.date_range("2023-01-01", periods=100, freq="B")
    tickers = [f"STOCK_{i}" for i in range(10)]
    
    np.random.seed(42)
    random_walk = np.random.normal(0, 1, size=(100, 10)).cumsum(axis=0) + 100
    close_df = pd.DataFrame(random_walk, index=dates, columns=tickers)
    prev_close_df = close_df.shift(1).bfill()
    volume_df = pd.DataFrame(np.random.randint(1000, 50000, size=(100, 10)), index=dates, columns=tickers)
    
    engine = MarketBreadthEngine(universe="nifty500")
    engine.close_df = close_df
    engine.prevclose_df = prev_close_df
    engine.volume_df = volume_df
    engine.index_obj = None
    
    report = engine.compute_breadth_report()
    
    assert isinstance(report, pd.DataFrame)
    assert len(report) == 100
    
    expected_cols = [
        "advancers", "decliners", "net_advances", "ad_line",
        "ad_ratio", "cumulative_ad_ratio",
        "mcclellan_oscillator", "mcclellan_summation",
        "mcclellan_oscillator_ratio", "mcclellan_summation_ratio",
        "pct_above_sma_20", "pct_above_sma_50", "pct_above_sma_200",
        "new_highs", "new_lows", "net_new_highs", "high_low_logic_index",
        "hindenburg_omen_raw", "hindenburg_omen",
        "up_volume", "down_volume", "up_down_volume_ratio", "trin",
        "up_volume_9_1", "down_volume_9_1",
        "zweig_thrust_ema10", "zweig_thrust_signal",
        "whaley_issues_thrust", "whaley_volume_thrust"
    ]
    
    for col in expected_cols:
        assert col in report.columns, f"Missing expected column: {col}"


def test_sector_rotation_engine():
    """Test sector rotation return calculations and engine execution."""
    dates = pd.date_range("2023-01-01", periods=300, freq="B")
    prices = pd.Series(np.linspace(100, 150, 300) + np.random.normal(0, 1, 300).cumsum(), index=dates)
    
    rets = compute_sector_returns(prices)
    assert isinstance(rets, dict)
    assert "1D" in rets
    assert "1M (21D)" in rets
    assert "1Y (252D)" in rets

    sector_eng = SectorRotationEngine(universe="nifty500")
    assert sector_eng.universe == "nifty500"
