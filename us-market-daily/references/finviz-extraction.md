# Finviz Calendar Data Extraction

Detailed reference for parsing finviz.com calendar data — embedded JSON extraction, timezone handling, Fed/Balance Sheet filtering, and edge cases.

## Source URL

`https://finviz.com/calendar.ashx` (server-rendered HTML with embedded JSON — NOT the React version)

## JSON Extraction Pattern

finviz embeds the calendar as `window.fc_data = {"data":{"entries":[...]}}` in a `<script>` tag:

```python
import requests, json, re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def _extract_finviz_entries(html: str) -> list:
    start = html.find('"entries":[')
    if start == -1:
        return []
    depth = 0
    i = start + len('"entries":[')
    while i < len(html):
        ch = html[i]
        if ch == '[': depth += 1
        elif ch == ']':
            if depth == 0: break
            depth -= 1
        i += 1
    json_str = '[' + html[start + len('"entries":['):i] + ']'
    return json.loads(json_str)
```

## Critical Timezone: The IJC Problem

Initial Jobless Claims (IJC) publishes at 20:30 ET = 00:30 UTC next day.
If cron runs at Taiwan 06:00 (UTC 22:00 previous day), the UTC day has rolled but ET hasn't.
**Solution**: Expand window to include prior evening events (after 16:00 ET on day before):

```python
from datetime import datetime, timedelta

def _date_in_window(dt_et: datetime, target_date: str, include_prior=True) -> bool:
    target = datetime.strptime(target_date, "%Y-%m-%d").date()
    event_date = dt_et.date()
    if event_date == target:
        return True
    if include_prior:
        prior = target - timedelta(days=1)
        if event_date == prior and dt_et.hour >= 16:
            return True
    return False
```

## Fed Events: Strict Ticker Whitelist

Do NOT use `"Fed" in event_name` — many indicators contain "Fed" but are not policy events.

```python
FED_TICKERS = {"FDTR", "UNITEDSTACENBANBALSH"}
# FDTR = Fed Funds Target Rate
# UNITEDSTACENBANBALSH = Fed Balance Sheet (imp=1 on finviz but market-critical)
```

## Economic Data: Blacklist + Importance

```python
BLACKLIST_TICKERS = {
    "UNITEDSTA3MONBILYIE", "UNITEDSTA6MONBILYIE", "USA4WEEBILYIE",
    "USA8WBY", "USA15YMR", "USA3YMR", "USA5YTY",
    "USAKFCI", "UNITEDSTAKFMI", "UNITEDSTACONJOBCLA",
    "UNITEDSTAREDIND", "USAAECW", "UNITEDSTANATGASSTOCH",
}
```

Skip blacklisted tickers; skip importance < 2 (except Fed Balance Sheet).

## Browser Fallback (when JSON parsing fails)

When `_extract_finviz_entries()` returns empty:

**Economic data**: Navigate to `https://finviz.com/calendar/economic?dateFrom=YYYY-MM-DD`
```javascript
const tables = document.querySelectorAll('table');
const econTable = tables[tables.length - 2];
// cells: time, event, impact, for, actual, expected, prior
```

**Earnings data**: Navigate to `https://finviz.com/calendar/earnings?dateFrom=YYYY-MM-DD`
```javascript
const tables = document.querySelectorAll('table');
const earningsTable = tables[tables.length - 1];
// cells: ticker, company, time, mktCap, epsEst, ...
```
