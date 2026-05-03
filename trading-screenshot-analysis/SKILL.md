---
name: trading-screenshot-analysis
category: trading
description: Analyze TradingView chart screenshots captured by the tv-chart-analyzer Chrome Extension — reads screenshot + JSON metadata, runs Vision analysis, returns structured trade review, and records completed trades to the wiki
version: 1.3.0
author: Hermes Agent
metadata:
  hermes:
    tags: [Trading, Vision, Analysis, Chrome-Extension, Screenshot]
    related_skills: [us-market-daily]

---

# Skill: Trading Screenshot Analysis

## When to Use

Use this skill when:
- The user says `trading-snap`, `分析截圖`, `analyze screenshot`, or requests a trade review
- A new PNG+JSON pair appears in the screenshots directory from the tv-chart-analyzer Chrome Extension
- The user wants Vision-based technical analysis of a TradingView chart
- The user says "幫我記錄到知識庫", "幫我覆盤和記錄", or asks to record a completed trade to the wiki

## Trigger Keywords

`trading-snap`, `分析截圖`, `analyze screenshot`, `chart review`, `截圖分析`, `trade review`, `交易日記`, `記錄交易`, `trade-log`, `session journal`

## File Naming — Two Sources

### Chrome Extension (tv_ prefix)

Screenshots captured via the **tv-chart-analyzer Chrome Extension** use:
- `tv_YYYY-MM-DD_HH-mm-ss.png` + matching `.json` metadata
- Saved to `$TRADING_SCREENSHOTS_DIR` (or `Downloads/` before import)

### Discord Attachments (screenshot_ prefix)

