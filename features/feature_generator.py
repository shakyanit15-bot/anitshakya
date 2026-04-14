from __future__ import annotations

import numpy as np
import pandas as pd


SESSION_BINS = {
    "Asia": (0, 7),
    "London": (7, 13),
    "NewYork": (13, 22),
}


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            (df["high"] - df["low"]).abs(),
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def _adx(df: pd.DataFrame, period: int) -> pd.Series:
    up_move = df["high"].diff()
    down_move = -df["low"].diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    atr = _atr(df, period)
    plus_di = 100 * pd.Series(plus_dm, index=df.index).rolling(period).sum() / atr
    minus_di = 100 * pd.Series(minus_dm, index=df.index).rolling(period).sum() / atr
    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)).fillna(0)
    return dx.rolling(period).mean()


def _session_feature(index: pd.DatetimeIndex) -> pd.DataFrame:
    hours = index.tz_convert("UTC").hour
    frame = pd.DataFrame(index=index)
    for name, (start, end) in SESSION_BINS.items():
        frame[f"session_{name}"] = ((hours >= start) & (hours < end)).astype(int)
    return frame


def add_multi_timeframe_alignment(df: pd.DataFrame, fast_col: str, slow_col: str) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    for tf, rule in {"M5": "5min", "M15": "15min", "H1": "1h"}.items():
        r = df[[fast_col, slow_col]].resample(rule).last().ffill()
        align = (r[fast_col] > r[slow_col]).astype(int).reindex(df.index, method="ffill").fillna(0)
        out[f"align_{tf}"] = align
    return out


def generate_features(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    c = cfg["features"]
    x = pd.DataFrame(index=df.index)

    ma_fast = _ema(df["close"], c["ma_fast"])
    ma_slow = _ema(df["close"], c["ma_slow"])
    atr = _atr(df, c["atr_period"])

    x["ret_1"] = df["close"].pct_change()
    for w in c["momentum_windows"]:
        x[f"mom_{w}"] = df["close"].pct_change(w)

    x["ma_fast"] = ma_fast
    x["ma_slow"] = ma_slow
    x["ma_slope_fast"] = ma_fast.diff(3)
    x["ma_slope_slow"] = ma_slow.diff(3)

    donch_hi = df["high"].rolling(c["donchian_period"]).max()
    donch_lo = df["low"].rolling(c["donchian_period"]).min()
    width = (donch_hi - donch_lo).replace(0, np.nan)
    x["donch_dist_norm"] = (df["close"] - (donch_hi + donch_lo) / 2) / width

    x["adx"] = _adx(df, c["adx_period"])
    x["atr"] = atr
    x["realized_vol"] = x["ret_1"].rolling(c["realized_vol_window"]).std()
    x["range_expansion"] = (df["high"] - df["low"]) / (df["high"] - df["low"]).rolling(c["range_window"]).mean()

    body = (df["close"] - df["open"]).abs()
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    x["body_ratio"] = body / rng
    x["upper_wick_ratio"] = (df["high"] - df[["open", "close"]].max(axis=1)).abs() / rng
    x["lower_wick_ratio"] = (df[["open", "close"]].min(axis=1) - df["low"]).abs() / rng
    x["breakout_strength"] = (df["close"] - donch_hi.shift(1)) / atr.replace(0, np.nan)

    spread = df["spread"] if "spread" in df else pd.Series(0.0, index=df.index)
    x["spread"] = spread
    x["spread_state"] = (spread > spread.rolling(c["spread_ma_window"]).mean()).astype(int)

    x = pd.concat([x, _session_feature(df.index), add_multi_timeframe_alignment(x.ffill(), "ma_fast", "ma_slow")], axis=1)
    x = x.replace([np.inf, -np.inf], np.nan)
    return x
