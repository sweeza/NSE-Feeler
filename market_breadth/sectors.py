"""
Sector Rotation & Participation Analytics Module for Market Breadth Dashboard.
Computes Cap-Weighted vs Equal-Weighted performance, period returns (1D, 1W, 1M, 3M, 6M, 1Y),
Participation spreads (EW - MCAP), internal breadth, and relative rotation metrics across
all official NSE sectoral indices and market-cap tiers.
"""

import numpy as np
import pandas as pd

try:
    import nseuniverse
    from nseuniverse import Index
except ImportError:
    nseuniverse = None
    Index = None


OFFICIAL_SECTORS = [
    {"key": "nifty50", "name": "Nifty 50", "index": "NIFTY 50", "type": "Benchmark"},
    {"key": "niftynext50", "name": "Nifty Next 50", "index": "NIFTY NEXT 50", "type": "Benchmark"},
    {"key": "nifty100", "name": "Nifty 100", "index": "NIFTY 100", "type": "Benchmark"},
    {"key": "midcap150", "name": "Nifty Midcap 150", "index": "NIFTY MIDCAP 150", "type": "Benchmark"},
    {"key": "smallcap250", "name": "Nifty Smallcap 250", "index": "NIFTY SMALLCAP 250", "type": "Benchmark"},
    {"key": "nifty500", "name": "Nifty 500", "index": "NIFTY 500", "type": "Benchmark"},
    {"key": "niftybank", "name": "Nifty Bank", "index": "NIFTY BANK", "type": "Sectoral"},
    {"key": "niftyit", "name": "Nifty IT", "index": "NIFTY IT", "type": "Sectoral"},
    {"key": "niftyauto", "name": "Nifty Auto", "index": "NIFTY AUTO", "type": "Sectoral"},
    {"key": "niftypharma", "name": "Nifty Pharma", "index": "NIFTY PHARMA", "type": "Sectoral"},
    {"key": "niftyhealthcare", "name": "Nifty Healthcare", "index": "NIFTY HEALTHCARE INDEX", "type": "Sectoral"},
    {"key": "niftyfmcg", "name": "Nifty FMCG", "index": "NIFTY FMCG", "type": "Sectoral"},
    {"key": "niftymetal", "name": "Nifty Metal", "index": "NIFTY METAL", "type": "Sectoral"},
    {"key": "niftyenergy", "name": "Nifty Energy", "index": "NIFTY ENERGY", "type": "Sectoral"},
    {"key": "niftyoilgas", "name": "Nifty Oil & Gas", "index": "NIFTY OIL & GAS", "type": "Sectoral"},
    {"key": "niftyfinance", "name": "Nifty Financial Services", "index": "NIFTY FINANCIAL SERVICES", "type": "Sectoral"},
    {"key": "niftyrealty", "name": "Nifty Realty", "index": "NIFTY REALTY", "type": "Sectoral"},
    {"key": "niftymedia", "name": "Nifty Media", "index": "NIFTY MEDIA", "type": "Sectoral"},
    {"key": "niftyconsumerdurables", "name": "Nifty Consumer Durables", "index": "NIFTY CONSUMER DURABLES", "type": "Sectoral"},
]


