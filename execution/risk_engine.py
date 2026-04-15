from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskState:
    start_of_day_equity: float
    peak_equity: float
    blocked: bool = False
    block_reason: str = ""


class RiskEngine:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.risk_cfg = cfg["risk"]

    def lot_size(self, equity: float, risk_pct: float, stop_value: float, min_lot: float = 0.01) -> float:
        if stop_value <= 0:
            return 0.0
        lots = (equity * risk_pct) / stop_value
        return max(min_lot, round(lots, 2))

    def check_kill_switch(self, state: RiskState, equity: float) -> RiskState:
        daily_loss = (state.start_of_day_equity - equity) / max(state.start_of_day_equity, 1e-9)
        dd = (state.peak_equity - equity) / max(state.peak_equity, 1e-9)

        if equity > state.peak_equity:
            state.peak_equity = equity

        if daily_loss >= self.risk_cfg["daily_loss_limit_pct"]:
            state.blocked = True
            state.block_reason = "DAILY_LOSS_LIMIT"
        elif dd >= self.risk_cfg["max_drawdown_pct"]:
            state.blocked = True
            state.block_reason = "MAX_DRAWDOWN_LIMIT"
        return state

    def entry_allowed(self, spread_points: float, slippage_points: float) -> tuple[bool, str]:
        if spread_points > self.risk_cfg["spread_limit_points"]:
            return False, "SPREAD_FILTER"
        if slippage_points > self.risk_cfg["max_slippage_points"]:
            return False, "SLIPPAGE_FILTER"
        return True, "OK"
