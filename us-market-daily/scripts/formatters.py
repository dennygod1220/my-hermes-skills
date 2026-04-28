"""
Discord 訊息格式化 — formatters.py
"""
import sys
import os
# Resolve the script directory relative to the skill root
_skill_dir = os.path.dirname(os.path.abspath(__file__))
if _skill_dir not in sys.path:
    sys.path.insert(0, _skill_dir)
from config import WATCHED_TICKERS
from datetime import datetime, timezone, timedelta
import re
from itertools import groupby

# ET → 台灣換算（EDT 期間 ET+12h = 台灣）
_TW_OFFSET = timedelta(hours=12)

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

# Day of week 中文
_DOW_CN = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]

# ═══════════════════════════════════════════════
#  事件名稱中英對照
# ═══════════════════════════════════════════════
_EVENT_CN = {
    # ── 聯準會 ──
    "Fed Interest Rate Decision":                      "FOMC利率決議",
    "Fed Press Conference":                            "鮑爾記者會",
    "Fed Balance Sheet":                               "Fed資產負債表",
    "FOMC Minutes":                                    "FOMC會議紀錄",
    "FOMC Member":                                     "Fed官員談話",
    "Fed Chair Speech":                                "Fed主席談話",
    "Federal Budget Balance":                          "聯邦預算",

    # ── 就業 ──
    "Nonfarm Payrolls":                                "非農就業",
    "Non Farm Payrolls":                               "非農就業",
    "Unemployment Rate":                               "失業率",
    "Initial Jobless Claims":                          "初領失業金",
    "Jobless Claims":                                   "初領失業金",
    "Continuing Jobless Claims":                       "續領失業金",
    "ADP Employment Change":                           "ADP小非農",
    "JOLTS Job Openings":                              "JOLTS職位空缺",
    "Employment Cost Index QoQ":                       "就業成本指數",
    "Employment Cost - Wages QoQ":                     "就業成本-薪資",
    "Employment Cost - Benefits QoQ":                  "就業成本-福利",
    "Average Hourly Earnings":                         "平均時薪",

    # ── 通膨 ──
    "CPI":                                              "CPI消費者物價指數",
    "Core CPI":                                        "核心CPI",
    "PPI":                                              "PPI生產者物價",
    "Core PPI":                                        "核心PPI",
    "PCE Price Index MoM":                              "PCE物價指數月率",
    "PCE Price Index YoY":                              "PCE物價指數年率",
    "Core PCE Price Index MoM":                        "核心PCE物價月率",
    "Core PCE Price Index YoY":                        "核心PCE物價年率",
    "Personal Income MoM":                             "個人收入月率",
    "Personal Spending MoM":                           "個人支出月率",

    # ── GDP ──
    "GDP Growth Rate QoQ Adv":                         "GDP季率初值",
    "GDP Growth Rate QoQ":                              "GDP季率",
    "GDP Price Index QoQ Adv":                         "GDP物價指數初值",
    "GDP Price Index QoQ":                              "GDP物價指數",

    # ── 消費 & 信心 ──
    "CB Consumer Confidence":                          "CB消費者信心",
    "Michigan Consumer Sentiment":                     "密大消費者信心",
    "Michigan Consumer Expectations":                  "密大消費者預期",
    "Michigan Current Conditions":                     "密大現況指數",
    "Retail Sales MoM":                                "零售銷售月率",
    "Retail Sales Ex Autos MoM":                       "零售銷售(不含汽車)",
    "Consumer Credit":                                 "消費者信貸",
    "Consumer Confidence":                             "消費者信心",

    # ── 製造業 ──
    "ISM Manufacturing PMI":                           "ISM製造業PMI",
    "ISM Manufacturing Employment":                    "ISM製造業就業",
    "ISM Services PMI":                                "ISM服務業PMI",
    "ISM Non-Manufacturing PMI":                       "ISM非製造業PMI",
    "Industrial Production MoM":                       "工業生產月率",
    "Factory Orders MoM":                              "工廠訂單月率",
    "Durable Goods Orders MoM":                        "耐久財訂單月率",
    "Durable Goods Orders Ex Transp MoM":              "耐久財訂單(不含運輸)",
    "Capacity Utilization":                            "產能利用率",

    # ── 房地產 ──
    "Building Permits":                                "建築許可",
    "Building Permits MoM Prel":                       "建築許可月率初值",
    "Building Permits Prel":                           "建築許可初值",
    "Housing Starts":                                  "新屋開工",
    "Housing Starts MoM":                              "新屋開工月率",
    "Existing Home Sales":                             "成屋銷售",
    "New Home Sales":                                  "新屋銷售",
    "S&P/Case-Shiller Home Price YoY":                 "S&P/Case-Shiller房價年率",

    # ── 貿易 ──
    "Goods Trade Balance Adv":                         "商品貿易帳初值",
    "Trade Balance":                                   "貿易收支",

    # ── 其他重要 ──
    "Treasury STRATEGY":                                "財政部季度再融資",

    # ── 區域 Fed ──
    "Empire State Manufacturing Index":                "紐約Fed製造業",
    "Philadelphia Fed Manufacturing Index":            "費城Fed製造業",
    "Richmond Fed Manufacturing Index":                "里奇蒙Fed製造業",
    "Kansas Fed Manufacturing Index":                  "堪薩斯Fed製造業",
    "Chicago PMI":                                     "芝加哥PMI",
}


