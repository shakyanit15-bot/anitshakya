from __future__ import annotations

import argparse
import copy
import itertools
import json
import tempfile
import os
from pathlib import Path

import yaml

from backtest.run_backtest import run
from execution.config_utils import load_config


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/base.yaml")
    parser.add_argument("--profile", default=None)
    parser.add_argument("--model", default="models/artifacts/ensemble.joblib")
    parser.add_argument("--output", default="reports/sensitivity_results.json")
    args = parser.parse_args()

    base_cfg = load_config(args.config, args.profile)
    thresholds = [0.55, 0.60, 0.65]
    sl_mults = [1.2, 1.4, 1.6]
    spread_shocks = [1.0, 1.5]
    slippage_shocks = [1.0, 1.5]

    results = []
    for th, slm, sp, slp in itertools.product(thresholds, sl_mults, spread_shocks, slippage_shocks):
        cfg = copy.deepcopy(base_cfg)

        cfg["model"]["confidence_threshold_buy"] = th
        cfg["model"]["confidence_threshold_sell"] = th
        cfg["labeling"]["atr_mult_lower"] = slm
        cfg["risk"]["spread_limit_points"] = int(cfg["risk"]["spread_limit_points"] * sp)
        cfg["execution"]["slippage_points"] = int(cfg["execution"]["slippage_points"] * slp)

        # Persist temp config to reuse normal runner
        tmp_dir = Path(tempfile.gettempdir())
        fd_cfg, tmp_cfg_path = tempfile.mkstemp(prefix="mad_turtle_cfg_", suffix=".yaml", dir=tmp_dir)
        os.close(fd_cfg)
        with open(tmp_cfg_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f)

        fd_bt, tmp_bt_path = tempfile.mkstemp(prefix="mad_turtle_bt_", suffix=".json", dir=tmp_dir)
        os.close(fd_bt)
        out = run(tmp_cfg_path, None, args.model, tmp_bt_path)
        results.append(
            {
                "threshold": th,
                "sl_mult": slm,
                "spread_shock": sp,
                "slippage_shock": slp,
                "metrics": out["metrics"],
            }
        )
        Path(tmp_cfg_path).unlink(missing_ok=True)
        Path(tmp_bt_path).unlink(missing_ok=True)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"results": results}, f, indent=2)


if __name__ == "__main__":
    main()