Screenshots shared via **Discord chat** use:
- `screenshot-*.png` (named by Discord's CDN)
- Saved to **wiki root** (`$WIKI_PATH/`) by the Discord integration
- **No JSON metadata** — all data comes from Vision analysis alone
- Must be **manually moved** to `trading/screenshots/` after analysis and recording

## Setup

The `TRADING_SCREENSHOTS_DIR` env var points to the screenshot directory. It's set in `~/.hermes/.env`:
```
export TRADING_SCREENSHOTS_DIR="/mnt/c/Users/denny/Downloads/Hermes_Workspace/tv-chart-analyzer/screenshots"
```

The wiki trading session journal template is at:
```
$WIKI_PATH/trading/templates/session-journal.md
```

Format rules for session journals are in `$WIKI_PATH/SCHEMA.md` (see "交易日記格式規範" section).

## Workflow

### Step 0: Import from Downloads (if needed)

Due to Chrome 147+ restrictions (see `references/chrome-extension-architecture.md` for the MV3 workaround details), screenshot files save to `Downloads/` instead of the screenshots directory. Before analyzing, import them:

```bash
python3 /mnt/c/Users/denny/Downloads/Hermes_Workspace/tv-chart-analyzer/hermes-watcher.py --import
```

`--import` also syncs a copy to wiki `trading/screenshots/` for `![[tv_YYYY-MM-DD_HH-MM-SS.png]]`引用.

If manual wiki archiving is needed:
```bash
python3 /mnt/c/Users/denny/Downloads/Hermes_Workspace/tv-chart-analyzer/hermes-watcher.py --archive-wiki
```

### Step 0.b: Handle Discord-attached screenshots (screenshot_*)

When screenshots arrive via Discord chat (not the Chrome Extension):

1. **Find the file** — it's at `$WIKI_PATH/screenshot-*.png` (wiki root)
2. **Run Vision** with a targeted prompt asking for ALL specific indicator values (see Step 3)
3. **Analyze against strategy** — manually compute DI gap, check KDJ vs MNQ thresholds, list all 5 entry conditions
4. **Do NOT move files yet** — wait until trade is recorded (see Step 7b)
5. **No JSON exists** for these — all analysis relies on Vision output alone. Cross-check with multiple Vision questions if uncertain.

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

Use `vision_analyze` on the screenshot PNG with a targeted prompt asking for exact numeric values:

```
I need specific numbers from this TradingView MNQ chart. Please provide:
1. KDJ: exact K, D, J values
2. ADX DI+/DI-: exact values and the gap (DI+ minus DI-)
3. EMA10, EMA30, EMA60: exact price levels
4. Current exact price and time (including candle countdown timer)
5. Any visible signal arrows (blue up / red down) on the chart
6. Any visible candlestick patterns at the current bar
```

### Step 4: Cross-Reference with User's Strategy (Wiki)

Before evaluating the trade, load the user's published strategy from their wiki:

```
$WIKI_PATH/trading/strategy/mnq-scalping-system.md
```

Also load the KDJ+DI combo indicator if the user may have used it:

```
$WIKI_PATH/trading/indicators/kdj-di-combo.md
```

Cross-reference the trade against the strategy's **entry conditions**, **position sizing rules**, and **exit plan**:

- Does the trade satisfy all the strategy's entry filters? List each condition and pass/fail.
- Does the position size match the strategy's sizing decision table?
- Is the SL/TP placement consistent with strategy rules (e.g., Train Mode 🚃, TP1 lock-in)?
- If conditions are partially met (< 4/5), note the deviation and whether it was a conscious choice (e.g., EMA10 support bounce entry) vs. a mistake.

The MNQ-specific indicator thresholds are documented in `references/indicator-vision-pitfalls.md`.

### Step 4.b: Compute DI Values Manually from Vision

⚡ Vision frequently confuses ADX and DI+ values (see Pitfalls). Always manually verify:
- DI+ is the **green** line value, DI- is the **red** line
- ADX is the **white/yellow** line — it is NOT DI+
- Compute DI gap = DI+ − DI- yourself
- Compare DI+ against the white threshold line (default 25) — don't trust Vision's word on this

### Step 5: Cross-Reference with Trade Parameters

Compare Vision analysis against the user's trade plan:
- Does the chart support the direction (long/short)?
- Is the entry price reasonable relative to support/resistance?
- Are SL/TP levels well-placed?
- Any visible risks the user may have missed?

### Step 6: Format Response — Trade Review

Structure the reply as:

```
## {Entry/Exit} Analysis @ {price}

📊 Conditions Check (做多五條件 or 做空五條件):
   [Table: condition | actual | pass/fail]

⚠️ Risk Check:
   [DI gap, J value stage, EMA structure]

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
When the user provides an entry or exit screenshot, always:
1. List all 5 strategy conditions in a table
2. Compute DI gap explicitly
3. Note J value stage vs MNQ thresholds (sweet spot 50-85, caution >100, oversold <0)
4. Give a clear go/no-go opinion

### Step 7: Record Trade to Wiki (Post-Session)

When the user says "幫我記錄到知識庫", "幫我覆盤和記錄", or after a session ends, do ALL of the following:

#### Step 7a: Update `trading/trade-log.yaml`

Add a new entry under `trades:` with fields:
- `id`: `"YYYY-MM-DD-NNN"` (sequential per day, e.g., `"2026-04-30-003"`)
- `date`, `session` (morning/night), `direction` (long/short)
- `contracts`, `entry_price`, `entry_time`, `exit_time`
- `exits[]`: array of `{price, reason, pnl}`
- `pnl_total`: sum of all exit pnls
- `entry_reason`: concise technical justification referencing indicator values
- `lesson_tags`: array of tag strings (reusable patterns like `"kdj-adx-di20-pattern"`, `"sl-to-breakeven-plus"`, `"entry-deviation-from-strategy"`)

Scroll to the end of the existing YAML file and append the new entry in alphabetical/sequential id order.

#### Step 7b: Move Discord Screenshots to `trading/screenshots/`

After recording, move any `screenshot-*.png` files from wiki root to `trading/screenshots/`:
```bash
mkdir -p $WIKI_PATH/trading/screenshots
mv $WIKI_PATH/screenshot-*.png $WIKI_PATH/trading/screenshots/
```

#### Step 7c: Write Session Journal

Use the template at `$WIKI_PATH/trading/templates/session-journal.md`. Follow this **exact section order per trade** (from SCHEMA.md):

1. **交易標題** — `## 交易一（方向×口數）：PnL + 表情符號`
2. **進場明細表** — 方向、口數、進場價格與時間、出場價格與時間、損益、持倉時間
3. **進場邏輯** — KDJ交叉狀態/數值、ADX DI+/DI- 數值與 gap、EMA 結構、市場情境
4. **📸 進場截圖** — `![[trading/screenshots/xxx.png]]` + 一句描述
5. **持倉過程截圖**（如有）— 中間追蹤的截圖，按時間順序排列
6. **出場分析** — 出場原因、Train Mode 條件對照表（🅰️🅱️🅲🅳）
7. **📸 出場截圖** — `![[trading/screenshots/xxx.png]]` + 一句描述
8. **覆盤** — 做對的 ✅ / 可以改進的 ⚠️ / 教訓 💡

After writing the session journal, **verify screenshot paths** — Discord screenshots should be `trading/screenshots/screenshot-*.png`, NOT `screenshot-*.png` (wiki root). Update the `sources:` frontmatter and any `![[ ]]` references accordingly.

Then update:
- `$WIKI_PATH/trading/index.md` — add session entry to the session list
- `$WIKI_PATH/log.md` — append a create entry
- Cross-link from the same-day morning/night counterpart if applicable

## Environment

The `TRADING_SCREENSHOTS_DIR` env var must be set. If it's missing, default to:
```
/mnt/c/Users/denny/Downloads/Hermes_Workspace/tv-chart-analyzer/screenshots
```

## Pitfalls

- ⚠️ Vision can misread exact price digits — cross-reference with JSON metadata
- ⚠️ **ADX/DI confusion**: Vision frequently reports the ADX main-line value as DI+ or DI−, especially when the DI lines and ADX line share similar numeric ranges (20-30). Always verify DI+/DI− values against the colored legend (green=+DI, red=−DI) — the white ADX line is a separate indicator. See `references/indicator-vision-pitfalls.md` for MNQ-specific thresholds.
- ⚠️ **KDJ threshold pitfall**: Vision uses standard 80/20 overbought/oversold thresholds — MNQ uses J < 0 / J > 105. Vision calling J=96 "overbought" is WRONG for MNQ.
- ⚠️ **DI gap is your friend**: Vision rarely computes DI+ minus DI−. Always compute the gap manually — it's a core strategy filter (gap > 10 = directional, < 5 = chop).
- ⚠️ Due to Chrome 147+ limitations, files download to `Downloads/` root, not `screenshots/`. Always run `--import` first to move them.
- ⚠️ No finviz calendar data here — that's handled by a separate cron/skill
- ⚠️ Screenshots only exist if the Extension popup was used — no data if user hasn't captured yet
- ⚠️ If `--import` finds nothing, try `--latest` directly — it searches both screenshots/ and Downloads/
- ⚠️ **Extension popup blocks SL display** — When the user says they set an SL but you can't see it in the screenshot, the popup may overlay it. Trust their word, don't assume no SL was set.
- ⚠️ **Entry hesitation signal** — When the user asks "should I wait for X before entering?" during a screenshot review, the answer is always "wait." Hesitation means conditions aren't mature.
- ⚠️ **Post-big-win bias** — After a successful trade (especially a comeback from loss), the user is more likely to consider marginal setups. Discourage entering unless the chart shows clear signals.
- ⚠️ **Multi-contract net loss trap** — When user closes 1 contract for a profit but leaves the 2nd with a wide SL, the total can still be negative. Always calculate net scenarios and push for breakeven SL after partial close.
- ⚠️ **SL inside EMA cluster** — If EMAs are within <5pt of each other, placing SL inside that cluster is risky. Move SL below the slowest EMA.
- ⚠️ **Consecutive screenshot delay** — Between user's "I entered" message and the next screenshot, several minutes may pass. Re-import and re-analyze on each "trading-snap" call.
- ⚠️ **User may change position size between mentions** — Always confirm contract count when the user says they "entered" or "closed".
- ⚠️ **Discord screenshots live at wiki root** — `screenshot-*.png` files land in `$WIKI_PATH/`, NOT `trading/screenshots/`. Always move them after recording and update paths.
- ⚠️ **No metadata for Discord screenshots** — unlike Chrome Extension screenshots, there's no `.json` file. Cross-reference Vision's readings with multiple questions to catch misreads.
- ⚠️ **Mid-candle snapshot trap** — When analyzing a user's entry, the screenshot may show a partially-formed candle. Indicator values on an incomplete candle can differ from what the user saw at entry. Always note the candle timer.
- ⚠️ **Screenshot path order of operations** — Write the session journal with correct paths on the first write. The patch tool's fuzzy matching can corrupt surrounding content if you try to fix paths later.
- ⚠️ **Session journal section order is fixed** — Do not rearrange. The order (entry logic → entry screenshot → in-trade screenshots → exit analysis → exit screenshot → review) is the user's preference.
- ⚠️ **Always update trade-log.yaml** — It's the machine-parsable record. Don't skip it even if the user only asks for a "session journal".