def _translate_event(name: str) -> str:
    """
    將英文事件名稱翻譯為中文。
    若無對應翻譯則保留原文。
    """
    # 先試完整名稱
    if name in _EVENT_CN:
        return _EVENT_CN[name]

    # 試試大寫對照
    upper = name.upper()
    for eng, cn in _EVENT_CN.items():
        if eng.upper() == upper:
            return cn

    # 試試部分匹配（ex: "Housing Starts" → "新屋開工"）
    # 優先最長匹配
    candidates = []
    for eng, cn in sorted(_EVENT_CN.items(), key=lambda x: -len(x[0])):
        if eng in name:
            candidates.append(cn)
    if candidates:
        # 用最長匹配的翻譯
        return candidates[0]

    return name


def _et_to_taiwan(et_time_str: str, et_date_str: str) -> tuple:
    """
    將美東時間 (ET) 轉換為台灣時間。
    回傳 (tw_date_str, tw_time_str) 例如 ("4/29", "08:30")
    """
    try:
        dt_et = datetime.strptime(f"{et_date_str} {et_time_str}", "%Y-%m-%d %H:%M")
        dt_tw = dt_et + _TW_OFFSET
        return (dt_tw.strftime("%m/%d"), dt_tw.strftime("%H:%M"))
    except Exception:
        return (et_date_str[5:], et_time_str)


def _et_to_taiwan_time_only(et_time_str: str, et_date_str: str) -> str:
    """僅回傳台灣時間字串"""
    _, tw_time = _et_to_taiwan(et_time_str, et_date_str)
    return tw_time


def _et_taiwan_dt(et_time_str: str, et_date_str: str) -> datetime:
    """回傳完整的台灣 datetime 物件"""
    try:
        dt_et = datetime.strptime(f"{et_date_str} {et_time_str}", "%Y-%m-%d %H:%M")
        return dt_et + _TW_OFFSET
    except Exception:
        return None


def _et_date_to_dow(date_str: str) -> str:
    """將 YYYY-MM-DD 轉為週幾"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return _DOW_CN[dt.weekday()]
    except Exception:
        return ""


def _et_date_to_short(date_str: str) -> str:
    """YYYY-MM-DD → MM/DD"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%m/%d")
    except Exception:
        return date_str[5:]


def _is_high_impact(event: dict) -> bool:
    """判斷是否為高度影響市場的事件（基於重要性或關鍵字）"""
    if event.get("importance") == "High":
        return True
    name = event.get("event", "").upper()
    high_impact_kw = [
        "FOMC", "FED", "INTEREST RATE", "NFP", "NONFARM",
        "CPI", "PCE", "GDP", "ISM MANUFACTURING", "ISM SERVICES",
        "RETAIL SALES", "JOLTS", "PAYROLLS", "UNEMPLOYMENT",
        "CONSUMER CONFIDENCE", "DURABLE GOODS",
        "CASE-SHILLER", "BUILDING PERMIT", "HOUSING START",
        "FOMC MINUTES", "BALANCE SHEET",
    ]
    for kw in high_impact_kw:
        if kw in name:
            return True
    return False


