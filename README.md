# anitshakya

## BTC/USD Silver Bullet Strategy (Pine Script v6)

**File:** `btc_silver_bullet.pine`

A quantitative Pine Script v6 strategy for **BTC/USD on a 1-minute chart**, implementing the ICT Silver Bullet concept.

---

### Strategy Logic

| # | Component | Detail |
|---|-----------|--------|
| 1 | **Market Bias** | Fetches the 15-minute 50 EMA (`request.security`, `lookahead_off`). Longs are only permitted while price is above the EMA; Shorts only while below. |
| 2 | **Liquidity Sweep** | Detects a wick beyond the previous session high (bearish) or low (bullish) followed by a close back inside the range. Session anchor is configurable: **Midnight** (full prior day) or **8:30 AM New York** (prior RTH open). |
| 3 | **MSS + Displacement** | After a sweep, waits for a strong full-bodied candle (body ≥ 60 % of range) that closes through the most-recent swing high (long) or swing low (short), confirming a Market Structure Shift. |
| 4 | **Fair Value Gap (FVG)** | Identifies a three-bar imbalance created during the displacement candle. Places a **limit entry at the 50 % midpoint** of the gap (confirmed retest). |
| 5 | **Time Filter** | All entries are restricted to the **Silver Bullet window: 10:00 AM – 10:59 AM New York Time** (`nyHour == 10`). Pending setups are cancelled when the window closes. |
| 6 | **Stop Loss** | **1.5 × ATR(14)** below (long) or above (short) the entry price. |
| 7 | **Take Profit** | Fixed **2:1 Risk-to-Reward** ratio relative to the stop distance. |
| 8 | **Break-Even** | Stop is moved to the entry price once price travels **1:1 RR** in favour. |
| 9 | **Backtest Integrity** | `barmerge.lookahead_off` on all `request.security()` calls; no future data leakage. |

---

### Visual Overlays

- 🟠 **15-min 50 EMA** – bias reference line
- 🔴 **Prev Session High** – potential liquidity level (step line)
- 🟢 **Prev Session Low**  – potential liquidity level (step line)
- 🟣 **Bear FVG Mid** / 🟢 **Bull FVG Mid** – active entry levels (dots)
- 🔵 **Silver Bullet background** – shaded blue when the time window is active
- Labels on each trade showing Entry, SL, and TP prices

---

### How to Use

1. Open **TradingView** and create a new Pine Script indicator/strategy.
2. Paste the contents of `btc_silver_bullet.pine`.
3. Apply to **BTCUSD**, **1-minute** timeframe.
4. Adjust inputs as needed (session anchor, ATR multiplier, RR ratio, etc.).
5. Run the Strategy Tester to review backtest results.