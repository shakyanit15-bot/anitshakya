from __future__ import annotations

import argparse
import json
from pathlib import Path

from execution.config_utils import load_config


def go_live_decision(summary: dict, cfg: dict) -> dict:
    crit = cfg["validation"]["pass_criteria"]

    run_metrics = [r.get("metrics", {}) for r in summary.get("runs", [])]
    sharpe_ok = all(m.get("Sharpe", -999) >= crit["min_sharpe"] for m in run_metrics) if run_metrics else False
    pf_ok = all(m.get("ProfitFactor", 0) >= crit["min_profit_factor"] for m in run_metrics) if run_metrics else False
    dd_ok = all(abs(m.get("MaxDrawdown", -1)) <= crit["max_drawdown_pct"] for m in run_metrics) if run_metrics else False
    trades_ok = sum(m.get("Trades", 0) for m in run_metrics) >= crit["min_trades"]

    passed = sharpe_ok and pf_ok and dd_ok and trades_ok
    return {
        "passed": passed,
        "checks": {
            "sharpe_ok": sharpe_ok,
            "profit_factor_ok": pf_ok,
            "drawdown_ok": dd_ok,
            "trades_ok": trades_ok,
        },
        "next_action": "GO_LIVE_PAPER" if passed else "RESEARCH_ITERATE",
    }


def sensitivity_template() -> dict:
    return {
        "threshold_grid": [0.55, 0.60, 0.65, 0.70],
        "sl_multipliers": [1.0, 1.2, 1.5, 1.8],
        "spread_shocks": [1.0, 1.5, 2.0],
        "slippage_shocks": [1.0, 1.5, 2.0],
        "note": "Run same backtest config while perturbing one variable at a time.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/base.yaml")
    parser.add_argument("--profile", default=None)
    parser.add_argument("--walk-forward", default="reports/walk_forward_summary.json")
    parser.add_argument("--output", default="reports/go_live_decision_report.json")
    args = parser.parse_args()

    cfg = load_config(args.config, args.profile)
    with open(args.walk_forward, "r", encoding="utf-8") as f:
        wf = json.load(f)

    report = {
        "system": cfg["system"],
        "walk_forward": wf,
        "decision": go_live_decision(wf, cfg),
        "sensitivity_test_plan": sensitivity_template(),
        "anti_leakage_controls": [
            "Triple-barrier labels use only future paths after each t0 and ATR at t0.",
            "Purged CV with embargo prevents overlapping information leakage.",
            "Walk-forward windows keep strict train/validate/test chronology.",
        ],
        "broker_specific_notes": [
            "Validate XAUUSD contract size and tick value for lot sizing.",
            "Map broker spread units to configured spread_limit_points.",
            "Tune slippage guardrails per VPS latency and broker execution policy.",
        ],
    }

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
