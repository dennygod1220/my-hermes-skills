# Indicator Vision Pitfalls — MNQ Trading

Vision analysis of TradingView screenshots frequently misreads indicator values.
This reference documents known failure modes and how to verify them.

## 1. DI Indicator (formerly 客製ADX)

**Renamed 2026-04-30** from 客製ADX → DI方向指標 because Vision repeatedly confused ADX and DI+.

### Vision failure mode

Vision sees the ADX main-line value (~28) and reports it as "DI+ = 28.41", when in fact:
- **ADX (white line)** is the composite trend-strength line (~28.41)
- **DI+ (green line)** and **DI- (red line)** are separate directional lines

### How to verify

Triangulate by color, not by number:
- Green text in the indicator panel → DI+
- Red text in the indicator panel → DI-
- White/yellow text → ADX (ignored by the user's strategy)
- The user's custom DI indicator hides the ADX label visually — the ADX line is plotted but not used

### Naming history

| File | Title | Notes |
|:----|:------|:------|
| `trading/indicators/di-indicator.md` | DI方向指標 | Current — diThresh param |
| (deleted) `客製ADX.md` | 客製ADX | Original — adxOver param, confusing name |

---

## 2. KDJ Calibration (MNQ-specific)

Standard KDJ thresholds (80/20) do NOT apply to MNQ futures.
This was empirically calibrated across multiple trading sessions.

| Signal | Standard | MNQ Actual |
|:-------|:---------|:-----------|
| Oversold | J < 20 | J < **0 ~ -5** |
| Overbought | J > 80 | J > **105** |
| Sweet spot | J 20-80 | J **50-85** ↗️ |

### Why it matters

Vision will flag J > 80 as "overbought" using standard thresholds.
If the user's J is at 96, that's still in the MNQ sweet/transition zone — NOT overbought yet.
**Always use MNQ-specific thresholds** when commenting on KDJ.

---

## 3. DI Gap Strength

The user's strategy uses DI gap (DI+ minus DI-) as a trend-strength filter:

| Gap | Meaning |
|:---:|:--------|
| > 10 | Directional trend — valid for 2-contract entry |
| 5-10 | Weak direction — 1 contract max |
| < 5 | Choppy / no direction — 0 or 1 contract |

Vision often skips the gap calculation entirely. **Always compute it manually** from the DI values.

---

## 4. J-Value Entry Timing Table (from Strategy)

| J Value | Phase | Action |
|:-------:|:------|:------:|
| 50-85 ↗️ | Sweet spot, fresh momentum | Normal entry |
| 20-50 | Mid-momentum | Enter but smaller targets |
| < 20 ↘️ | Momentum exhausted | WAIT — pattern may be stale |
| > 100 🚀 | Near exhaustion | Enter but tighten targets |

---

## 5. EMA Weak-Support Signal (Collapse Warning)

When **EMA10 - EMA30 < 10pt**, the fast/medium lines are too close — a single candle can break both, making the EMA structure unreliable as support.

Vision will still call EMA10 "support" — but when the gap is < 10pt, flag it as weakened support.
