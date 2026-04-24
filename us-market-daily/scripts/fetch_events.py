#!/usr/bin/env python3
"""
美股事件每日抓取 — fetch_events.py
資料來源：
  - Fed/FOMC 事件 + 經濟數據：finviz.com（從 HTML 嵌入式 JSON 解析）
  - 財報 EPS 預估：yfinance
"""
import sys
sys.path.insert(0, "/root/.hermes/skills/my-hermes-skills/us-market-daily/scripts")
from config import WATCHED_TICKERS, LOG_FILE
import requests
import yfinance as yf
from datetime import datetime, date, timezone
import logging
import time
import re
import json

# 設定日誌
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

try:
    from zoneinfo import ZoneInfo
    NY_ZONE = ZoneInfo("America/New_York")
except Exception:
    NY_ZONE = None


def utc_to_et(utc_dt: datetime) -> datetime:
    """UTC datetime → 美東時區（ET）"""
    if NY_ZONE is not None:
        return utc_dt.astimezone(NY_ZONE)
    # fallback: rough offset
    return utc_dt.astimezone(timezone.utc)


def get_financial_date_et() -> str:
    """取得今天美國 Eastern Time 的日期字串 (YYYY-MM-DD)"""
    try:
        now_et = utc_to_et(datetime.now(timezone.utc))
        return now_et.strftime("%Y-%m-%d")
    except Exception as e:
        logger.exception("get_financial_date_et failed: %s", e)
        return datetime.utcnow().strftime("%Y-%m-%d")


def _extract_finviz_entries(html: str) -> list:
    """
    從 finviz.com HTML 中取出嵌入式 JSON entries 陣列。
    finviz 把行事曆資料埋在 <script> 標籤的 JSON 中：
      {"data":{"initialDateFrom":"...","entries":[...]}}
    """
    # 找 "entries":[
    start = html.find('"entries":[')
    if start == -1:
        logger.error("_extract_finviz_entries: entries key not found in HTML")
        return []

    # 手動對括號計數，找到匹配的 ]
    depth = 0
    i = start + len('"entries":[')
    while i < len(html):
        ch = html[i]
        if ch == '[':
            depth += 1
        elif ch == ']':
            if depth == 0:
                break
            depth -= 1
        i += 1

    json_str = '[' + html[start + len('"entries":['):i] + ']'
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.exception("_extract_finviz_entries: JSON parse failed: %s", e)
        return []


def _parse_finviz_entry(entry: dict) -> dict:
    """
    將一個 finviz entry dict 標準化，回傳：
      {date_et, time_et, ticker, event, category, importance, previous, forecast, actual, dt_et}
    """
    raw_dt = entry.get("date", "")
    try:
        dt_utc = datetime.fromisoformat(raw_dt.replace("Z", "+00:00"))
        dt_et = utc_to_et(dt_utc)
        date_str = dt_et.strftime("%Y-%m-%d")
        time_str = dt_et.strftime("%H:%M")
    except Exception:
        dt_et = None
        date_str = raw_dt[:10] if raw_dt else ""
        time_str = ""

    return {
        "date_et":   date_str,
        "time_et":   time_str,
        "ticker":    entry.get("ticker", ""),
        "event":     entry.get("event", ""),
        "category":  entry.get("category", ""),
        "importance": entry.get("importance", 0),   # 1/2/3
        "previous":  entry.get("previous") or "",
        "forecast": entry.get("forecast") or "",
        "actual":   entry.get("actual") or "",
        "dt_et":    dt_et,
    }


def _date_in_window(dt_et: datetime, target_date: str, include_prior_evening: bool = True) -> bool:
    """
    判斷一個美東時間是否屬於目標日期的顯示窗口。
    - 目標日期本身的全天事件
    - 目標日期前一天 16:00 ET 之後（即美股盤後到午夜的 events）
    """
    target = datetime.strptime(target_date, "%Y-%m-%d").date()
    event_date = dt_et.date()

    if event_date == target:
        return True
    if include_prior_evening:
        # 前一天 16:00 ET 之後的事件（盤後/午夜場）也算進來
        prior_date = target - __import__('datetime').timedelta(days=1)
        if event_date == prior_date and dt_et.hour >= 16:
            return True
    return False


def fetch_fed_events(date_str: str) -> list:
    """
    抓取 Fed 官方政策相關事件（嚴格定義）。
    ticker=FDTR：Fed 政策聲明/官員演講
    ticker=UNITEDSTACENBANBALSH：Fed 資產負債表（市場高度關注）
    """
    url = "https://finviz.com/calendar.ashx"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        time.sleep(1)
    except Exception as e:
        logger.exception("fetch_fed_events: HTTP request failed: %s", e)
        return []

    entries = _extract_finviz_entries(resp.text)
    # Fed 相關 ticker
    FED_TICKERS = {"FDTR", "UNITEDSTACENBANBALSH"}
    results = []
    for e in entries:
        parsed = _parse_finviz_entry(e)
        ticker = parsed["ticker"]
        dt_et  = parsed.get("dt_et")

        if ticker not in FED_TICKERS:
            continue
        if dt_et is None:
            continue
        if not _date_in_window(dt_et, date_str):
            continue

        results.append({
            "time_et":     parsed["time_et"],
            "event":       parsed["event"],
            "description": parsed["category"],
        })

    results.sort(key=lambda x: x["time_et"])
    logger.info("fetch_fed_events: found %d Fed events for %s", len(results), date_str)
    return results


