"""
Core technical indicators for Market Breadth & Participation analysis.
Covers Advance-Decline, Moving Average Breadth, High-Low Extremes, Volume Breadth,
Breadth Thrusts, and Equal-Weighted vs Cap-Weighted Index Spread.
"""


import numpy as np
import pandas as pd


def compute_advance_decline(close_df: pd.DataFrame, prev_close_df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes Advance-Decline metrics (raw and universe-count normalized):
    - advancers (A), decliners (D), unchanged (U), active_issues (N_t)
    - net_advances (A - D), ad_line (Cumulative sum)
    - ad_ratio = (A - D) / N_t, cumulative_ad_ratio
    - mcclellan_oscillator, mcclellan_summation
    - mcclellan_oscillator_ratio, mcclellan_summation_ratio
    """
    active = close_df.notna() & prev_close_df.notna() & (close_df > 0) & (prev_close_df > 0)
    
    adv = (active & (close_df > prev_close_df)).sum(axis=1)
    dec = (active & (close_df < prev_close_df)).sum(axis=1)
    unch = (active & (close_df == prev_close_df)).sum(axis=1)
    total_active = adv + dec + unch
    
    net_adv = adv - dec
    ad_line = net_adv.cumsum()
    
    # Section 5 Rule 2: Normalize by Universe Count Nt
    eps = 1e-6
    ad_ratio = np.where(total_active > 0, net_adv / (total_active + eps), 0.0)
    ad_ratio_series = pd.Series(ad_ratio, index=close_df.index)
    cum_ad_ratio = ad_ratio_series.cumsum()
    
    # McClellan Oscillator (Raw Net Advances)
    ema19 = net_adv.ewm(span=19, adjust=False).mean()
    ema39 = net_adv.ewm(span=39, adjust=False).mean()
    mc_osc = ema19 - ema39
    mc_sum = mc_osc.cumsum()
    
    # McClellan Oscillator (Ratio-adjusted)
    ema19_r = ad_ratio_series.ewm(span=19, adjust=False).mean()
    ema39_r = ad_ratio_series.ewm(span=39, adjust=False).mean()
    mc_osc_r = ema19_r - ema39_r
    mc_sum_r = mc_osc_r.cumsum()
    
    df = pd.DataFrame({
        "advancers": adv,
        "decliners": dec,
        "unchanged": unch,
        "active_issues": total_active,
        "net_advances": net_adv,
        "ad_line": ad_line,
        "ad_ratio": ad_ratio_series,
        "cumulative_ad_ratio": cum_ad_ratio,
        "mcclellan_oscillator": mc_osc,
        "mcclellan_summation": mc_sum,
        "mcclellan_oscillator_ratio": mc_osc_r,
        "mcclellan_summation_ratio": mc_sum_r
    }, index=close_df.index)
    
    return df


def compute_ma_breadth(close_df: pd.DataFrame, windows: list | None = None) -> pd.DataFrame:
    """
    Computes percentage of active universe stocks trading above their SMAs (20, 50, 200 days).
    """
    if windows is None:
        windows = [20, 50, 200]
    results = {}
    active = close_df.notna() & (close_df > 0)
    
    for w in windows:
        sma = close_df.rolling(window=w, min_periods=w).mean()
        above = (active & (close_df > sma)).sum(axis=1)
        total_active = active.sum(axis=1)
        
        pct = np.where(total_active > 0, (above / total_active) * 100.0, np.nan)
        results[f"pct_above_sma_{w}"] = pct
        results[f"count_above_sma_{w}"] = above
        
    results["active_count"] = active.sum(axis=1)
    return pd.DataFrame(results, index=close_df.index)


def compute_high_low_breadth(close_df: pd.DataFrame, mc_osc: pd.Series | None = None, benchmark_close: pd.Series | None = None, window: int = 252) -> pd.DataFrame:
    """
    Computes 52-week High-Low breadth, High-Low Logic Index, raw and full Hindenburg Omen.
    """
    active = close_df.notna() & (close_df > 0)
    rolling_max = close_df.rolling(window=window, min_periods=window).max()
    rolling_min = close_df.rolling(window=window, min_periods=window).min()
    
    new_highs = (active & (close_df >= rolling_max * 0.995) & (rolling_max > 0)).sum(axis=1)
    new_lows = (active & (close_df <= rolling_min * 1.005) & (rolling_min > 0)).sum(axis=1)
    
    net_new_highs = new_highs - new_lows
    total_active = active.sum(axis=1)
    
    hlli = np.where(total_active > 0, np.minimum(new_highs, new_lows) / total_active, 0.0)
    
    # Raw threshold condition: both NH and NL >= 2.2% of active issues
    pct_nh = np.where(total_active > 0, new_highs / total_active, 0.0)
    pct_nl = np.where(total_active > 0, new_lows / total_active, 0.0)
    hindenburg_raw = (pct_nh >= 0.022) & (pct_nl >= 0.022)
    
    # Full Hindenburg Omen condition:
    # 1. Both NH and NL >= 2.2% of active issues
    # 2. Market is in an uptrend (benchmark close > 50 SMA or ROC20 > 0, or mean close > 50 SMA)
    # 3. McClellan Oscillator is negative
    # 4. New Highs not more than 2x New Lows (new_highs <= 2 * new_lows)
    if benchmark_close is not None and len(benchmark_close) == len(close_df):
        bm_sma50 = benchmark_close.rolling(window=50, min_periods=1).mean()
        uptrend = (benchmark_close > bm_sma50) | (benchmark_close.pct_change(20) > 0)
    else:
        mean_close = close_df.mean(axis=1)
        mean_sma50 = mean_close.rolling(window=50, min_periods=1).mean()
        uptrend = (mean_close > mean_sma50)
        
    if mc_osc is None:
        mc_osc = pd.Series(0.0, index=close_df.index)
        
    neg_mc = (mc_osc < 0)
    not_too_many_highs = (new_highs <= 2.0 * new_lows + 1e-6)
    
    hindenburg_full = hindenburg_raw & uptrend & neg_mc & not_too_many_highs
    
    df = pd.DataFrame({
        "new_highs": new_highs,
        "new_lows": new_lows,
        "net_new_highs": net_new_highs,
        "high_low_logic_index": hlli,
        "hindenburg_omen_raw": hindenburg_raw.astype(int),
        "hindenburg_omen": hindenburg_full.astype(int)
    }, index=close_df.index)
    
    return df


def compute_volume_breadth(close_df: pd.DataFrame, volume_df: pd.DataFrame, prev_close_df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes volume breadth:
    - Advancing Volume, Declining Volume
    - Up/Down Volume Ratio (UDVR), TRIN (Arms Index)
    - 9:1 Up-Volume Days & 9:1 Down-Volume Days
    """
    active = close_df.notna() & prev_close_df.notna() & volume_df.notna() & (close_df > 0) & (prev_close_df > 0)
    
    is_adv = active & (close_df > prev_close_df)
    is_dec = active & (close_df < prev_close_df)
    
    up_vol = (volume_df * is_adv.astype(float)).sum(axis=1)
    down_vol = (volume_df * is_dec.astype(float)).sum(axis=1)
    
    adv_count = is_adv.sum(axis=1)
    dec_count = is_dec.sum(axis=1)
    
    eps = 1e-6
    total_vol = up_vol + down_vol
    udvr = up_vol / (down_vol + eps)
    
    adv_dec_ratio = adv_count / (dec_count + eps)
    vol_ratio = up_vol / (down_vol + eps)
    trin = adv_dec_ratio / (vol_ratio + eps)
    
    # 9:1 Impulse Days
    up_vol_pct = np.where(total_vol > 0, up_vol / total_vol, 0.0)
    down_vol_pct = np.where(total_vol > 0, down_vol / total_vol, 0.0)
    
    up_9_1 = (up_vol_pct >= 0.90)
    down_9_1 = (down_vol_pct >= 0.90)
    
    df = pd.DataFrame({
        "up_volume": up_vol,
        "down_volume": down_vol,
        "up_down_volume_ratio": udvr,
        "trin": trin,
        "up_volume_9_1": up_9_1.astype(int),
        "down_volume_9_1": down_9_1.astype(int)
    }, index=close_df.index)
    
    return df


def compute_breadth_thrusts(ad_df: pd.DataFrame, vol_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    Computes Breadth Thrust indicators:
    - Zweig Breadth Thrust (ZBT)
    - Whaley 10-day Issues Thrust (Adv > 2 * Dec sum)
    - Whaley 5-day Volume Thrust (5d UpVol >= 9 * 5d DownVol)
    """
    adv = ad_df["advancers"]
    dec = ad_df["decliners"]
    total_ad = adv + dec
    
    ratio = np.where(total_ad > 0, adv / total_ad, np.nan)
    ratio_series = pd.Series(ratio, index=ad_df.index)
    
    zbt_ema10 = ratio_series.ewm(span=10, adjust=False).mean()
    was_oversold = (zbt_ema10.rolling(window=10, min_periods=10).min() < 0.40)
    is_thrust = was_oversold & (zbt_ema10 > 0.615)
    
    # Whaley Issues Thrust (10-day sum)
    adv_sum10 = adv.rolling(window=10, min_periods=10).sum()
    dec_sum10 = dec.rolling(window=10, min_periods=10).sum()
    whaley_issues_thrust = (adv_sum10 > 2.0 * dec_sum10)
    
    whaley_vol_thrust = pd.Series(0, index=ad_df.index)
    if vol_df is not None and "up_volume" in vol_df.columns and "down_volume" in vol_df.columns:
        up_vol_sum5 = vol_df["up_volume"].rolling(window=5, min_periods=5).sum()
        down_vol_sum5 = vol_df["down_volume"].rolling(window=5, min_periods=5).sum()
        whaley_vol_thrust = (up_vol_sum5 >= 9.0 * down_vol_sum5)

    df = pd.DataFrame({
        "zweig_thrust_ratio": ratio_series,
        "zweig_thrust_ema10": zbt_ema10,
        "zweig_thrust_signal": is_thrust.astype(int),
        "whaley_issues_thrust": whaley_issues_thrust.astype(int),
        "whaley_volume_thrust": whaley_vol_thrust.astype(int),
        "whaley_thrust_signal": whaley_issues_thrust.astype(int)
    }, index=ad_df.index)
    
    return df


def compute_equal_vs_cap_weighted(close_df: pd.DataFrame, prev_close_df: pd.DataFrame, official_cap_close: pd.Series) -> pd.DataFrame:
    """
    Computes Equal-Weighted Index via compounded daily returns of active constituents:
    r_EW,t = (1 / N_t) * sum_{i in Active_t} (Close_i,t / PrevClose_i,t - 1)
    I_EW,t = I_EW,t-1 * (1 + r_EW,t)
    Normalized to match official cap-weighted index on first common date, plus 20-day ROC spread.
    """
    active = close_df.notna() & prev_close_df.notna() & (close_df > 0) & (prev_close_df > 0)
    returns = (close_df / prev_close_df - 1.0).where(active)
    
    eq_daily_ret = returns.mean(axis=1).fillna(0.0)
    
    common_dates = eq_daily_ret.index.intersection(official_cap_close.index)
    if len(common_dates) == 0:
        return pd.DataFrame(index=close_df.index)
        
    cap_aligned = official_cap_close.loc[common_dates]
    eq_ret_aligned = eq_daily_ret.loc[common_dates]
    
    eq_prices = [cap_aligned.iloc[0]]
    for r in eq_ret_aligned.iloc[1:]:
        eq_prices.append(eq_prices[-1] * (1.0 + r))
    eq_compounded = pd.Series(eq_prices, index=common_dates)
    
    ratio = eq_compounded / (cap_aligned + 1e-6)
    spread = eq_compounded - cap_aligned
    
    roc20_eq = eq_compounded.pct_change(20) * 100.0
    roc20_cap = cap_aligned.pct_change(20) * 100.0
    roc20_spread = roc20_eq - roc20_cap
    
    df = pd.DataFrame({
        "equal_weighted_close": eq_compounded,
        "cap_weighted_close": cap_aligned,
        "eq_cap_ratio": ratio,
        "eq_cap_spread": spread,
        "eq_cap_roc20_spread": roc20_spread
    }, index=common_dates)
    
    return df.reindex(close_df.index)
