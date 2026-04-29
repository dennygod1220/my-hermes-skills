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

### Step 5b: Live Position Management (when user reports an active trade)

After initial analysis (Step 1-5a), the user may report entering a trade. This starts a live position management loop across multiple screenshots:

**Phase A — Entry Confirmation:**
- User says "I entered X contracts at Y price, direction Z"
- Assess entry quality: is price near EMA support/resistance? Is entry within reasonable range of current price?
- Calculate initial R:R: suggested SL placement relative to EMA cluster, suggested TP targets
- Flag if SL is too tight for 3-min chart noise — typical SL needs 10-25pt room depending on EMA spread
- Flag if chasing (entering after big move) vs. pullback entry — pullbacks are preferred
- Provide 2-3 SL placement options (tight/medium/conservative) with trade-offs for each
- **⚠️ Exit monitoring — structural thesis break**: Throughout the position's life, track whether the EMA structure that justified the entry is intact. If the entry thesis was "price above all EMAs → long" and price later breaks below ALL three EMAs, the thesis is invalidated. **Advise manual exit before hard SL** — the thesis break IS the exit signal; the hard SL is just a backup. Know the specific structural thesis behind each entry so you can detect its invalidation.

**Phase B — SL Adjustment:**
- User adjusts SL — confirm new level is technically sound
- Recalculate R:R with new SL
- Check SL against: EMA levels, VRVP high-volume nodes, recent swing lows/highs
- Warn if SL sits inside an EMA cluster (<5pt spread between EMAs = weak wall, SL needs more room)
- Example analysis: "Fast EMA 27,483 / Mid EMA 27,477 / Your SL 27,474.5 → below the cluster, sound placement"

**Phase C — Partial Profit-Taking:**
- User reports closing 1 contract (e.g., "I closed 1 at X")
- Confirm PnL on closed contract: `(exit - entry) × points value` — note points gained
- Update remaining position: 1 contract left, recalculate risk
- **Strongly recommend moving remaining SL to breakeven** — don't let the remaining contract turn a winning trade into a net loss
- Alternative: move SL to just below nearest EMA (technical trailing)

**Phase D — Remaining Position Management:**
- Track remaining contract: entry, current SL, current price
- Provide ongoing trailing SL options aligned with EMAs as price moves
- Advise on final exit: indicator exhaustion (PPO cross, KDJ J-value overbought), price rejection at resistance
- Know when to call it: if momentum indicators are extremely overbought (KDJ J>105, Stoch RSI>90) and price stalling at resistance, recommend taking the remaining profit

**Multi-Contract R:R Template:**

```
Entry: 27,490.5 (2 contracts)
Contract 1: closed at 27,499.5 → +9 pts ✅
Contract 2: still open, SL at 27,474.5 → risking -16 pts

Net scenarios:
  - Both SL hits: +9 - 16 = -7 pts ❌ (worst case, avoidable by moving SL to breakeven)
  - Both TP1 hits: +9 + 9 = +18 pts ✅
  - TP1 then TP2 runs: +9 + 44.5 = +53.5 pts 🚀
```

**Psychological Coaching (embedded throughout):**
- Post-SL-hit cooldown: don't re-enter for 15-30 min (from mnq-scalping-framework)
- Post-win bias: user is more likely to consider marginal setups after a win — discourage
- Hesitation = wait: if user asks "should I wait for X?" the answer is always "wait"
- Partial win > potential loss: moving SL to breakeven after first contract closed prevents a winning trade from becoming a loss

### Step 6: Post-Trade Knowledge Base Logging (if user requests)

When the user says "幫我寫交易紀錄", "記到知識庫", "save to wiki" or similar after a trade concludes:

> **Wiki root** is `WIKI_PATH` from `.env` → `/mnt/c/Users/denny/Downloads/SillyTavern/koboldcpp-config/AI_Brain`
> **Screenshots** are already synced to `WIKI/trading/screenshots/` by the `--import` step.

#### 6a. Create or update the session file

- File: `WIKI/trading/sessions/YYYY-MM-DD-mnq-{session}.md` (session = `morning` or `night`)
- **If a file already exists** (e.g. adding a second trade to an existing session), read it first with `read_file`, then rewrite the full file to include all trades.
- YAML frontmatter: `title`, `date`, `product: MNQ1!`, `timeframe`, `pnl` (final total for the session), `session: morning/night`, `tags: [trading, mnq, session]`, `sources` (list of screenshot filenames)
- For **multi-trade sessions**, calculate total session PnL: `trade1_pnl + trade2_pnl = session_pnl`
- Trade details per trade: entry price, direction, size, stop loss, take profit, result in points ($ value optional)
- Review sections per trade: ✅ What went right, ⚠️ What could improve, 💡 Lessons learned
- Include a **total day PnL** section at the end combining all sessions (morning + night):
  ```
  早盤：+37點 ✅
  夜盤：+16.25點 ✅
  ────────────────
  全日：+53.25點 💪
  ```
- Reference screenshots via `![[tv_YYYY-MM-DD_HH-mm-ss.png]]`
- Screenshots already imported by `--import` are auto-synced to wiki — `WIKI_PATH/trading/screenshots/`

#### 6b. (Optional) Create journal entry for reusable lessons

- In `WIKI/trading/journal/{slug}.md`
- Single principle with concrete example from today's trade
- Frontmatter: `title`, `created`, `updated`, `type: learning`, `tags: [trading, learning, trap, mnq]`
- Reference the session file in `sources` frontmatter

#### 6c. Update indices

1. **`WIKI/trading/index.md`** — add new session / journal entries, bump `updated` date
2. **`WIKI/index.md`** — add to 📈 Trading section, increment total page count, bump `updated` date
3. **`WIKI/log.md`** — append log entries for each action (create/update session, create journal, update indices)

#### 6d. Conventions

- lowercase-hyphen filenames, YAML frontmatter (title/created/updated/type/tags/sources), [[wikilinks]]
- Update index.md and log.md on EVERY change (create/update/delete)
- Read SCHEMA.md first if unsure about structure (`WIKI_PATH/SCHEMA.md`)
- For updates to existing session files: re-read the file first, then rewrite with added trades

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
- ⚠️ **Extension popup blocks SL display** — When the user says they set an SL but you can't see it in the screenshot, the popup may overlay it. Trust their word, don't assume no SL was set.
- ⚠️ **Entry hesitation signal** — When the user asks "should I wait for X before entering?" during a screenshot review, the answer is always "wait." Hesitation means conditions aren't mature. Entering while hesitant produces weak entries that tend to get stopped out.
- ⚠️ **Post-big-win bias** — After a successful trade (especially a comeback from loss), the user is more likely to consider marginal setups. Discourage entering unless the chart shows clear, non-ambiguous signals.
- ⚠️ **Multi-contract net loss trap** — When user closes 1 contract for a profit but leaves the 2nd with a wide SL, the total can still be negative. Always calculate net scenarios and push for breakeven SL after partial close.
- ⚠️ **SL inside EMA cluster** — If EMAs are within <5pt of each other, placing SL inside that cluster is risky because price can breach all EMAs easily. Move SL below the slowest EMA.
- ⚠️ **Consecutive screenshot delay** — Between user's "I entered" message and the next screenshot, several minutes may pass. Don't assume the chart is identical — re-import and re-analyze on each "trading-snap" call.
- ⚠️ **User may change position size between mentions** — Always confirm contract count when the user says they "entered" or "closed" — don't assume the count from a prior message.
