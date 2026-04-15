from __future__ import annotations

import numpy as np
import pandas as pd

from features.feature_generator import generate_features
from features.labeling import make_dataset, triple_barrier_labels


def _cfg() -> dict:
    return {
        "features": {
            "atr_period": 14,
            "adx_period": 14,
            "donchian_period": 20,
            "ma_fast": 10,
            "ma_slow": 20,
            "realized_vol_window": 10,
            "range_window": 10,
            "momentum_windows": [3, 6],
            "spread_ma_window": 10,
        },
        "labeling": {"atr_mult_upper": 1.2, "atr_mult_lower": 1.2, "max_hold_bars": 10},
    }


def _sample(n: int = 220) -> pd.DataFrame:
    idx = pd.date_range("2025-01-01", periods=n, freq="5min", tz="UTC")
    base = 2500 + np.cumsum(np.random.default_rng(7).normal(0, 0.5, n))
    high = base + np.random.default_rng(8).uniform(0.1, 1.2, n)
    low = base - np.random.default_rng(9).uniform(0.1, 1.2, n)
    open_ = base + np.random.default_rng(10).normal(0, 0.2, n)
    close = base
    spread = np.random.default_rng(11).integers(15, 35, n)
    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "tick_volume": 100,
            "spread": spread,
        },
        index=idx,
    )


def test_feature_generation_contains_required_columns() -> None:
    df = _sample()
    x = generate_features(df, _cfg())
    for col in ["ma_slope_fast", "donch_dist_norm", "adx", "atr", "realized_vol", "body_ratio", "align_M15", "session_London"]:
        assert col in x.columns


def test_triple_barrier_output_classes_and_no_lookahead_shape() -> None:
    df = _sample()
    x = generate_features(df, _cfg())
    y = triple_barrier_labels(df, x["atr"], 1.2, 1.2, 10)
    assert set(y.dropna().unique()).issubset({-1, 0, 1})

    ds = make_dataset(x, df, _cfg())
    assert "label" in ds.columns
    assert len(ds) <= len(df)
