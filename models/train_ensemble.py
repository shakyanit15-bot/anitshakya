from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from data.data_loader import DataLoader
from execution.config_utils import load_config
from features.feature_generator import generate_features
from features.labeling import make_dataset
from models.calibration import CalibratedModel

# Labels are intentionally encoded as {-1: SELL, 0: NO_TRADE, 1: BUY} across the project.
CLASS_LABEL_OFFSET = -1


def _build_model(name: str, seed: int):
    if name == "lightgbm":
        from lightgbm import LGBMClassifier

        return LGBMClassifier(
            n_estimators=300,
            learning_rate=0.03,
            num_leaves=31,
            class_weight="balanced",
            random_state=seed,
        )
    if name == "xgboost":
        from xgboost import XGBClassifier

        return XGBClassifier(
            n_estimators=250,
            max_depth=5,
            learning_rate=0.04,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="multi:softprob",
            eval_metric="mlogloss",
            random_state=seed,
        )
    if name == "catboost":
        from catboost import CatBoostClassifier

        return CatBoostClassifier(
            iterations=300,
            learning_rate=0.03,
            depth=6,
            random_seed=seed,
            verbose=False,
            loss_function="MultiClass",
        )
    raise ValueError(f"Unsupported model: {name}")


def _purged_splits(n_samples: int, n_splits: int, embargo: int):
    tscv = TimeSeriesSplit(n_splits=n_splits)
    for train_idx, test_idx in tscv.split(np.arange(n_samples)):
        if embargo > 0:
            train_idx = train_idx[train_idx < (test_idx[0] - embargo)]
        if len(train_idx) > 0:
            yield train_idx, test_idx


def train(config_path: str, profile_path: str | None, output_dir: str) -> dict:
    cfg = load_config(config_path, profile_path)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    data_cfg = cfg["data"]
    loader = DataLoader(data_cfg["input_csv"], data_cfg["datetime_col"])
    raw = loader.load(required_columns=data_cfg["required_columns"])

    x = generate_features(raw, cfg)
    ds = make_dataset(x, raw, cfg)

    y = ds["label"].astype(int).values
    x = ds.drop(columns=["label"]).astype(float)

    models = []
    for i, model_name in enumerate(cfg["model"]["ensemble"]):
        model = _build_model(model_name, cfg["model"]["random_seed"] + i)
        calibrated = CalibratedModel(model, method=cfg["model"]["calibration_method"])
        calibrated.fit(x.values, y)
        models.append({"name": model_name, "model": calibrated})

    val_scores = []
    for tr, te in _purged_splits(
        len(x),
        cfg["validation"]["purged_cv_folds"],
        cfg["validation"]["embargo_bars"],
    ):
        probs = []
        for m in models:
            local_model = _build_model(m["name"], cfg["model"]["random_seed"])
            calibrated = CalibratedModel(local_model, method=cfg["model"]["calibration_method"])
            calibrated.fit(x.values[tr], y[tr])
            probs.append(calibrated.predict_proba(x.values[te]))
        avg_prob = np.mean(probs, axis=0)
        # Model classes are encoded as {-1, 0, 1}; argmax returns {0, 1, 2}, so shift by CLASS_LABEL_OFFSET.
        pred = np.argmax(avg_prob, axis=1) + CLASS_LABEL_OFFSET
        val_scores.append(float((pred == y[te]).mean()))

    artifact = {
        "config": cfg,
        "features": list(x.columns),
        "models": models,
        "cv_accuracy": float(np.mean(val_scores)) if val_scores else None,
    }
    joblib.dump(artifact, out / "ensemble.joblib")
    with open(out / "training_summary.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "rows": int(len(x)),
                "class_balance": pd.Series(y).value_counts(normalize=True).to_dict(),
                "cv_accuracy": artifact["cv_accuracy"],
            },
            f,
            indent=2,
        )
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/base.yaml")
    parser.add_argument("--profile", default=None)
    parser.add_argument("--output", default="models/artifacts")
    args = parser.parse_args()
    train(args.config, args.profile, args.output)


if __name__ == "__main__":
    main()
