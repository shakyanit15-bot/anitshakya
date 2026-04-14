from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from data.data_loader import DataLoader
from execution.config_utils import load_config
from features.feature_generator import generate_features
from models.signal import EnsembleSignalEngine


def in_news_blackout(ts: pd.Timestamp, news_df: pd.DataFrame, before_min: int, after_min: int) -> bool:
    if news_df.empty:
        return False
    d = (news_df["event_time"] - ts).dt.total_seconds() / 60.0
    return bool(((d >= -after_min) & (d <= before_min)).any())


def run_bridge(config_path: str, profile_path: str | None, model_path: str, output_signal_file: str, news_csv: str | None = None) -> None:
    cfg = load_config(config_path, profile_path)
    loader = DataLoader(cfg["data"]["input_csv"], cfg["data"]["datetime_col"])
    raw = loader.load(required_columns=cfg["data"]["required_columns"])
    feats = generate_features(raw, cfg).dropna()

    latest_ts = feats.index[-1]
    latest = feats.iloc[-1]

    engine = EnsembleSignalEngine(model_path)
    pred = engine.predict_row(latest)

    spread = float(raw.loc[latest_ts, "spread"]) if "spread" in raw.columns else 0.0
    vol_unhealthy = latest["realized_vol"] > feats["realized_vol"].quantile(0.95)
    spread_unhealthy = spread > cfg["risk"]["spread_limit_points"]

    news_df = pd.DataFrame(columns=["event_time"])
    if news_csv:
        news_df = pd.read_csv(news_csv)
        news_df["event_time"] = pd.to_datetime(news_df["event_time"], utc=True)

    news_block = in_news_blackout(
        latest_ts,
        news_df,
        cfg["filters"]["news_blackout_minutes_before"],
        cfg["filters"]["news_blackout_minutes_after"],
    )

    signal = pred.signal
    if vol_unhealthy or spread_unhealthy or news_block:
        signal = "NO_TRADE"

    sl_points = float(latest["atr"] * cfg["labeling"]["atr_mult_lower"] / 0.01)
    out = Path(output_signal_file)
    out.parent.mkdir(parents=True, exist_ok=True)

    frame = pd.DataFrame(
        [
            {
                "time": latest_ts.strftime("%Y-%m-%d %H:%M:%S"),
                "signal": signal,
                "confidence": round(pred.confidence, 6),
                "sl_points": round(sl_points, 2),
            }
        ]
    )
    frame.to_csv(out, index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/base.yaml")
    parser.add_argument("--profile", default=None)
    parser.add_argument("--model", default="models/artifacts/ensemble.joblib")
    parser.add_argument("--signal-file", default="execution/signal_pipe.csv")
    parser.add_argument("--news-csv", default=None)
    args = parser.parse_args()

    run_bridge(args.config, args.profile, args.model, args.signal_file, args.news_csv)


if __name__ == "__main__":
    main()