def _try_parse_num(raw: str) -> float:
    """嘗試將 finviz 的字串數值轉為 float，例如 '1.2%', '$50B', '5M'"""
    try:
        s = raw.strip().replace("%", "").replace("$", "").replace(",", "")
        s = s.replace("M", "").replace("B", "").replace("T", "")
        return float(s)
    except (ValueError, TypeError, AttributeError):
        return None


def _is_worsening(prev: str, forecast: str) -> bool:
    """
    判斷預期是否比前值差（對經濟數據而言，數值下降 = 惡化）。
    回傳 True 表示預期惡化。
    """
    p = _try_parse_num(prev)
    f = _try_parse_num(forecast)
    if p is None or f is None:
        return False
    # 如果差距超過 5% 且預期更低 = 惡化
    if abs(p) > 0.01 and (p - f) / abs(p) > 0.05:
        return True
    return False


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


# ═══════════════════════════════════════════════════════════════
#  舊版完整格式（保留給早報 06:00 使用）
# ═══════════════════════════════════════════════════════════════

def build_market_brief(events: dict) -> str:
    """
    組裝完整市場早報文字訊息。
    events = fetch_all_events() 回傳的 dict
    """
    date_str = events.get("date", "")

    try:
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
    weekly = events.get("weekly_data", [])
    earn   = events.get("earnings", [])

    fed_block    = format_fed_events(fed)
    earn_block   = format_earnings(earn)
    tonight_block = build_tonight_table_old(econ, date_str)
    weekly_block = _build_weekly_highlights_old(weekly, date_str)
    vix_block    = format_vix()

    if not (fed_block or earn_block or tonight_block or weekly_block):
        blocks.append("_今日無重大市場事件。_\n")
        blocks.append(vix_block)
    else:
        if fed_block:
            blocks.append(fed_block)
        if earn_block:
            blocks.append(earn_block)
        if tonight_block:
            blocks.append(tonight_block)
        else:
            blocks.append("_今晚無重大經濟數據發布。_\n")
        if weekly_block:
            blocks.append(weekly_block)
        if vix_block:
            blocks.append(vix_block)

    blocks.append("━━━━━━━━━━━━━━━━━━")
    blocks.append("_資料來源：finviz.com · yfinance_")

    return "\n".join(blocks)


def build_tonight_table_old(today_events: list, today_date_et: str) -> str:
    """舊版「📅 今晚」表格（保留向後相容）"""
    if not today_events:
        return ""

    dow = _et_date_to_dow(today_date_et)
    date_short = _et_date_to_short(today_date_et)

    lines = [f"**📅 今晚（{date_short} {dow}）**"]
    lines.append("時間(台北)│數據│預期 vs 前值")
    lines.append("─────────┼────┼────────────")

    for e in today_events:
        event_date_et = e.get("date_et", today_date_et) or today_date_et
        tw_time = _et_to_taiwan_time_only(e.get("time_et", ""), event_date_et)
        event_name = e.get("event", "")
        prev = e.get("previous", "")
        fcst = e.get("forecast", "")

        parts = []
        if prev:
            parts.append(f"前值 {prev}")
        if fcst:
            arrow = " ← " if parts else ""
            parts.append(f"預期{arrow}{fcst}")
        detail = "／".join(parts) if parts else "—"

        imp = e.get("importance", "Low")
        emoji = _IMPORTANCE_EMOJI.get(imp, "⚪")

        suffix = ""
        if prev and fcst:
            try:
                prev_f = _try_parse_num(prev)
                fcst_f = _try_parse_num(fcst)
                if prev_f is not None and fcst_f is not None and abs(prev_f) > 0.01:
                    diff = abs(prev_f - fcst_f) / abs(prev_f)
                    if diff > 0.05:
                        suffix = " ⚠️"
            except (ValueError, TypeError):
                pass

        lines.append(f"`{tw_time}`│{emoji}{event_name}{suffix}│{detail}")

    return "\n".join(lines) + "\n"


