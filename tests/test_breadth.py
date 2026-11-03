"""
Unit tests for Market Breadth Engine, Indicators, Sector Rotation module, and app figure builders.
"""

import numpy as np
import pandas as pd

from app import (
    create_ad_figure,
    create_cockpit_figure,
    create_dma_figure,
    create_sector_quadrant_figure,
    create_volume_figure,
    render_tab_content,
    update_sector_drilldown,
)
from market_breadth import (
    OFFICIAL_SECTORS,
    MarketBreadthEngine,
    compute_all_sectors_summary,
)


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


def test_sectors_module(monkeypatch):
    """Test official sectors and computation functions with mock data."""
    assert len(OFFICIAL_SECTORS) > 0
    dates = pd.date_range("2023-01-01", periods=50, freq="B")
    tickers = ["STOCK_1", "STOCK_2"]
    mock_close = pd.DataFrame(
        np.column_stack([np.linspace(100, 110, 50), np.linspace(200, 220, 50)]),
        index=dates,
        columns=tickers
    )
    mock_prev = mock_close.shift(1).bfill()

    import market_breadth.sectors as sectors_mod
    def mock_load(name, universe="master", adjusted=True, forward_fill=False, start=None, end=None):
        if name == "close":
            return mock_close
        elif name == "prevclose":
            return mock_prev
        return pd.DataFrame()

    if sectors_mod.nseuniverse is not None:
        monkeypatch.setattr(sectors_mod.nseuniverse, "load", mock_load)

    sectors_mod._SECTOR_CACHE.clear()
    summary = compute_all_sectors_summary(start="2023-01-01", end="2023-01-31")
    assert isinstance(summary, pd.DataFrame)
    if not summary.empty:
        assert "Sector" in summary.columns
        assert "1D Cap (%)" in summary.columns
        assert "1D Spread (%)" in summary.columns
        assert "1M Cap (%)" in summary.columns
        assert "1M Spread (%)" in summary.columns
        assert "Breadth (% > 50 DMA)" in summary.columns



def test_app_figure_builders_and_callbacks():
    """Verify all figure builders and app callback renderers execute successfully without TypeErrors."""
    dates = pd.date_range("2023-01-01", periods=50, freq="B")
    mock_df = pd.DataFrame(index=dates)
    mock_df["cap_weighted_close"] = np.linspace(100, 110, 50)
    mock_df["equal_weighted_close"] = np.linspace(100, 112, 50)
    mock_df["eq_cap_roc20_spread"] = np.random.normal(0, 1, 50)
    mock_df["cumulative_ad_ratio"] = np.linspace(0, 5, 50)
    mock_df["mcclellan_oscillator_ratio"] = np.random.normal(0, 10, 50)
    mock_df["mcclellan_summation_ratio"] = np.linspace(100, 200, 50)
    mock_df["pct_above_sma_20"] = np.linspace(40, 70, 50)
    mock_df["pct_above_sma_50"] = np.linspace(45, 65, 50)
    mock_df["pct_above_sma_200"] = np.linspace(50, 60, 50)
    mock_df["net_new_highs"] = np.random.randint(-10, 20, 50)
    mock_df["high_low_logic_index"] = np.linspace(0.1, 0.5, 50)
    mock_df["up_down_volume_ratio"] = np.linspace(0.8, 1.5, 50)
    mock_df["trin"] = np.linspace(0.7, 1.3, 50)
    mock_df["zweig_thrust_ema10"] = np.linspace(0.4, 0.7, 50)

    fig1 = create_cockpit_figure(mock_df)
    assert fig1 is not None

    fig2 = create_ad_figure(mock_df)
    assert fig2 is not None

    fig3 = create_dma_figure(mock_df)
    assert fig3 is not None

    fig4 = create_volume_figure(mock_df)
    assert fig4 is not None

    mock_summary = pd.DataFrame({
        "Sector": ["Nifty Bank", "Nifty IT"],
        "1M Cap (%)": [5.2, -2.1],
        "1M Spread (%)": [1.5, -0.8],
        "Breadth (% > 50 DMA)": [75.0, 45.0]
    })
    fig5 = create_sector_quadrant_figure(mock_summary)
    assert fig5 is not None

    fig_drill = update_sector_drilldown("nifty50")
    assert fig_drill is not None

    tab_render = render_tab_content("tab-sectors")
    assert tab_render is not None
