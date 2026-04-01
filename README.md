# anitshakya

## US100 Scalping Strategy (Pine Script v6)

**File:** `us100_scalping.pine`

A TradingView Pine Script v6 strategy for **US100 (Nasdaq)** scalping on **1-minute and 3-minute** charts.

### Strategy Summary

- Trend structure via **EMA 9 / EMA 21 / EMA 50**
- Momentum filters using **RSI (14)** and **MACD (12, 26, 9)** histogram crossovers
- Smart-money volume confirmation: `volume > 1.2 x SMA(volume, 20)`
- Volatility filter using **VIX activity** (avoid flat volatility)
- Confluence scoring model (0–100%, 20 points each for Trend, RSI, MACD, Volume, Volatility)
- Entries only during **New York open session (09:30–12:00 EST)** when score is `>= 75%`
- Risk controls:
  - Stop: **ATR(14) x 1.5** or fixed **15 points**
  - Target: **1:2 RR** or fixed **30 points**
  - Forced flat at **16:00 EST**
- Visuals: EMA plots + Buy/Sell `plotshape` signals when score threshold is met

### How to Use

1. Open TradingView and create a new Pine Script strategy.
2. Paste `us100_scalping.pine`.
3. Apply to **US100**, on **1m or 3m** timeframe.
4. Adjust stop/target and VIX settings via inputs.
