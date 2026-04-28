# Discord 訊息格式範本

## 傍晚簡潔格式（台灣 18:00）

```
📅 **今晚（04/28 週二）**
| 時間 (台北) | 數據 | 預期 vs 前值 |
|------------|------|-------------|
| 07:00 | MBA 30-Year Mortgage Rate | 前值 6.35% |
| 08:30 | Building Permits Prel | 前值 1.386M |
| 08:30 | Durable Goods Orders Ex Transp MoM | 預期 0.4% ← 前值 0.8% ⚠️ |
| 08:30 | Durable Goods Orders MoM | 前值 -1.4%，預期 0.5% |
| 08:30 | Housing Starts | 前值 1.487M |
| 10:30 | EIA Crude Oil Stocks Change | 前值 1.925M |

🔥 **本週重頭戲：**
週四 04/30 → Core PCE Price Index MoM (8:30) + GDP Growth Rate QoQ Adv (8:30) + Personal Spending MoM (8:30)
週五 05/01 → ISM Manufacturing PMI (10:00)

━━━━━━━━━━━━━━━━━━
_資料來源：finviz.com · yfinance_
```

## 完整早報格式（台灣 06:00）

```
📅 **美股早報 — 2026年04月23日**
━━━━━━━━━━━━━━━━━━
🔵 聯準會動態
• **Fed Balance Sheet** — `04:30 ET` — _Central Bank Balance Sheet_

📊 今日財報
• __AAPL__ (Apple Inc.) — EPS 預估 $9.37 / 營收 $435.6B
• __MSFT__ (Microsoft Corporation) — EPS 預估 $18.90 / 營收 $305.4B

📈 經濟數據發布
🟡 **Michigan Consumer Sentiment Final** — `22:00 ET`
  └ 前值: 53.3 / 預期: 47.6

⚡ 市場情緒
• VIX 恐慌指數: **19.13**

━━━━━━━━━━━━━━━━━━
_資料來源：finviz.com · yfinance_
```

## 格式說明

### 傍晚格式
- `|` pipe table 格式，Discord 直接顯示為純文字表格
- 時間欄為台灣時間（自動從 ET 轉換）
- ⚠️ 標記表示預期顯著惡化（比前值低 >5%）
- 本週重頭戲按台灣日期分組，已去重
- 已過期的事件自動過濾不顯示

### 早報格式
- 日期標題使用 `**粗體**`
- 各 section 使用 `**emoji 標題**`
- Fed 事件：粗體事件名稱 + ` 時間 ET` + 斜體分類
- 財報：股票代碼加底線 + 公司名稱 + [盤前/盤後] + EPS/營收
- 經濟數據：🟡重要性emoji + 粗體名稱 + 時間 + 前值/預期
- VIX：直接顯示數值
- footer：資料來源備註
