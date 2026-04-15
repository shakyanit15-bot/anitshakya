# Deployment Runbook: Local -> VPS -> Paper -> Live

## 1) Local Build & Validation
1. Install Python deps and run `pytest -q`.
2. Train model with selected profile.
3. Run backtest, walk-forward, and report generation.
4. Confirm go-live decision report passes criteria.

## 2) VPS Setup
1. Provision low-latency Windows VPS near broker server.
2. Install MT5 terminal + MetaEditor.
3. Configure terminal auto-login with paper account.
4. Sync Python signal service and schedule task every bar close (M5).

## 3) MT5 Paper Rollout
1. Compile and attach `MadTurtleXAUUSD` EA to XAUUSD M5 chart.
2. Enable Algo Trading.
3. Verify signal file ingestion and logging in common files.
4. Keep profile conservative first.

## 4) Monitoring Checklist
- Spread and slippage within configured bounds.
- Daily kill-switch not repeatedly triggered.
- Max drawdown under policy.
- Signal-to-fill latency acceptable.
- Session and news blackout behavior consistent.
- Counter-signal and max-hold exits functioning.

## 5) Incident Response (Disable Conditions)
Disable immediately when any condition is met:
- API/file signal mismatch or stale signals.
- Repeated order rejections or abnormal slippage.
- Daily loss circuit breaker trigger.
- Unexpected spread regime / broker execution anomaly.
- Model drift (paper performance materially below validation).

Actions:
1. Disable AutoTrading in MT5.
2. Close open position manually if policy requires.
3. Preserve logs (`mad_turtle_log.csv`, `.jsonl`) and MT5 journal.
4. Run post-incident root-cause report before restart.

## 6) Live Small-Capital Start
1. Switch to live with smallest allowed lot sizing.
2. Use conservative profile for first month.
3. Increase risk only after statistically meaningful stable performance.
4. Re-run walk-forward monthly with latest data and re-approve go-live.
