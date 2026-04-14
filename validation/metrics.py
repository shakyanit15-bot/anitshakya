from __future__ import annotations

import numpy as np
import pandas as pd


def compute_metrics(trades: pd.DataFrame, equity: pd.DataFrame, bars_per_year: int = 12 * 24 * 252) -> dict:
    # Default assumes 5-minute bars: 12 bars/hour * 24 hours/day * 252 trading days/year.
    if equity.empty:
        return {}

    eq = equity["equity"].astype(float)
    rets = eq.pct_change().fillna(0.0)
    years = max(len(eq) / bars_per_year, 1 / bars_per_year)

    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1
    sharpe = np.sqrt(bars_per_year) * rets.mean() / (rets.std() + 1e-12)
    downside = rets[rets < 0].std() + 1e-12
    sortino = np.sqrt(bars_per_year) * rets.mean() / downside

    running_max = eq.cummax()
    dd = (eq - running_max) / running_max
    max_dd = dd.min()
    calmar = cagr / abs(max_dd if max_dd != 0 else 1e-9)

    pnl = trades["pnl"] if not trades.empty and "pnl" in trades else pd.Series(dtype=float)
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]

    gross_profit = wins.sum()
    gross_loss = abs(losses.sum())
    profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else float("inf")

    expectancy = float(pnl.mean()) if len(pnl) else 0.0
    win_rate = float((pnl > 0).mean()) if len(pnl) else 0.0
    avg_win = float(wins.mean()) if len(wins) else 0.0
    avg_loss = float(losses.mean()) if len(losses) else 0.0

    exposure = float((~equity.get("blocked", pd.Series(False, index=equity.index))).mean())
    turnover = float(len(trades) / len(eq)) if len(eq) else 0.0

    return {
        "CAGR": float(cagr),
        "Sharpe": float(sharpe),
        "Sortino": float(sortino),
        "ProfitFactor": float(profit_factor),
        "Expectancy": float(expectancy),
        "MaxDrawdown": float(max_dd),
        "Calmar": float(calmar),
        "WinRate": float(win_rate),
        "AvgWin": float(avg_win),
        "AvgLoss": float(avg_loss),
        "Exposure": float(exposure),
        "Turnover": float(turnover),
        "Trades": int(len(trades)),
    }


def regime_breakdown(trades: pd.DataFrame, market: pd.DataFrame) -> dict:
    if trades.empty:
        return {}

    market = market.copy()
    market["regime_trend"] = (market.get("adx", 0) >= 25).astype(int)
    atr_series = market["atr"] if "atr" in market.columns else pd.Series(0.0, index=market.index)
    market["regime_vol"] = (atr_series >= atr_series.median()).astype(int)

    out = {}
    merged = trades.merge(market[["regime_trend", "regime_vol"]], left_on="entry_time", right_index=True, how="left")

    for key, grp in merged.groupby(["regime_trend", "regime_vol"]):
        out[f"trend_{key[0]}_highvol_{key[1]}"] = {
            "trades": int(len(grp)),
            "pnl": float(grp["pnl"].sum()),
            "win_rate": float((grp["pnl"] > 0).mean()) if len(grp) else 0.0,
        }

    if "entry_time" in trades:
        sessions = pd.to_datetime(trades["entry_time"], utc=True).dt.hour
        for name, cond in {
            "Asia": (sessions < 7),
            "London": ((sessions >= 7) & (sessions < 13)),
            "NewYork": ((sessions >= 13) & (sessions < 22)),
        }.items():
            grp = trades[cond]
            out[f"session_{name}"] = {
                "trades": int(len(grp)),
                "pnl": float(grp["pnl"].sum()) if len(grp) else 0.0,
            }

    return out
