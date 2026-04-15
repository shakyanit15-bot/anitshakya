from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class DataLoader:
    csv_path: str
    datetime_col: str = "time"

    def load(self, required_columns: list[str] | None = None) -> pd.DataFrame:
        df = pd.read_csv(self.csv_path)
        if required_columns:
            missing = [c for c in required_columns if c not in df.columns]
            if missing:
                raise ValueError(f"Missing required columns: {missing}")

        df[self.datetime_col] = pd.to_datetime(df[self.datetime_col], utc=True)
        df = df.sort_values(self.datetime_col).drop_duplicates(self.datetime_col)
        df = df.set_index(self.datetime_col)
        numeric_cols = list(df.columns)
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
        return df.dropna(subset=["open", "high", "low", "close"])
