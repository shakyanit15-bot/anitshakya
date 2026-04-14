# Dry-Run Simulation Instructions

1. Prepare `data/xauusd_mt5_bars.csv` with required columns:
   `time,open,high,low,close,tick_volume,spread`
2. Train model:
   `python -m models.train_ensemble --config config/base.yaml --profile config/conservative.yaml --output models/artifacts`
3. Run backtest:
   `python -m backtest.run_backtest --config config/base.yaml --profile config/conservative.yaml --model models/artifacts/ensemble.joblib`
4. Walk-forward validation:
   `python -m validation.walk_forward --config config/base.yaml --profile config/conservative.yaml --model models/artifacts/ensemble.joblib`
5. Generate go-live report:
   `python -m reports.report_generator --config config/base.yaml --profile config/conservative.yaml`
6. Inspect outputs:
   - `reports/backtest_summary.json`
   - `reports/trades.csv`
   - `reports/equity_curve.csv`
   - `reports/walk_forward_summary.json`
   - `reports/go_live_decision_report.json`
