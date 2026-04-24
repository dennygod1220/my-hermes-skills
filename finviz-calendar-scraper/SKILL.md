---
name: finviz-calendar-scraper
category: data-science
description: Scrape finviz.com calendar for US stock market events — earnings, Fed/FOMC, economic data. Extracts embedded JSON from HTML, handles UTC/ET timezone crossover.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Finviz, Web-Scraping, Financial-Data, Timezone, Python]
    related_skills: [reddit-ai-monitor]
prerequisites:
  commands: []
  env_vars: []
---

# finviz Calendar Scraper

Scrape US stock market events from finviz.com calendar — earnings, Fed/FOMC, economic data — and handle the embedded JSON + timezone edge cases that make this source tricky.

## Trigger Conditions

- "抓 finviz 行事曆" / "scrape finviz calendar"
- "美股 Fed 事件" / "finviz Fed events"
- "finviz HTML JSON" / "parse finviz embedded JSON"

## Data Source

**URL**: `https://finviz.com/calendar.ashx`

finviz.com embeds its entire calendar as a JSON array inside a `<script>` tag:
```html
<script>
  window.fc_data = {"data":{"initialDateFrom":"...","entries":[...]}}
</script>
```

It is NOT an AJAX API — the data is in the HTML on first load. This makes it scrapable without Selenium.

## Core Extraction Pattern

```python
import requests
import json
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def _extract_finviz_entries(html: str) -> list:
    """
    Find 'entries' JSON array in finviz HTML and return as a Python list.
    Uses bracket-counting to find the matching ] for the array.
    """
    start = html.find('"entries":[')
    if start == -1:
        return []

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
    return json.loads(json_str)
```

## Standardizing Entries

```python
from datetime import datetime, timezone

def _parse_finviz_entry(entry: dict) -> dict:
    raw_dt = entry.get("date", "")  # ISO format UTC, e.g. "2026-04-23T08:30:00Z"
    dt_utc = datetime.fromisoformat(raw_dt.replace("Z", "+00:00"))
    dt_et = dt_utc.astimezone(ZoneInfo("America/New_York"))

    return {
        "date_et":   dt_et.strftime("%Y-%m-%d"),
        "time_et":   dt_et.strftime("%H:%M"),
        "ticker":    entry.get("ticker", ""),
        "event":     entry.get("event", ""),
        "category":  entry.get("category", ""),
        "importance": entry.get("importance", 0),  # 1=Low, 2=Medium, 3=High
        "previous":  entry.get("previous") or "",
        "forecast":  entry.get("forecast") or "",
        "actual":    entry.get("actual") or "",
        "dt_et":     dt_et,
    }
```

## Critical: Timezone Crossover — The IJC Problem

**The Problem**: Initial Jobless Claims (IJC) publishes at 20:30 ET. At 20:30 ET = 00:30 UTC the next day. If your cron runs at Taiwan 06:00 (UTC 22:00 the previous day), the UTC day has already rolled over but the ET day hasn't. finviz uses ET dates as keys, so IJC gets filed under the previous ET date — but your date filter sees it as "tomorrow" and drops it.

**The Solution**: Expand the date window to include events from the evening before:

```python
from datetime import datetime, timedelta

def _date_in_window(dt_et: datetime, target_date: str, include_prior_evening: bool = True) -> bool:
    """
    Returns True if dt_et falls within the display window for target_date.

    Window includes:
    - All events on target_date
    - Events after 16:00 ET on the day before (post-market / midnight events)
    """
    target = datetime.strptime(target_date, "%Y-%m-%d").date()
    event_date = dt_et.date()

    if event_date == target:
        return True
    if include_prior_evening:
        prior_date = target - timedelta(days=1)
        if event_date == prior_date and dt_et.hour >= 16:
            return True
    return False
```

## Fed Events: Strict Ticker Whitelist

Do NOT use string matching like `"Fed" in event_name` — many economic indicators contain "Fed" but are not Fed policy events (e.g., "Chicago Fed National Activity Index").

```python
# Only these two tickers are actual Fed policy events
FED_TICKERS = {"FDTR", "UNITEDSTACENBANBALSH"}

def fetch_fed_events(date_str: str) -> list:
    """
    FDTR = Fed Funds Target Rate (policy statements, speeches)
    UNITEDSTACENBANBALSH = Fed Balance Sheet (always include, imp=1)
    """
    # ... fetch and filter by ticker in FED_TICKERS
```

Note: `UNITEDSTACENBANBALSH` has `importance=1` on finviz. Add it to Fed events directly — do not filter by importance — because it is market-critical even at Low importance.

## Economic Data: Blacklist + Importance Threshold

```python
BLACKLIST_TICKERS = {
    # Treasury auctions (noise for market-moving events)
    "UNITEDSTA3MONBILYIE", "UNITEDSTA6MONBILYIE", "USA4WEEBILYIE",
    "USA8WBY", "USA15YMR", "USA3YMR", "USA5YTY",
    # Regional Fed indices (not national policy)
    "USAKFCI", "UNITEDSTAKFMI", "UNITEDSTACONJOBCLA",
    # Other noise
    "UNITEDSTAREDIND", "USAAECW", "UNITEDSTANATGASSTOCH",
}

def fetch_economic_data(date_str: str) -> list:
    for entry in entries:
        # Skip blacklisted tickers
        # Skip importance < 2 (unless ticker is Fed Balance Sheet)
        # Apply _date_in_window() filter
```

## Example: Fetching Earnings with yfinance

```python
import yfinance as yf

def fetch_earnings(tickers: list) -> list:
    results = []
    for tkr in tickers:
        t = yf.Ticker(tkr)
        info = t.info or {}

        # Try multiple EPS keys (forward EPS is most reliable)
        eps_est = None
        for key in ("epsForward", "forwardEps", "trailingEps", "epsCurrentYear"):
            val = info.get(key)
            if val is not None:
                eps_est = round(float(val), 2)
                break

        results.append({
            "ticker":       tkr,
            "company":      info.get("shortName") or info.get("longName") or tkr,
            "eps_estimate": eps_est,
        })
    return results
```

## Pitfalls

1. **finviz is JS-rendered on some pages** — always use `calendar.ashx` (server-rendered), not the React version at `finviz.com/calendar`
2. **IJC timezone**: 20:30 ET = UTC 00:30+1day. Without `_date_in_window()` it will be missing from morning reports
3. **"Fed" in event name**: Chicago Fed, Kansas Fed, etc. are economic indices, not policy events. Use ticker whitelist only
4. **Importance 1 Fed Balance Sheet**: finviz marks it as imp=1 but it's market-critical. Always include it via ticker whitelist
5. **No BMO/AMC in finviz earnings**: finviz only says "Time TBD". Use yfinance calendar to get actual announcement time for BMO/AMC classification
6. **Rate limiting**: Add `time.sleep(1)` between requests to avoid 429

## Verification

```bash
/usr/bin/python3 -c "
import sys; sys.path.insert(0, '/path/to/scripts')
from fetch_events import fetch_all_events
import json; print(json.dumps(fetch_all_events(), indent=2, ensure_ascii=False))
"
```

## Files

```
scripts/
├── fetch_events.py   # Main scraper (finviz JSON extraction + yfinance)
├── formatters.py     # Discord message formatting
└── config.py        # Tickers, channel ID, log path
```
