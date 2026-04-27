---
name: trading-screenshot-analysis
category: trading
description: Analyze TradingView chart screenshots captured by the tv-chart-analyzer Chrome Extension — reads screenshot + JSON metadata, runs Vision analysis, returns structured trade review
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [Trading, Vision, Analysis, Chrome-Extension, Screenshot]
    related_skills: [tradingview-chrome-extension-vision, us-market-daily]

---

# Skill: Trading Screenshot Analysis

## When to Use

Use this skill when:
- The user says `trading-snap`, "分析截圖", "analyze screenshot", or requests a trade review
- A new PNG+JSON pair appears in the screenshots directory from the tv-chart-analyzer Chrome Extension
- The user wants Vision-based technical analysis of a TradingView chart

## Trigger Keywords

`trading-snap`, `分析截圖`, `analyze screenshot`, `chart review`, `截圖分析`, `trade review`

## File Naming

Screenshots are named `tv_YYYY-MM-DD_HH-mm-ss.png` with a matching `tv_YYYY-MM-DD_HH-mm-ss.json`. Always look for `tv_` prefix when searching for screenshots.

## Setup

The `TRADING_SCREENSHOTS_DIR` env var points to the screenshot directory. It's set in `~/.hermes/.env`:
```
export TRADING_SCREENSHOTS_DIR="/mnt/c/Users/denny/Downloads/Hermes_Workspace/tv-chart-analyzer/screenshots"
```

## Workflow

### Step 0: Import from Downloads (if needed)

Due to Chrome 147+ restrictions, screenshot files save to `Downloads/` instead of the screenshots directory. Before analyzing, import them:

```bash
python3 /mnt/c/Users/denny/Downloads/Hermes_Workspace/tv-chart-analyzer/hermes-watcher.py --import
```

### Step 1: Get Latest Screenshot + Metadata

```bash
python3 /mnt/c/Users/denny/Downloads/Hermes_Workspace/tv-chart-analyzer/hermes-watcher.py --latest
```

This outputs the symbol, price, direction, SL/TP, and indicator values from the JSON metadata, along with the PNG path.

### Step 2: Extract JSON Path

Read the JSON metadata file (paired with the PNG) to get structured data:
- `symbol`, `price`, `changePercent`
- `trade.direction` (long/short), `trade.entryPrice`, `trade.stopLoss`, `trade.takeProfit`
- `trade.notes`
- `indicators` (VRVP, EMA 20/30/60, KDJ, PPO, Stoch RSI)

### Step 3: Vision Analysis

Use `vision_analyze` on the screenshot PNG with a prompt like:
```
Analyze this TradingView chart for:
1. Candlestick pattern identification (bullish/bearish engulfing, doji, hammer, etc.)
2. Key support and resistance levels
3. Trend direction and strength
4. Any visible chart patterns (head and shoulders, double top/bottom, triangles, flags)
5. Volume analysis if visible
6. Overall sentiment
```

### Step 4: Cross-Reference with Trade Parameters

Compare Vision analysis against the user's trade plan:
- Does the chart support the direction (long/short)?
- Is the entry price reasonable relative to support/resistance?
- Are SL/TP levels well-placed?
- Any visible risks the user may have missed?

### Step 5: Format Response

Structure the reply as:

```
📸 Pattern Analysis:
   [Pattern type, trendline notes, key S/R levels]

📊 Indicator Confirmation:
   [MA position, RSI state, volume context]

⚠️ Risk Check:
   [Chart risks, time considerations]

🟢 Summary: [bias + confidence + recommendation]
```

## Environment

The `TRADING_SCREENSHOTS_DIR` env var must be set. If it's missing, default to:
```
/mnt/c/Users/denny/Downloads/Hermes_Workspace/tv-chart-analyzer/screenshots
```

## Pitfalls

- ⚠️ Vision can misread exact price digits — cross-reference with JSON metadata
- ⚠️ Due to Chrome 147+ limitations, files download to `Downloads/` root, not `screenshots/`. Always run `--import` first to move them.
- ⚠️ No finviz calendar data here — that's handled by a separate cron/skill
- ⚠️ Screenshots only exist if the Extension popup was used — no data if user hasn't captured yet
- ⚠️ If `--import` finds nothing, try `--latest` directly — it searches both screenshots/ and Downloads/
