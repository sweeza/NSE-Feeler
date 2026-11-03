"""
Market Breadth Engine: Orchestrates data loading via nseuniverse and computes all breadth indicators.
"""


import pandas as pd

try:
    import nseuniverse
    from nseuniverse import Index
except ImportError:
    nseuniverse = None
    Index = None

from .indicators import (
    compute_advance_decline,
    compute_breadth_thrusts,
    compute_equal_vs_cap_weighted,
    compute_high_low_breadth,
    compute_ma_breadth,
    compute_volume_breadth,
)


class MarketBreadthEngine:
    """
    Core engine for computing market breadth and participation metrics for NSE universes (default: Nifty 500).
    """

    def __init__(self, universe: str = "nifty500"):
        self.universe = universe.lower().strip()
        self.close_df = None
        self.prevclose_df = None
        self.volume_df = None
        self.index_obj = None

    def load_data(self, start: str | None = None, end: str | None = None, forward_fill: bool = False, adjusted: bool = True):
        """
        Loads required tensors ('close', 'prevclose', 'volume') from nseuniverse for the specified universe.
        """
        if nseuniverse is None:
            raise ImportError("nseuniverse package is required but not installed.")

        print(f"Loading tensors for universe '{self.universe}' (adjusted={adjusted})...")
        self.close_df = nseuniverse.load("close", universe=self.universe, adjusted=adjusted, start=start, end=end, forward_fill=forward_fill)
        self.prevclose_df = nseuniverse.load("prevclose", universe=self.universe, adjusted=adjusted, start=start, end=end, forward_fill=forward_fill)
        self.volume_df = nseuniverse.load("volume", universe=self.universe, adjusted=adjusted, start=start, end=end, forward_fill=forward_fill)

        # Map universe name to official index name for equal vs cap weighted comparison
        index_map = {
            "nifty500": "NIFTY 500",
            "nifty50": "NIFTY 50",
            "nifty100": "NIFTY 100",
            "nifty200": "NIFTY 200",
            "midcap150": "NIFTY MIDCAP 150",
            "smallcap250": "NIFTY SMALLCAP 250"
        }
        official_name = index_map.get(self.universe, "NIFTY 500")
        try:
            self.index_obj = Index(official_name)
        except Exception:  # noqa: BLE001
            try:
                self.index_obj = Index("NIFTY 500")
            except Exception:  # noqa: BLE001
                self.index_obj = None

        print(f"Successfully loaded close shape: {self.close_df.shape}")

    def compute_breadth_report(self) -> pd.DataFrame:
        """
        Computes all categories of market breadth indicators plus Equal vs Cap-Weighted spread.
        """
        if self.close_df is None or self.prevclose_df is None or self.volume_df is None:
            self.load_data()

        print("Computing Advance-Decline metrics...")
        ad_df = compute_advance_decline(self.close_df, self.prevclose_df)

        print("Computing Moving Average breadth (% above 20, 50, 200 SMAs)...")
        ma_df = compute_ma_breadth(self.close_df, windows=[20, 50, 200])

        print("Computing Volume breadth & TRIN / UDVR / 9:1 Days...")
        vol_df = compute_volume_breadth(self.close_df, self.volume_df, self.prevclose_df)

        print("Computing 52-week High-Low breadth & Hindenburg Omen...")
        benchmark_close = None
        if self.index_obj is not None:
            try:
                idx_hist = self.index_obj.history()
                if "close" in idx_hist.columns:
                    benchmark_close = idx_hist["close"]
            except Exception:  # noqa: BLE001, S110
                pass
        hl_df = compute_high_low_breadth(self.close_df, mc_osc=ad_df["mcclellan_oscillator"], benchmark_close=benchmark_close, window=252)

        print("Computing Breadth Thrusts (Zweig & Whaley)...")
        thrust_df = compute_breadth_thrusts(ad_df, vol_df)

        eq_cap_df = pd.DataFrame(index=self.close_df.index)
        if self.index_obj is not None:
            print("Computing Equal-Weighted vs Cap-Weighted Index Spread...")
            try:
                idx_hist = self.index_obj.history()
                if "close" in idx_hist.columns:
                    eq_cap_df = compute_equal_vs_cap_weighted(self.close_df, self.prevclose_df, idx_hist["close"])
            except Exception as e:  # noqa: BLE001
                print(f"Warning: Could not compute index spread: {e}")

        # Concatenate all indicators into a single comprehensive dataframe
        combined = pd.concat([
            ad_df,
            ma_df,
            hl_df,
            vol_df,
            thrust_df,
            eq_cap_df
        ], axis=1)

        # Drop duplicate columns if any
        combined = combined.loc[:, ~combined.columns.duplicated()]
        return combined