def _build_weekly_highlights_old(weekly_data: list, today_date_et: str) -> str:
    """舊版「🔥 本週重頭戲」"""
    if not weekly_data:
        return ""

    future_high = []
    for e in weekly_data:
        date_et = e.get("date_et", "")
        if not date_et or date_et <= today_date_et:
            continue
        if not _is_high_impact(e):
            continue
        future_high.append(e)

    if not future_high:
        return ""

    future_high.sort(key=lambda x: x.get("date_et", ""))

    lines = ["**🔥 本週重頭戲**"]

    for date_et, group in groupby(future_high, key=lambda x: x.get("date_et", "")):
        events = list(group)
        dow = _et_date_to_dow(date_et)
        date_short = _et_date_to_short(date_et)

        event_names = []
        for e in events:
            tw_time = _et_to_taiwan_time_only(e.get("time_et", ""), date_et)
            name = e.get("event", "")
            event_names.append(f"{name} (`{tw_time}`)" if tw_time else name)

        line = f"• **{dow} {date_short}** → {', '.join(event_names)}"
        lines.append(line)

    return "\n".join(lines) + "\n"


# ═══════════════════════════════════════════════════════════════
#  新版簡潔格式（傍晚 18:00 推送專用）
# ═══════════════════════════════════════════════════════════════

def build_compact_brief(events: dict) -> str:
    """
    簡潔傍晚格式 — 一眼看完今晚事件 + 本週重頭戲。

    輸出範例：
      📅 今晚（4/28 週二）
      | 時間 (台北) | 數據 | 預期 vs 前值 |
      |------------|------|-------------|
      | 21:00 | S&P/Case-Shiller Home Price Index YoY | 前值 +1.2% |
      | 22:00 | CB Consumer Confidence | 預期 89 ← 前值 91.8 ⚠️ |
      | 22:00 | Richmond Fed Manufacturing Index | 前值 0，預期 2 |

      🔥 本週重頭戲：
      週三 4/29 → Fed Interest Rate Decision (凌晨2:00) + FOMC Press Conference
      週四 4/30 → GDP QoQ (20:30) + Initial Jobless Claims (20:30)
      週五 5/1 → ISM Manufacturing PMI (22:00)
    """
    date_str = events.get("date", "")

    # ── 時段判斷 ──
    now_utc = datetime.now(timezone.utc)
    tw_hour = (now_utc.hour + 8) % 24
    is_evening = tw_hour >= 12  # 台灣中午過後 = 傍晚推送

    blocks = []

    # ── 今晚表格 ──
    econ = events.get("economic_data", [])
    fed_today = events.get("fed_events", [])
    tonight_table = _build_compact_tonight_table(econ, fed_today, date_str, is_evening)
    if tonight_table:
        blocks.append(tonight_table)

    # ── 本週重頭戲 ──
    weekly = events.get("weekly_data", [])
    weekly_block = _build_compact_weekly_highlights(weekly, date_str)
    if weekly_block:
        blocks.append(weekly_block)

    blocks.append("━━━━━━━━━━━━━━━━━━")
    blocks.append("_資料來源：finviz.com · yfinance_")

    return "\n\n".join(blocks)