def fetch_economic_data(date_str: str) -> list:
    """
    抓取美國重要經濟數據發布，只回傳指定日期窗口的項目。
    窗口：目標日期全天 + 前一天 16:00 ET 之後。
    排除：國債標售、區域Fed指數（Kansas、Chicago等以Fed為名但非政策）、
          Redbook、每週ADP、續領失業金。
    只保留 Medium(2) 或 High(3) 重要性的項目。
    """
    url = "https://finviz.com/calendar.ashx"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        time.sleep(1)
    except Exception as e:
        logger.exception("fetch_economic_data: HTTP request failed: %s", e)
        return []

    entries = _extract_finviz_entries(resp.text)
    results = []

    # Fed Balance Sheet → 已移至 fetch_fed_events
    # 嚴格的黑名單 — 這些不是真正的「宏觀經濟數據」
    skipped_tickers = {
        # Fed 相關（已由 fetch_fed_events 處理）
        "FDTR",
        "UNITEDSTACENBANBALSH",
        # 國債標售
        "UNITEDSTA3MONBILYIE",
        "UNITEDSTA6MONBILYIE",
        "USA4WEEBILYIE",
        "USA8WBY",
        "USA15YMR",
        "USA3YMR",
        "USA5YTY",
        # 區域 Fed 指數（非政策事件，干擾太多）
        "USAKFCI",
        "UNITEDSTAKFMI",
        "UNITEDSTACONJOBCLA",
        # 其他干擾
        "UNITEDSTAREDIND",
        "USAAECW",
        "UNITEDSTANATGASSTOCH",
    }

    for e in entries:
        parsed = _parse_finviz_entry(e)
        ticker = parsed["ticker"]
        event  = parsed["event"]
        dt_et  = parsed.get("dt_et")
        imp    = parsed["importance"]

        if ticker in skipped_tickers:
            continue
        if dt_et is None:
            continue
        if not _date_in_window(dt_et, date_str):
            continue

        # Fed Balance Sheet 永遠保留（imp=1 也留）
        is_fed_data = ticker == "UNITEDSTACENBANBALSH"
        if not is_fed_data and imp < 2:
            continue

        importance_label = {1: "Low", 2: "Medium", 3: "High"}.get(imp, "Low")

        results.append({
            "time_et":     parsed["time_et"],
            "event":       parsed["event"],
            "importance":  importance_label,
            "previous":    parsed["previous"],
            "forecast":    parsed["forecast"],
        })

    results.sort(key=lambda x: x["time_et"])
    logger.info("fetch_economic_data: found %d items for %s", len(results), date_str)
    return results


def fetch_earnings(tickers: list) -> list:
    """
    用 yfinance 抓財報日期與 EPS 預估。
    回傳：[{ticker, company, time (BMO/AMC/N/A), eps_estimate, revenue_estimate}]
    """
    results = []
    for tkr in tickers:
        try:
            t = yf.Ticker(tkr)
            info = {}
            try:
                info = t.info or {}
            except Exception:
                pass

            company = (info.get("shortName") or info.get("longName") or tkr)

            # EPS 預估（forward EPS 最準）
            eps_est = None
            for key in ("epsForward", "forwardEps", "trailingEps", "epsCurrentYear"):
                if key in info and info[key] is not None:
                    try:
                        eps_est = round(float(info[key]), 2)
                        break
                    except Exception:
                        continue

            # 營收（十億美元）
            revenue_est = None
            for key in ("totalRevenue", "revenue", "revenueAverage"):
                val = info.get(key)
                if val is not None:
                    try:
                        revenue_est = round(float(val) / 1e9, 2)
                        break
                    except Exception:
                        continue

            # 嘗試從 calendar 抓財報時間來判斷 BMO/AMC
            time_flag = "N/A"
            try:
                cal = t.calendar
                cal_str = str(cal)
                # 找 datetime pattern
                m = re.search(r"(20\d{2}-\d{2}-\d{2}T\d{2}:\d{2})", cal_str)
                if m:
                    dt_str = m.group(1)
                    try:
                        dt_utc = datetime.fromisoformat(dt_str)
                        if dt_utc.tzinfo is None:
                            dt_utc = dt_utc.replace(tzinfo=timezone.utc)
                        dt_et = utc_to_et(dt_utc)
                        h = dt_et.hour
                        time_flag = "BMO" if h < 9 else ("AMC" if h >= 16 else "N/A")
                    except Exception:
                        pass
            except Exception:
                pass

            results.append({
                "ticker":          tkr,
                "company":         company,
                "time":            time_flag,
                "eps_estimate":    eps_est,
                "revenue_estimate": revenue_est,
            })
            logger.debug("fetch_earnings: %s OK — EPS=%s, rev=%s, time=%s",
                         tkr, eps_est, revenue_est, time_flag)
            time.sleep(0.4)

        except Exception as e:
            logger.exception("fetch_earnings: failed for %s: %s", tkr, e)
            results.append({
                "ticker":          tkr,
                "company":         tkr,
                "time":            "N/A",
                "eps_estimate":    None,
                "revenue_estimate": None,
            })
    return results


def fetch_all_events() -> dict:
    """整合三個來源，回傳統一格式"""
    date_str = get_financial_date_et()
    fed    = fetch_fed_events(date_str)
    econ   = fetch_economic_data(date_str)
    earn   = fetch_earnings(WATCHED_TICKERS)

    return {
        "date":          date_str,
        "fed_events":    fed,
        "economic_data": econ,
        "earnings":      earn,
    }


if __name__ == "__main__":
    result = fetch_all_events()
    # 友善輸出
    print(json.dumps(result, indent=2, ensure_ascii=False))
