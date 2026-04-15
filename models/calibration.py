from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.calibration import CalibratedClassifierCV


class CalibratedModel:
    def __init__(self, base_model: Any, method: str = "isotonic"):
        self.base_model = base_model
        self.method = method
        self.model = CalibratedClassifierCV(base_model, method=method, cv=3)

    def fit(self, x: np.ndarray, y: np.ndarray) -> "CalibratedModel":
        self.model.fit(x, y)
        return self

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(x)

    def predict(self, x: np.ndarray) -> np.ndarray:
        return self.model.predict(x)
