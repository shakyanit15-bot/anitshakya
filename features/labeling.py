from __future__ import annotations

import numpy as np
import pandas as pd


LABEL_MAP = {-1: "SELL", 0: "NO_TRADE", 1: "BUY"}


def triple_barrier_labels(
    df: pd.DataFrame,
    atr: pd.Series,
    upper_mult: float,
    lower_mult: float,
    max_hold_bars: int,
) -> pd.Series:
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    atrv = atr.values

    labels = np.zeros(len(df), dtype=int)
    for i in range(len(df) - max_hold_bars - 1):
        if np.isnan(atrv[i]) or atrv[i] <= 0:
            labels[i] = 0
            continue
        up_barrier = close[i] + upper_mult * atrv[i]
        dn_barrier = close[i] - lower_mult * atrv[i]

        outcome = 0
        for j in range(i + 1, i + max_hold_bars + 1):
            if high[j] >= up_barrier:
                outcome = 1
                break
            if low[j] <= dn_barrier:
                outcome = -1
                break
        labels[i] = outcome
    return pd.Series(labels, index=df.index, name="label")


def make_dataset(features: pd.DataFrame, raw_df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    lcfg = cfg["labeling"]
    atr_col = "atr" if "atr" in features.columns else None
    if atr_col is None:
        raise ValueError("ATR not found in features; generate features first")

    y = triple_barrier_labels(
        raw_df,
        features[atr_col],
        lcfg["atr_mult_upper"],
        lcfg["atr_mult_lower"],
        lcfg["max_hold_bars"],
    )

    ds = features.copy()
    ds["label"] = y
    ds = ds.dropna()
    return ds
