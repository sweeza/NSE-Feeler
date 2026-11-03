"""
Market Breadth & Participation Engine for Nifty 500 and NSE universes.
"""

from .engine import MarketBreadthEngine
from .sectors import (
    OFFICIAL_SECTORS,
    compute_all_sectors_summary,
    compute_sector_timeseries,
)

__all__ = [
    "OFFICIAL_SECTORS",
    "MarketBreadthEngine",
    "compute_all_sectors_summary",
    "compute_sector_timeseries"
]