def compute_sector_timeseries(sector_key: str, start: str | None = None, end: str | None = None) -> dict:
    """
    Loads constituent tensors and official index for a given sector/universe,
    computes equal-weighted index, returns across periods, and internal breadth.
    """
    if nseuniverse is None:
        raise ImportError("nseuniverse is required.")

    sec_info = next((s for s in OFFICIAL_SECTORS if s["key"] == sector_key), OFFICIAL_SECTORS[0])
    
    try:
        close_df = nseuniverse.load("close", universe=sector_key, adjusted=True, start=start, end=end)
        prev_close_df = nseuniverse.load("prevclose", universe=sector_key, adjusted=True, start=start, end=end)
    except Exception as e:
        print(f"Error loading tensors for {sector_key}: {e}")
        return {}

    if close_df.empty or prev_close_df.empty:
        return {}

    # Official Index Cap-Weighted Close
    cap_close = pd.Series(dtype=float)
    try:
        idx_obj = Index(sec_info["index"])
        hist = idx_obj.history(start=start, end=end)
        if "Close" in hist.columns:
            cap_close = hist["Close"]
        elif "close" in hist.columns:
            cap_close = hist["close"]
    except Exception:
        # Fallback to mean close of universe if official index not found
        cap_close = close_df.mean(axis=1)

    # Compute Equal-Weighted Index
    active = close_df.notna() & prev_close_df.notna() & (close_df > 0) & (prev_close_df > 0)
    returns = (close_df / prev_close_df - 1.0).where(active)
    eq_daily_ret = returns.mean(axis=1).fillna(0.0)

    common_dates = eq_daily_ret.index.intersection(cap_close.index)
    if len(common_dates) == 0:
        common_dates = eq_daily_ret.index
        cap_close = close_df.mean(axis=1).reindex(common_dates).ffill()

    cap_aligned = cap_close.reindex(common_dates).ffill()
    eq_ret_aligned = eq_daily_ret.reindex(common_dates).fillna(0.0)

    eq_prices = [cap_aligned.iloc[0] if not pd.isna(cap_aligned.iloc[0]) else 100.0]
    for r in eq_ret_aligned.iloc[1:]:
        eq_prices.append(eq_prices[-1] * (1.0 + r))
    eq_compounded = pd.Series(eq_prices, index=common_dates)

    eq_cap_ratio = eq_compounded / (cap_aligned + 1e-6)

    # Internal Breadth (% above 50 DMA)
    sma50 = close_df.rolling(window=50, min_periods=20).mean()
    above50 = (active & (close_df > sma50)).sum(axis=1)
    total_active = active.sum(axis=1)
    pct_above_50 = np.where(total_active > 0, (above50 / total_active) * 100.0, 0.0)
    pct_above_50_series = pd.Series(pct_above_50, index=close_df.index).reindex(common_dates).ffill()

    # Period Returns (%)
    periods = {"1D": 1, "1W (5D)": 5, "1M (21D)": 21, "3M (63D)": 63, "6M (126D)": 126, "1Y (252D)": 252}
    returns_summary = {}

    for label, days in periods.items():
        if len(cap_aligned) > days:
            cap_ret = (cap_aligned.iloc[-1] / cap_aligned.iloc[-days] - 1.0) * 100.0
            eq_ret = (eq_compounded.iloc[-1] / eq_compounded.iloc[-days] - 1.0) * 100.0
            spread = eq_ret - cap_ret
        else:
            cap_ret, eq_ret, spread = 0.0, 0.0, 0.0
        returns_summary[label] = {
            "cap_return": round(cap_ret, 2),
            "eq_return": round(eq_ret, 2),
            "spread_ew_mcap": round(spread, 2)
        }

    return {
        "sector_key": sector_key,
        "sector_name": sec_info["name"],
        "index_name": sec_info["index"],
        "dates": common_dates,
        "cap_close": cap_aligned,
        "eq_close": eq_compounded,
        "eq_cap_ratio": eq_cap_ratio,
        "pct_above_50": pct_above_50_series,
        "returns_summary": returns_summary,
        "latest_breadth": round(pct_above_50_series.iloc[-1] if len(pct_above_50_series) > 0 else 0.0, 1),
        "latest_ratio": round(eq_cap_ratio.iloc[-1] if len(eq_cap_ratio) > 0 else 1.0, 3)
    }


def compute_all_sectors_summary(start: str | None = None, end: str | None = None) -> pd.DataFrame:
    """
    Computes summary performance and EW-vs-MCAP spread for all official sectors.
    """
    rows = []
    for sec in OFFICIAL_SECTORS:
        res = compute_sector_timeseries(sec["key"], start=start, end=end)
        if not res:
            continue
        rs = res["returns_summary"]
        rows.append({
            "Sector": res["sector_name"],
            "Type": sec["type"],
            "1W Cap (%)": rs["1W (5D)"]["cap_return"],
            "1W Spread (%)": rs["1W (5D)"]["spread_ew_mcap"],
            "1M Cap (%)": rs["1M (21D)"]["cap_return"],
            "1M Spread (%)": rs["1M (21D)"]["spread_ew_mcap"],
            "3M Cap (%)": rs["3M (63D)"]["cap_return"],
            "3M Spread (%)": rs["3M (63D)"]["spread_ew_mcap"],
            "6M Cap (%)": rs["6M (126D)"]["cap_return"],
            "6M Spread (%)": rs["6M (126D)"]["spread_ew_mcap"],
            "1Y Cap (%)": rs["1Y (252D)"]["cap_return"],
            "1Y Spread (%)": rs["1Y (252D)"]["spread_ew_mcap"],
            "Breadth (% > 50 DMA)": res["latest_breadth"],
            "EW/MCAP Ratio": res["latest_ratio"]
        })
    return pd.DataFrame(rows)