def _is_market_moving(event: dict) -> bool:
    """
    判斷事件是否會影響 MNQ / MES（美國指數期貨）。

    規則：
    - finviz 重要性為 High (3) → 保留
    - 事件名稱包含下列關鍵字 → 保留
    - 其他（區域性/商品特有/不重要）→ 過濾掉
    """
    imp = event.get("importance", "")
    if imp == "High":
        return True

    name = event.get("event", "").upper()

    # 一定會影響大盤的關鍵事件
    major_kw = [
        "NONFARM", "PAYROLLS", "UNEMPLOYMENT RATE",
        "CPI", "PCE", "PPI",
        "GDP GROWTH", "GDP PRICE",
        "FOMC", "FED INTEREST RATE", "FED BALANCE SHEET",
        "FOMC MINUTES",
        "ISM MANUFACTURING", "ISM SERVICES", "ISM NON-MANUFACTURING",
        "RETAIL SALES",
        "CONSUMER CONFIDENCE",
        "JOLTS",
        "DURABLE GOODS ORDERS",
        "INITIAL JOBLESS CLAIMS", "JOBLESS CLAIMS",
        "INDUSTRIAL PRODUCTION",
        "MICHIGAN CONSUMER SENTIMENT",
        "ADP EMPLOYMENT",
        "BUILDING PERMITS",
        "EXISTING HOME SALES", "NEW HOME SALES",
        "PERSONAL INCOME", "PERSONAL SPENDING",
        "CONSUMER CREDIT",
        "EMPLOYMENT COST",
        "FACTORY ORDERS",
        "TREASURY STRATEGY", "QUARTERLY REFUNDING",
        "BUDGET",
    ]

    for kw in major_kw:
        if kw in name:
            return True

    return False


def _build_compact_tonight_table(
    today_events: list, fed_events: list, today_date_et: str, is_evening: bool
) -> str:
    """
    簡潔版今晚/今日事件表格 — 只顯示會影響 MNQ/MES 的市場事件。

    - 自動合併 finviz 拆成兩行的同一事件（前值/預期合併）
    - 過濾掉區域性/商品特有/低重要性數據
    - 加入 Fed 事件（FOMC、資產負債表）
    - is_evening=True → 標題用「今晚」，且只顯示尚未發生的事件
    """
    if not today_events and not fed_events:
        return ""

    # 現在台灣時間
    now_tw = datetime.utcnow() + _TW_OFFSET

    # ── 步驟 1：收集 + 過濾事件 ──
    # 從經濟數據中只留會影響大盤的
    filtered = []
    for e in today_events:
        if not _is_market_moving(e):
            continue
        e = dict(e)  # copy 以免改到原始資料
        e["event"] = _translate_event(e.get("event", ""))
        filtered.append(e)

    # 加入 Fed 事件
    for fe in fed_events:
        fe_time = fe.get("time_et", "")
        fe_event = fe.get("event", "")
        if not fe_time or not fe_event:
            continue
        # 幫 Fed event 加注「Fed」前綴以資識別
        display_name = _translate_event(fe_event)
        if not fe_event.upper().startswith("FED") and not "FOMC" in fe_event.upper():
            display_name = f"Fed {display_name}"
        filtered.append({
            "date_et":     today_date_et,
            "time_et":     fe_time,
            "event":       display_name,
            "importance":  "High",
            "previous":    "",
            "forecast":    "",
            "_is_fed":     True,
        })

    if not filtered:
        return ""

    # 日期頭
    try:
        dt = datetime.strptime(today_date_et, "%Y-%m-%d")
        date_short = dt.strftime("%m/%d")
        dow = _DOW_CN[dt.weekday()]
    except Exception:
        date_short = today_date_et[5:]
        dow = ""

    # 排序（先時間再 name）
    filtered.sort(key=lambda x: (x.get("time_et", ""), x.get("event", "")))

    # ── 步驟 2：去重 — 合併同時間同名事件的 prev/forecast ──
    deduped = {}
    for e in filtered:
        event_date_et = e.get("date_et", today_date_et) or today_date_et
        key = (e.get("time_et", ""), e.get("event", ""))
        tw_dt = _et_taiwan_dt(e.get("time_et", ""), event_date_et)

        # 過期過濾
        if is_evening and tw_dt and tw_dt <= now_tw:
            continue

        if key not in deduped:
            deduped[key] = {
                "tw_dt": tw_dt,
                "event": e.get("event", ""),
                "previous": "",
                "forecast": "",
            }
        # 合併 prev/forecast
        p = (e.get("previous") or "").strip()
        f = (e.get("forecast") or "").strip()
        if p and not deduped[key]["previous"]:
            deduped[key]["previous"] = p
        if f and not deduped[key]["forecast"]:
            deduped[key]["forecast"] = f

    if not deduped:
        return "📅 **今晚無重大經濟數據發布**"

    # 排序輸出
    sorted_rows = sorted(deduped.values(), key=lambda x: (x["tw_dt"] if x["tw_dt"] else datetime.min, x["event"]))

    heading = "今晚" if is_evening else "今日"
    lines = [f"📅 **{heading}（{date_short} {dow}）**"]
    lines.append("| 時間 (台北) | 數據 | 預期 vs 前值 |")
    lines.append("|------------|------|-------------|")

    for row in sorted_rows:
        tw_time = row["tw_dt"].strftime("%H:%M") if row["tw_dt"] else "--:--"
        detail = _format_exp_vs_prev(row["previous"], row["forecast"])
        lines.append(f"| {tw_time} | {row['event']} | {detail} |")

    return "\n".join(lines)


