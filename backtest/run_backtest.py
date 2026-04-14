from __future__ import annotations

import argparse
import json
from pathlib import Path

from backtest.engine import EventDrivenBacktester
from data.data_loader import DataLoader
from execution.config_utils import load_config
from features.feature_generator import generate_features
from features.labeling import make_dataset
from models.signal import EnsembleSignalEngine
from validation.metrics import compute_metrics, regime_breakdown


def build_signals(ds, model_path: str):
    engine = EnsembleSignalEngine(model_path)
    rows = []
    for ts, row in ds.iterrows():
        pred = engine.predict_row(row)
        rows.append({"time": ts, "signal": pred.signal, "confidence": pred.confidence})
    return rows


def run(config_path: str, profile_path: str | None, model_path: str, output_path: str) -> dict:
    cfg = load_config(config_path, profile_path)
    loader = DataLoader(cfg["data"]["input_csv"], cfg["data"]["datetime_col"])
    raw = loader.load(required_columns=cfg["data"]["required_columns"])

    features = generate_features(raw, cfg)
    ds = make_dataset(features, raw, cfg)

    signal_rows = build_signals(ds.drop(columns=["label"]), model_path)
    signal_df = __import__("pandas").DataFrame(signal_rows).set_index("time")

    market = raw.loc[signal_df.index].copy()
    market["atr"] = ds.loc[signal_df.index, "atr"]

    bt = EventDrivenBacktester(cfg)
    trades, equity = bt.run(market, signal_df)

    metrics = compute_metrics(trades, equity)
    regimes = regime_breakdown(trades, market)

    payload = {
        "metrics": metrics,
        "regime_breakdown": regimes,
        "trades_head": trades.head(20).to_dict(orient="records"),
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    trades.to_csv("reports/trades.csv", index=False)
    equity.to_csv("reports/equity_curve.csv")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/base.yaml")
    parser.add_argument("--profile", default=None)
    parser.add_argument("--model", default="models/artifacts/ensemble.joblib")
    parser.add_argument("--output", default="reports/backtest_summary.json")
    args = parser.parse_args()
    run(args.config, args.profile, args.model, args.output)


if __name__ == "__main__":
    main()
