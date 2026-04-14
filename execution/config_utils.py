from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(base_path: str | Path, profile_path: str | Path | None = None) -> dict[str, Any]:
    with open(base_path, "r", encoding="utf-8") as f:
        base = yaml.safe_load(f)
    if profile_path is None:
        return base
    with open(profile_path, "r", encoding="utf-8") as f:
        profile = yaml.safe_load(f)
    return _deep_merge(base, profile)