def _format_exp_vs_prev(prev: str, fcst: str) -> str:
    """
    格式化「預期 vs 前值」欄位。

    邏輯：
    - 只有前值 → 「前值 X」
    - 只有預期 → 「預期 X」
    - 兩者都有：
      - 預期比前值差很多 → 「預期 X ← 前值 Y ⚠️」
      - 一般情況 → 「前值 X，預期 Y」
    - 都沒有 → 「—」
    """
    prev = prev.strip()
    fcst = fcst.strip()

    if prev and fcst:
        if _is_worsening(prev, fcst):
            return f"預期 {fcst} ← 前值 {prev} ⚠️"
        else:
            return f"前值 {prev}，預期 {fcst}"
    elif prev:
        return f"前值 {prev}"
    elif fcst:
        return f"預期 {fcst}"
    else:
        return "—"


def _build_compact_weekly_highlights(weekly_data: list, today_date_et: str) -> str:
    """
    簡潔版本週重頭戲 — 用**台灣日期**分組，一行一天，事件用 + 連接。

    每個事件的 ET 時間會先轉成台灣時間，再按台灣日期分組顯示。
    已過期的台灣時間事件會自動過濾掉。
    """
    if not weekly_data:
        return ""

    # 將每個事件轉為台灣 datetime，只留會影響 MNQ/MES 且未來的事件
    tw_events = []
    for e in weekly_data:
        date_et = e.get("date_et", "")
        time_et = e.get("time_et", "")
        if not date_et or not time_et:
            continue
        if not _is_market_moving(e):
            continue
        # 排除今天 ET 正在發生的事件（已在今晚表格中）
        if date_et <= today_date_et:
            continue
        tw_dt = _et_taiwan_dt(time_et, date_et)
        if tw_dt is None:
            continue
        tw_events.append({
            "tw_date": tw_dt.strftime("%Y-%m-%d"),
            "tw_dt": tw_dt,
            "event": _translate_event(e.get("event", "")),
        })

    if not tw_events:
        return ""

    # 依台灣 datetime 排序
    tw_events.sort(key=lambda x: x["tw_dt"])

    lines = ["🔥 **本週重頭戲：**"]

    for tw_date, group in groupby(tw_events, key=lambda x: x["tw_date"]):
        events = list(group)
        first_dt = events[0]["tw_dt"]
        try:
            day_label = f"{_DOW_CN[first_dt.weekday()]} {first_dt.strftime('%m/%d')}"
        except Exception:
            day_label = tw_date[5:]

        # 去重：相同 event name 只顯示一次
        seen_events = set()
        event_parts = []
        for e in events:
            name = e["event"]
            if name in seen_events:
                continue
            seen_events.add(name)
            h = e["tw_dt"].hour
            m = e["tw_dt"].strftime("%M")
            if h < 6:
                tw_ts = f"凌晨{h}:{m}"
            else:
                tw_ts = f"{h}:{m}"
            event_parts.append(f"{name} ({tw_ts})")

        lines.append(f"{day_label} → {' + '.join(event_parts)}")

    return "\n".join(lines)
