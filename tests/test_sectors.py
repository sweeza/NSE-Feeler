"""
Unit tests for Sector Rotation & Participation analytics module.
"""

import numpy as np
import pandas as pd

import market_breadth.sectors as sectors_mod
from market_breadth.sectors import (
    OFFICIAL_SECTORS,
    compute_all_sectors_summary,
    compute_sector_timeseries,
)


def test_official_sectors_list():
    assert len(OFFICIAL_SECTORS) > 0
    nifty50 = next((s for s in OFFICIAL_SECTORS if s["key"] == "nifty50"), None)
    assert nifty50 is not None
    assert nifty50["name"] == "Nifty 50"


def test_sector_computation_with_mock_tensor(monkeypatch):
    """Test sector computation and summary with mock tensor data to ensure offline robustness."""
    dates = pd.date_range("2023-01-01", periods=100, freq="B")
    tickers = ["STOCK_1", "STOCK_2", "STOCK_3"]
    np.random.seed(42)
    mock_close = pd.DataFrame(np.random.normal(100, 5, size=(100, 3)).cumsum(axis=0) + 100, index=dates, columns=tickers)
    mock_prev = mock_close.shift(1).bfill()

    def mock_load(name, universe="master", adjusted=True, forward_fill=False, start=None, end=None):
        if name == "close":
            return mock_close
        elif name == "prevclose":
            return mock_prev
        return pd.DataFrame()

    if sectors_mod.nseuniverse is not None:
        monkeypatch.setattr(sectors_mod.nseuniverse, "load", mock_load)

    # Clear sector cache for test
    sectors_mod._SECTOR_CACHE.clear()

    res = compute_sector_timeseries("nifty50", start="2023-01-01", end="2023-03-31")
    assert res is not None
    assert "cap_close" in res
    assert "eq_close" in res
    assert "returns_summary" in res
    assert "1W (5D)" in res["returns_summary"]
    assert "pct_above_20" in res
    assert "pct_above_50" in res
    assert "pct_above_200" in res
    assert "ad_ratio_pct" in res

    summary = compute_all_sectors_summary(start="2023-01-01", end="2023-01-31")
    assert isinstance(summary, pd.DataFrame)
    if not summary.empty:
        expected_cols = [
            "Sector", "Type",
            "1D Cap (%)", "1D EW (%)", "1D Spread (%)",
            "1W Cap (%)", "1W EW (%)", "1W Spread (%)",
            "1M Cap (%)", "1M EW (%)", "1M Spread (%)",
            "3M Cap (%)", "3M EW (%)", "3M Spread (%)",
            "6M Cap (%)", "6M EW (%)", "6M Spread (%)",
            "1Y Cap (%)", "1Y EW (%)", "1Y Spread (%)",
            "Breadth (% > 20 DMA)", "Breadth (% > 50 DMA)", "Breadth (% > 200 DMA)",
            "A/D Ratio (%)", "EW/MCAP Ratio"
        ]
        for col in expected_cols:
            assert col in summary.columns, f"Missing required column in sectors summary: {col}"
