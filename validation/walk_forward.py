from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from backtest.engine import EventDrivenBacktester
from data.data_loader import DataLoader
from execution.config_utils import load_config
from features.feature_generator import generate_features
from features.labeling import make_dataset
from models.signal import EnsembleSignalEngine
from validation.metrics import compute_metrics, regime_breakdown


def _simulate_signals(ds: pd.DataFrame, model_path: str) -> pd.DataFrame:
    engine = EnsembleSignalEngine(model_path)
    rows = []
    for ts, row in ds.iterrows():
        res = engine.predict_row(row)
        rows.append({"time": ts, "signal": res.signal, "confidence": res.confidence})
    return pd.DataFrame(rows).set_index("time")


def run_walk_forward(config_path: str, profile_path: str | None, model_path: str) -> dict:
    cfg = load_config(config_path, profile_path)
    loader = DataLoader(cfg["data"]["input_csv"], cfg["data"]["datetime_col"])
    raw = loader.load(required_columns=cfg["data"]["required_columns"])

    features = generate_features(raw, cfg)
    ds = make_dataset(features, raw, cfg)

    v = cfg["validation"]
    train_n = v["walk_forward_train_bars"]
    val_n = v["walk_forward_validate_bars"]
    test_n = v["walk_forward_test_bars"]
    step = v["walk_forward_step_bars"]

    backtester = EventDrivenBacktester(cfg)
    runs = []
    start = 0

    while start + train_n + val_n + test_n <= len(ds):
        test_slice = ds.iloc[start + train_n + val_n : start + train_n + val_n + test_n]
        market_slice = raw.loc[test_slice.index].copy()
        market_slice["atr"] = test_slice["atr"]

        signals = _simulate_signals(test_slice.drop(columns=["label"]), model_path)
        trades, equity = backtester.run(market_slice, signals)
        metrics = compute_metrics(trades, equity)
        regimes = regime_breakdown(trades, market_slice)

        runs.append(
            {
                "window_start": str(test_slice.index.min()),
                "window_end": str(test_slice.index.max()),
                "metrics": metrics,
                "regimes": regimes,
            }
        )
        start += step

    summary = {
        "runs": runs,
        "mean_sharpe": float(pd.Series([r["metrics"].get("Sharpe", 0.0) for r in runs]).mean()) if runs else 0.0,
        "mean_profit_factor": float(pd.Series([r["metrics"].get("ProfitFactor", 0.0) for r in runs]).replace([float("inf")], pd.NA).dropna().mean()) if runs else 0.0,
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/base.yaml")
    parser.add_argument("--profile", default=None)
    parser.add_argument("--model", default="models/artifacts/ensemble.joblib")
    parser.add_argument("--output", default="reports/walk_forward_summary.json")
    args = parser.parse_args()

    out = run_walk_forward(args.config, args.profile, args.model)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
