# US Market Daily — 美股事件每日 Discord 推送

## 概述

每天自動抓取美股重要事件（Fed/FOMC 動態、重量級財報、經濟數據），格式化後推送到 Discord。

## 推送時間

| 台灣時間 | UTC | cron |
|----------|-----|------|
| 06:00    | 前一天 22:00 | `0 22 * * *` |
| 17:00    | 09:00 | `0 9 * * *` |

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
| `DISCORD_CHANNEL_ID` | `1496298887714046216` | Discord 頻道 ID（可覆寫給其他 profile 用） |

### 股票名單

在 `scripts/config.py` 的 `WATCHED_TICKERS` 中修改。

## 目錄結構

```
us-market-daily/
├── SKILL.md
├── scripts/
│   ├── fetch_events.py   # 資料抓取
│   ├── formatters.py     # Discord 訊息格式化
│   └── config.py         # 設定（股票名單、頻道 ID）
└── references/
    └── DISCORD_TEMPLATE.md
```

## 依賴

- Python 3.12+（使用 `/usr/bin/python3`）
- `yfinance`, `beautifulsoup4`, `lxml`, `feedparser`
- 統一裝在系統 Python 下，不使用 venv

## 測試

```bash
# 測試資料抓取
/usr/bin/python3 scripts/fetch_events.py

# 測試格式化輸出
/usr/bin/python3 -c "
import sys; sys.path.insert(0, 'scripts')
from fetch_events import fetch_all_events
from formatters import build_market_brief
print(build_market_brief(fetch_all_events()))
"
```

## cron job ID

- 早上（台灣 06:00）：`us-market-daily-morning`（`729a86ae3791`）
- 下午（台灣 17:00）：`us-market-daily-afternoon`（`4ec66aacf00c`）
