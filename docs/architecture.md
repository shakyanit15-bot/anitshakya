# System Architecture (Mad Turtle XAUUSD)

## Component Diagram
- **Market Data Layer**: MT5 bars export (M5 base; M15/H1 derived by resampling)
- **Research Layer**: Feature engineering + triple barrier labeling
- **Model Layer**: Ensemble training + calibration + serialized artifacts
- **Signal Layer**: Confidence-thresholded BUY/SELL/NO_TRADE + dormant-mode filters
- **Risk Layer**: Position sizing, spread/slippage checks, kill-switches
- **Execution Layer**: MQL5 EA order management and exits
- **Validation Layer**: Backtest, walk-forward, sensitivity, go-live report
- **Monitoring Layer**: CSV/JSON logs and incident playbook

## Explicit Data Flow
1. MT5 historical/live bars arrive in CSV
2. `data_loader` normalizes timestamps and schema
3. `feature_generator` computes trend/vol/candle/regime/multi-TF features
4. `labeling` creates leakage-safe triple barrier classes
5. `train_ensemble` fits calibrated multi-class ensemble
6. `signal_bridge` emits latest signal + confidence + SL points
7. EA ingests signal, runs hard risk filters and policy gates
8. EA sends order with mandatory SL and max one open position
9. EA exits by counter-signal / trailing-stop / max-hold
10. Execution and controls are logged for audit and retraining feedback
