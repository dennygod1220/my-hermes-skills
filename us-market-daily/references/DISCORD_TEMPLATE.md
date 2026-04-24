# Discord 訊息格式範本

## 每日早報（台灣 06:00 / 17:00）

```
📅 **美股早報 — 2026年04月23日**
━━━━━━━━━━━━━━━━━━
🔵 聯準會動態
• **Fed Balance Sheet** — `04:30 ET` — _Central Bank Balance Sheet_

📊 今日財報
• __AAPL__ (Apple Inc.) [時間待定] — EPS 預估 $9.37 / 營收 $435.6B
• __MSFT__ (Microsoft Corporation) [時間待定] — EPS 預估 $18.90 / 營收 $305.4B
• __NVDA__ (NVIDIA Corporation) [時間待定] — EPS 預估 $11.24 / 營收 $215.9B
• __AMZN__ (Amazon.com, Inc.) [時間待定] — EPS 預估 $9.49 / 營收 $716.9B
• __META__ (Meta Platforms, Inc.) [時間待定] — EPS 預估 $35.86 / 營收 $201.0B
• __GOOGL__ (Alphabet Inc.) [時間待定] — EPS 預估 $13.48 / 營收 $402.8B
• __TSLA__ (Tesla, Inc.) [時間待定] — EPS 預估 $2.75 / 營收 $94.8B

📈 經濟數據發布
🟡 **Michigan Consumer Sentiment Final** — `22:00 ET`
  └ 前值: 53.3 / 預期: 47.6

⚡ 市場情緒
• VIX 恐慌指數: **19.13**

━━━━━━━━━━━━━━━━━━
_資料來源：finviz.com · yfinance_
```

## 格式說明

- 日期標題使用 `**粗體**`
- 各 section 使用 `**emoji 標題**`
- Fed 事件：粗體事件名稱 + ` 時間 ET` + 斜體分類
- 財報：股票代碼粗體 + 公司名稱 + [盤前/盤後] + EPS/營收
- 經濟數據：🟡重要性emoji + 粗體名稱 + 時間 + 前值/預期
- VIX：直接顯示數值
- footer：資料來源備註
