from __future__ import annotations

import pandas as pd

from backtest.engine import EventDrivenBacktester


def _cfg() -> dict:
    return {
        "labeling": {"max_hold_bars": 5, "atr_mult_lower": 1.4},
        "execution": {"slippage_points": 5, "commission_per_lot": 7.0},
        "risk": {
            "risk_pct": 0.005,
            "daily_loss_limit_pct": 0.05,
            "max_drawdown_pct": 0.2,
            "spread_limit_points": 100,
            "max_slippage_points": 50,
        },
    }


def _market() -> pd.DataFrame:
    idx = pd.date_range("2025-01-01", periods=40, freq="5min", tz="UTC")
    price = pd.Series(2500.0 + (pd.RangeIndex(40) * 0.2), index=idx)
    return pd.DataFrame(
        {
            "open": price,
            "high": price + 1.0,
            "low": price - 1.0,
            "close": price,
            "spread": 20,
            "atr": 1.2,
        },
        index=idx,
    )


def _signals(idx) -> pd.DataFrame:
    s = pd.DataFrame(index=idx)
    s["signal"] = "NO_TRADE"
    s.loc[idx[3], "signal"] = "BUY"
    s.loc[idx[15], "signal"] = "SELL"
    s["confidence"] = 0.8
    return s


def test_backtest_reproducible_results() -> None:
    market = _market()
    signals = _signals(market.index)

    bt1 = EventDrivenBacktester(_cfg())
    bt2 = EventDrivenBacktester(_cfg())

    trades1, eq1 = bt1.run(market, signals)
    trades2, eq2 = bt2.run(market, signals)

    assert trades1.equals(trades2)
    assert eq1.equals(eq2)
