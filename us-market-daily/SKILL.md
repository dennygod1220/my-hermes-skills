---
name: us-market-daily
description: "US market events — daily Discord push of Fed/FOMC, earnings, economic data via finviz + yfinance. Absorbed finviz-calendar-scraper."
umbrella: true
absorbed: [finviz-calendar-scraper]
---

# US Market Daily — 美股事件每日 Discord 推送

## 概述

每天自動抓取美股重要事件（Fed/FOMC 動態、重量級財報、經濟數據），格式化後推送到 Discord。
支援兩種格式：
- **完整格式**（早報 06:00）：含 Fed 動態、財報預估、經濟數據表格、VIX 情緒指標
- **簡潔格式**（晚報 18:00）：僅今晚事件表格 + 本週重頭戲，一眼掃完

## 推送時間

| 台灣時間 | UTC | cron | 格式 |
|----------|-----|------|------|
| 06:00    | 前一天 22:00 | `0 22 * * *` | 完整 (build_market_brief) |
| 18:00    | 10:00 | `0 10 * * *` | 簡潔 (build_compact_brief) |

## 事件類型

- 🔵 **聯準會動態**：FOMC 會議、Fed 官員演講、央行資產負債表
- 📊 **重量級財報**：AAPL、MSFT、NVDA、AMZN、META、GOOGL、TSLA、SPY
- 📈 **經濟數據**：NFP、CPI、GDP、零售銷售、ISM、消費者信心（僅 Medium/High 重要性）

## 資料來源

- Fed / 經濟數據：[finviz.com](https://finviz.com/calendar.ashx)（從 HTML 嵌入式 JSON 解析）
- 財報 EPS：[yfinance](https://pypi.org/project/yfinance/)

## 設定

### 環境變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `DISCORD_CHANNEL_ID` | `1496787470652674199` | Discord 頻道 ID（可覆寫給其他 profile 用） |

### 股票名單

在 `scripts/config.py` 的 `WATCHED_TICKERS` 中修改。

## 目錄結構

```
us-market-daily/
├── SKILL.md
├── scripts/
│   ├── fetch_events.py       # 資料抓取
│   ├── formatters.py         # Discord 訊息格式化（含兩種格式函數）
│   ├── push_to_discord.py    # cron 專用：抓取+格式化+輸出到 stdout
│   └── config.py             # 設定（股票名單、頻道 ID）
└── references/
    └── DISCORD_TEMPLATE.md
```

## 格式化輸出

### 傍晚簡潔格式（--evening）

```
📅 **今晚（04/28 週二）**
| 時間 (台北) | 數據 | 預期 vs 前值 |
|------------|------|-------------|
| 07:00 | MBA 30-Year Mortgage Rate | 前值 6.35% |
| 08:30 | Durable Goods Orders Ex Transp MoM | 預期 0.4% ← 前值 0.8% ⚠️ |
| 08:30 | Durable Goods Orders MoM | 前值 -1.4%，預期 0.5% |
| 10:30 | EIA Crude Oil Stocks Change | 前值 1.925M |

🔥 **本週重頭戲：**
週四 04/30 → Core PCE Price Index MoM (8:30) + GDP Growth Rate QoQ Adv (8:30) + PCE Price Index YoY (8:30)
週五 05/01 → ISM Manufacturing Employment (10:00) + ISM Manufacturing PMI (10:00)

━━━━━━━━━━━━━━━━━━
_資料來源：finviz.com · yfinance_
```

### 預期 vs 前值 邏輯

- 只有前值 → `前值 X`
- 只有預期 → `預期 X`
- 兩者都有且預期顯著較差 → `預期 X ← 前值 Y ⚠️`
- 兩者都有但數值接近 → `前值 X，預期 Y`
- 都沒有 → `—`

### 時區轉換

- 所有事件時間先以美東時間（ET）儲存
- 顯示時自動轉換為台灣時間（ET + 12h，EDT 期間）
- 週間重頭戲按**台灣日期**分組（非 ET 日期）

## 依賴

- Python 3.12+（使用 `/usr/bin/python3`）
- `yfinance`, `beautifulsoup4`, `lxml`, `feedparser`
- 統一裝在系統 Python 下，不使用 venv

## 測試

```bash
# 測試資料抓取
cd /root/.hermes/profiles/stock_master/skills/my-hermes-skills/us-market-daily/scripts
/usr/bin/python3 fetch_events.py

# 測試完整格式輸出
/usr/bin/python3 push_to_discord.py

# 測試簡潔格式輸出（傍晚用）
/usr/bin/python3 push_to_discord.py --evening
```

## cron job 設定

建立 cron job 時，必須：
1. 將 `skills` 設為 `["my-hermes-skills/us-market-daily"]`
2. prompt 中指示 agent 先 `skill_view(name="my-hermes-skills/us-market-daily")` 載入 skill
3. 執行 `scripts/push_to_discord.py`（早報）或 `scripts/push_to_discord.py --evening`（晚報）
4. 將 stdout 輸出內容作為最終回應 — 系統會自動交付，**不需要**呼叫 `send_message` 工具

### 早報 prompt（06:00）
```
你是美股早報推送代理。請按照 us-market-daily skill 的完整流程執行：

1. 先載用 skill: skill_view(name="my-hermes-skills/us-market-daily")
2. 執行指令：
   cd /root/.hermes/profiles/stock_master/skills/my-hermes-skills/us-market-daily && /usr/bin/python3 scripts/push_to_discord.py
   抓取資料並以完整格式輸出
3. 將 stdout 輸出內容作為最終回應 — 系統會自動交付
```

### 晚報 prompt（18:00）
```
你是美股晚報推送代理。請按照 us-market-daily skill 的完整流程執行：

1. 先載用 skill: skill_view(name="my-hermes-skills/us-market-daily")
2. 執行指令：
   cd /root/.hermes/profiles/stock_master/skills/my-hermes-skills/us-market-daily && /usr/bin/python3 scripts/push_to_discord.py --evening
   抓取資料並以簡潔傍晚格式輸出
3. 將 stdout 輸出內容作為最終回應 — 系統會自動交付
```

cron job ID：
- 早上（台灣 06:00）：`07441461b201`（us-market-daily-06am）
- 下午（台灣 18:00）：`7c19b06fde75`（us-market-daily-06pm）

## 注意事項

- cron job 的 agent session 使用系統 Python（`/usr/bin/python3`），依賴已預裝
- `cronjob run` 動作可能不會立即執行，jobs 仍保持 scheduled 狀態
- Discord home channel ID: `1496787470652674199`（DM 頻道，使用 bare "discord" target 發送）
- 傍晚格式會自動過濾已過期的台灣時間事件，只顯示即將到來的
- 週間重頭戲會自動去重（相同 event name 只顯示一次）

## 資料來源：Finviz Calendar 解析

市場事件資料從 finviz.com 嵌入式 JSON 解析取得。詳細 extraction code、timezone handling 與 edge cases 請見 `references/finviz-extraction.md`。

### 關鍵注意事項

- **Timezone 陷阱（IJC 問題）**：Initial Jobless Claims 20:30 ET = 00:30 UTC+1d，早報時間可能跨 UTC 日
- **Fed 事件只能用 ticker whitelist**：`FDTR` + `UNITEDSTACENBANBALSH` 唯二，不能用字串比對 "Fed"
- **經濟數據 blacklist**：國債拍賣、區域 Fed 指數等 noise ticker 需過濾
- **重要性門檻**：經濟數據只看 importance >= 2（Fed 資產負債表例外）
- **JSON 解析失敗後備**：fallback 到 browser tool 直接從 HTML table 抓資料
