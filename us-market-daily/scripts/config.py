import os

# =============================================================================
# 美股事件每日推送 — 設定檔
# =============================================================================
# 給其他 profile 用時，只需設定以下環境變數即可覆寫，不需要改這支程式碼。
#
# 覆寫變數：
#   DISCORD_CHANNEL_ID   — Discord 頻道 ID（預設：你的個人頻道）
#   WATCHED_TICKERS      — 逗號分隔的股票代碼列表
#                         （預設：見下方列表）
# =============================================================================

# 追蹤的股票名單（僅真正撼動 S&P 500 的巨頭）
WATCHED_TICKERS = [
    "AAPL",   # Apple
    "MSFT",   # Microsoft
    "NVDA",   # NVIDIA
    "AMZN",   # Amazon
    "META",   # Meta
    "GOOGL",  # Alphabet (Google)
    "TSLA",   # Tesla
    "SPY",    # S&P 500 ETF（市場總指標）
]

# 讀取環境變數，可被環境變數覆寫
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "1496298887714046216")

# 日誌檔案路徑
LOG_FILE = "/tmp/us_market_daily.log"

# 市場假日（美股休市日，推播時略過）
US_MARKET_HOLIDAYS = [
    "2026-01-01",   # New Year's Day
    "2026-01-19",   # MLK Day
    "2026-02-16",   # Presidents Day
    "2026-04-10",   # Good Friday
    "2026-05-25",   # Memorial Day
    "2026-07-03",   # Independence Day (observed)
    "2026-09-07",   # Labor Day
    "2026-11-26",   # Thanksgiving
    "2026-12-25",   # Christmas
]
