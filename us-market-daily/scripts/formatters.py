"""
Discord 訊息格式化 — formatters.py
"""
import sys
sys.path.insert(0, "/root/.hermes/skills/my-hermes-skills/us-market-daily/scripts")
from config import WATCHED_TICKERS

# importance 數字 → emoji
_IMPORTANCE_EMOJI = {
    "High":   "🔴",
    "Medium": "🟡",
    "Low":    "⚪",
}

# time flag → 中文
_TIME_LABEL = {
    "BMO": "盤前",
    "AMC": "盤後",
    "N/A": "時間待定",
}


def format_fed_events(fed_events: list) -> str:
    """格式化 Fed / FOMC 事件 block"""
    if not fed_events:
        return ""

    lines = ["**🔵 聯準會動態**"]
    for e in fed_events:
        time_et = e.get("time_et", "")
        time_str = f"`{time_et} ET`" if time_et else ""
        event    = e.get("event", "")
        desc     = e.get("description", "")
        line = f"• **{event}**"
        if time_str:
            line += f" — {time_str}"
        if desc:
            line += f" — _{desc}_"
        lines.append(line)

    return "\n".join(lines) + "\n"


def format_earnings(earnings: list) -> str:
    """格式化財報 block（只顯示有實質數據的股票）"""
    if not earnings:
        return ""

    # 過濾掉完全沒有 eps 且沒有 revenue 的
    valid = [
        e for e in earnings
        if e.get("eps_estimate") is not None or e.get("revenue_estimate") is not None
    ]
    if not valid:
        return ""

    lines = ["**📊 今日財報**"]
    for e in valid:
        ticker = e.get("ticker", "")
        company = e.get("company", "")
        time_flag = _TIME_LABEL.get(e.get("time", ""), e.get("time", ""))
        eps = e.get("eps_estimate")
        rev = e.get("revenue_estimate")

        # 單行敘述
        label = f"__{ticker}__ ({company})" if company != ticker else f"__{ticker}__"
        if time_flag and time_flag != "N/A":
            label += f" [{time_flag}]"

        parts = []
        if eps is not None:
            parts.append(f"EPS 預估 **${eps:.2f}**")
        if rev is not None:
            parts.append(f"營收 **${rev:.1f}B**")
        detail = " / ".join(parts) if parts else "無預估數據"
        lines.append(f"• {label} — {detail}")

    return "\n".join(lines) + "\n"


def format_economic_data(econ_data: list) -> str:
    """格式化經濟數據 block"""
    if not econ_data:
        return ""

    lines = ["**📈 經濟數據發布**"]
    for e in econ_data:
        time_et = e.get("time_et", "")
        time_str = f"`{time_et} ET`" if time_et else "`全天`"
        event    = e.get("event", "")
        imp      = e.get("importance", "Low")
        emoji    = _IMPORTANCE_EMOJI.get(imp, "⚪")
        prev     = e.get("previous", "—")
        fcst     = e.get("forecast", "—")

        parts = []
        if prev and prev != "—":
            parts.append(f"前值: {prev}")
        if fcst and fcst != "—":
            parts.append(f"預期: {fcst}")
        detail = " / ".join(parts) if parts else ""

        line = f"{emoji} **{event}** — {time_str}"
        if detail:
            line += f"\n  └ {detail}"
        lines.append(line)

    return "\n".join(lines) + "\n"


def format_vix() -> str:
    """取得 VIX 恐慌指數（簡單版，不中斷流程）"""
    try:
        import yfinance as yf
        vix = yf.Ticker("^VIX")
        info = vix.info or {}
        price = info.get("regularMarketPrice") or info.get("previousClose")
        if price:
            return f"**⚡ 市場情緒**\n• VIX 恐慌指數: **{price:.2f}**\n"
    except Exception:
        pass
    return ""


def build_market_brief(events: dict) -> str:
    """
    組裝完整市場早報文字訊息。
    events = fetch_events() 回傳的 dict
    """
    date_str = events.get("date", "")

    # 格式化日期（2026-04-23 → 2026年4月23日）
    try:
        from datetime import datetime
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        date_display = dt.strftime("%Y年%m月%d日")
    except Exception:
        date_display = date_str

    blocks = [
        f"📅 **美股早報 — {date_display}**",
        "━━━━━━━━━━━━━━━━━━",
    ]

    fed    = events.get("fed_events", [])
    econ   = events.get("economic_data", [])
    earn   = events.get("earnings", [])

    fed_block    = format_fed_events(fed)
    earn_block   = format_earnings(earn)
    econ_block   = format_economic_data(econ)
    vix_block    = format_vix()

    # 如果三個 block 都空的，給一個提示
    if not (fed_block or earn_block or econ_block):
        blocks.append("_今日無重大市場事件。_")
    else:
        if fed_block:
            blocks.append(fed_block)
        if earn_block:
            blocks.append(earn_block)
        if econ_block:
            blocks.append(econ_block)
        if vix_block:
            blocks.append(vix_block)

    blocks.append("━━━━━━━━━━━━━━━━━━")
    blocks.append("_資料來源：finviz.com · yfinance_")

    return "\n".join(blocks)
