from __future__ import annotations

from dataclasses import dataclass

import joblib
import numpy as np
import pandas as pd


@dataclass
class SignalResult:
    signal: str
    confidence: float
    probs: dict[str, float]


class EnsembleSignalEngine:
    def __init__(self, model_path: str):
        self.artifact = joblib.load(model_path)
        self.features = self.artifact["features"]
        self.cfg = self.artifact["config"]

    def predict_row(self, feature_row: pd.Series) -> SignalResult:
        row = feature_row[self.features].astype(float).values.reshape(1, -1)
        probs = [m["model"].predict_proba(row)[0] for m in self.artifact["models"]]
        avg_prob = np.mean(probs, axis=0)

        p_sell, p_no, p_buy = float(avg_prob[0]), float(avg_prob[1]), float(avg_prob[2])
        th_buy = self.cfg["model"]["confidence_threshold_buy"]
        th_sell = self.cfg["model"]["confidence_threshold_sell"]
        no_trade_max = self.cfg["model"]["no_trade_max_confidence"]

        signal = "NO_TRADE"
        confidence = max(p_buy, p_sell)
        if p_buy >= th_buy and p_no <= no_trade_max:
            signal = "BUY"
            confidence = p_buy
        elif p_sell >= th_sell and p_no <= no_trade_max:
            signal = "SELL"
            confidence = p_sell

        return SignalResult(
            signal=signal,
            confidence=confidence,
            probs={"SELL": p_sell, "NO_TRADE": p_no, "BUY": p_buy},
        )
