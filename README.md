# Mad Turtle XAUUSD ML Trading System

Production-oriented adaptive trend-following system for **XAUUSD** with ML ensemble, strict risk controls, leakage-safe validation, and MT5/MQL5 execution.

## Executive Summary
- Multi-timeframe (M5/M15/H1) feature pipeline with trend, volatility, candle, session, spread, and alignment context.
- 3-class calibrated ensemble classifier: **BUY / SELL / NO_TRADE**.
- Triple-barrier labeling with ATR-based barriers and time barrier.
- Event-driven backtest with costs (spread, slippage, commission) and one-position policy.
- Walk-forward and purged CV validation.
- MT5 EA template enforcing: one position, no martingale/grid/averaging-down, always SL, kill-switches, and dormant filters.

## Architecture
### Component Diagram (text)
1. MT5 Bars CSV / Live feed
2. Python Data Loader
3. Feature Generator (M5+resampled M15/H1 context)
4. Triple-Barrier Labeling
5. Ensemble Trainer + Probability Calibration
6. Signal Engine + Dormant-Mode Filters
7. Risk Engine (lot sizing, limits, circuit breakers)
8. Backtest/Walk-Forward Validator
9. Go-Live Decision Report
10. MQL5 EA execution + structured logs

### Data Flow
`MT5 bars -> data_loader -> feature_generator -> signal model -> signal_bridge -> risk checks -> MQL5 order execution -> logs (CSV/JSON) -> validation reports`

## Folder Tree
```text
/data
/features
/models
/backtest
/validation
/execution
/mql5
/config
/reports
/monitoring
/tests
/docs
```

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run Pipeline
1. Put historical bars at `data/xauusd_mt5_bars.csv`
2. Train ensemble:
   ```bash
   python -m models.train_ensemble --config config/base.yaml --profile config/moderate.yaml --output models/artifacts
   ```
3. Run backtest:
   ```bash
   python -m backtest.run_backtest --config config/base.yaml --profile config/moderate.yaml --model models/artifacts/ensemble.joblib
   ```
4. Run walk-forward:
   ```bash
   python -m validation.walk_forward --config config/base.yaml --profile config/moderate.yaml --model models/artifacts/ensemble.joblib
   ```
5. Generate decision report:
   ```bash
   python -m reports.report_generator --config config/base.yaml --profile config/moderate.yaml
   ```
6. Build signal file for EA:
   ```bash
   python -m execution.signal_bridge --config config/base.yaml --profile config/moderate.yaml --model models/artifacts/ensemble.joblib --signal-file execution/signal_pipe.csv
   ```

## Testing
```bash
pytest -q
```

## MQL5 Deployment Notes
- Copy `mql5/MadTurtleXAUUSD.mq5` into `MQL5/Experts/` and compile in MetaEditor.
- Ensure `signal_pipe.csv` is available to terminal **Common Files** path.
- Validate broker-specific tick size/value and spread units before live deployment.

## Anti-Leakage Controls
- Triple-barrier labels use future-only path from each t0 and ATR at t0.
- Purged time-series CV with embargo.
- Walk-forward chronological train/validate/test splits.

## Overfitting Controls
- Use strict out-of-sample walk-forward windows.
- Apply confidence threshold and dormant regime filters.
- Stress test spread/slippage shocks and threshold sensitivity before go-live.

## Live-Paper Rollout (summary)
1. Local dry-run + report pass.
2. Deploy on VPS with MT5 paper account.
3. Run 2–4 weeks paper monitoring.
4. Start tiny live capital with conservative profile.
5. Scale only after passing drawdown and execution quality gates.

See `docs/deployment_runbook.md` for full checklist.
