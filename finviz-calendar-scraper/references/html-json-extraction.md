# Finviz HTML Embedded JSON Extraction

## When to Use This Technique

finviz.com pages (calendar.ashx and others) have empty HTML tables — the real data lives in a `<script>` tag's JSON block. If BeautifulSoup table parsing fails, extract from the HTML directly.

## The Pattern

```html
<script>
  {
    "data": {
      "initialDateFrom": "2026-04-20",
      "entries": [
        {"calendarId": 419826, "ticker": "FDTR", "event": "Fed Waller Speech", ...},
        ...
      ]
    }
  }
</script>
```

## Extraction Code

```python
import requests, json

def extract_finviz_entries(html: str) -> list:
    # 1. Find "entries":[
    start = html.find('"entries":[')
    if start == -1:
        return []

    # 2. Bracket-counting to find the matching ]
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

    # 3. JSON decode
    json_str = '[' + html[start + len('"entries":['):i] + ']'
    return json.loads(json_str)
```

## Why Not json.loads on the whole script block?

The HTML wraps the JSON inside `{"data":{` and `}}`. Extracting just the `entries` array is cleaner and avoids dealing with the outer structure.

## Example Usage

```python
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

resp = requests.get("https://finviz.com/calendar.ashx", headers=HEADERS, timeout=15)
entries = extract_finviz_entries(resp.text)

for e in entries:
    print(e["date"], e["ticker"], e["event"])
```

## Pitfalls

- **User-Agent too simple** → finviz returns different HTML without the JSON block
- **Rate limiting** → add `time.sleep(1)` between requests
- **Page structure changes** → test with `resp.text[:5000]` to confirm JSON is present before deploying
- **Different pages may differ** → some finviz pages use different JS structures
