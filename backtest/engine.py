from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from execution.risk_engine import RiskEngine, RiskState


@dataclass
class Position:
    side: str
    entry_price: float
    stop_price: float
    lots: float
    entry_time: pd.Timestamp
    max_hold_bars: int
    bars_held: int = 0


class EventDrivenBacktester:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.risk_engine = RiskEngine(cfg)

    def run(self, market_df: pd.DataFrame, signal_df: pd.DataFrame, initial_equity: float = 100000.0) -> tuple[pd.DataFrame, pd.DataFrame]:
        equity = initial_equity
        risk_state = RiskState(start_of_day_equity=equity, peak_equity=equity)

        trade_log: list[dict] = []
        equity_curve = []
        pos: Position | None = None

        max_hold = self.cfg["labeling"]["max_hold_bars"]
        slippage = self.cfg["execution"]["slippage_points"]
        commission = self.cfg["execution"]["commission_per_lot"]

        for ts, row in market_df.iterrows():
            signal_row = signal_df.loc[ts] if ts in signal_df.index else None
            risk_state = self.risk_engine.check_kill_switch(risk_state, equity)

            if pos is not None:
                pos.bars_held += 1
                close_reason = None

                if pos.side == "BUY" and row["low"] <= pos.stop_price:
                    exit_price = pos.stop_price
                    close_reason = "STOP_LOSS"
                elif pos.side == "SELL" and row["high"] >= pos.stop_price:
                    exit_price = pos.stop_price
                    close_reason = "STOP_LOSS"
                elif signal_row is not None and (
                    (pos.side == "BUY" and signal_row["signal"] == "SELL")
                    or (pos.side == "SELL" and signal_row["signal"] == "BUY")
                ):
                    exit_price = row["close"]
                    close_reason = "COUNTER_SIGNAL"
                elif pos.bars_held >= pos.max_hold_bars:
                    exit_price = row["close"]
                    close_reason = "MAX_HOLD"
                else:
                    exit_price = None

                if exit_price is not None:
                    pnl_points = (exit_price - pos.entry_price) if pos.side == "BUY" else (pos.entry_price - exit_price)
                    gross = pnl_points * pos.lots * 100
                    costs = (slippage * pos.lots) + (commission * pos.lots)
                    net = gross - costs
                    equity += net
                    trade_log.append(
                        {
                            "entry_time": pos.entry_time,
                            "exit_time": ts,
                            "side": pos.side,
                            "entry_price": pos.entry_price,
                            "exit_price": exit_price,
                            "lots": pos.lots,
                            "pnl": net,
                            "reason": close_reason,
                        }
                    )
                    pos = None

            if pos is None and signal_row is not None and not risk_state.blocked:
                allowed, block_reason = self.risk_engine.entry_allowed(row.get("spread", 0.0), slippage)
                if allowed and signal_row["signal"] in {"BUY", "SELL"}:
                    atr = max(row.get("atr", 0.0), 1e-6)
                    stop_dist = atr * self.cfg["labeling"]["atr_mult_lower"]
                    stop_value = stop_dist * 100
                    lots = self.risk_engine.lot_size(
                        equity,
                        self.cfg["risk"]["risk_pct"],
                        stop_value,
                    )
                    if lots > 0:
                        stop_price = row["close"] - stop_dist if signal_row["signal"] == "BUY" else row["close"] + stop_dist
                        pos = Position(
                            side=signal_row["signal"],
                            entry_price=row["close"],
                            stop_price=stop_price,
                            lots=lots,
                            entry_time=ts,
                            max_hold_bars=max_hold,
                        )
                elif not allowed:
                    trade_log.append(
                        {
                            "entry_time": ts,
                            "exit_time": ts,
                            "side": "NO_TRADE",
                            "entry_price": np.nan,
                            "exit_price": np.nan,
                            "lots": 0,
                            "pnl": 0,
                            "reason": block_reason,
                        }
                    )

            equity_curve.append({"time": ts, "equity": equity, "blocked": risk_state.blocked})

        return pd.DataFrame(trade_log), pd.DataFrame(equity_curve).set_index("time")
