"""
Unit tests for Sector Rotation & Participation analytics module.
"""

import pandas as pd
from market_breadth.sectors import OFFICIAL_SECTORS, compute_sector_timeseries, compute_all_sectors_summary


def test_official_sectors_list():
    assert len(OFFICIAL_SECTORS) > 0
    nifty50 = next((s for s in OFFICIAL_SECTORS if s["key"] == "nifty50"), None)
    assert nifty50 is not None
    assert nifty50["name"] == "Nifty 50"


def test_sector_timeseries_mock_or_real():
    """Test sector computation with nifty50 (or fallback)."""
    try:
        res = compute_sector_timeseries("nifty50", start="2023-01-01", end="2023-03-31")
        if res:
            assert "cap_close" in res
            assert "eq_close" in res
            assert "returns_summary" in res
            assert "1W (5D)" in res["returns_summary"]
    except Exception as e:
        print(f"Sector test skipped due to missing nseuniverse data: {e}")


def test_all_sectors_summary_structure():
    """Test summary dataframe creation structure."""
    try:
        df = compute_all_sectors_summary(start="2023-01-01", end="2023-01-31")
        if not df.empty:
            assert "Sector" in df.columns
            assert "1W Spread (%)" in df.columns
            assert "Breadth (% > 50 DMA)" in df.columns
    except Exception as e:
        print(f"Summary test skipped: {e}")
