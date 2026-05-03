# TradingView Chrome Extension Architecture

## Purpose

Bypass WSL CDP limitations and TradingView bot-detection risks. Instead of Hermes controlling Chrome via CDP, the Chrome Extension **pushes** data from TradingView to Hermes via local files.

## Architecture

```
Chrome Extension (TradingView tab)
  ├── chrome.tabs.captureVisibleTab() → screenshot PNG
  ├── DOM querySelector() → price, MA, RSI values
  └── Popup input → direction, entry, stop-loss, target
          │
          ▼
  Local file: C:\Users\{user}\Download\tv_*.png + tv_*.json
          │
          ▼ (via /mnt/c/ in WSL)
  Hermes Agent
  ├── Vision: pattern analysis, trendlines, support/resistance
  ├── Web Search: finviz calendar, news, events
  └── Discord notification with full analysis
```

## Extension MVP Capabilities

| Feature | Implementation | Notes |
|---------|---------------|-------|
| Screenshot | `chrome.tabs.captureVisibleTab()` | Vision reads patterns, trendlines, candlestick formations |
| DOM price/indicator grab | `document.querySelector()` | 3-5 values max: current price, MA, RSI — keep minimal |
| Popup input | Extension Action Popup | Fields: direction (long/short), entry price, stop-loss, target, notes |
| Save to disk | `<a download>` from popup + `chrome.storage.session` | See MV3 workaround below |

## MV3 Critical: Data URIs and Blob URLs

In Chrome 147+ (Manifest V3), the standard approach fails:
- **Service worker** lacks `URL.createObjectURL()` (throws `is not a function`)
- **Data URI in `chrome.downloads.download()`** — Chrome 147+ **ignores the `filename` parameter** entirely for data URIs/blob URLs. Files go to `Downloads/` with UUID names.
- **Offscreen API** (`chrome.offscreen.createDocument`) has `createObjectURL()` but no `chrome.downloads.download()`

### The Only Working Pattern

1. **Background** (service worker): `captureVisibleTab()` → data URL → build JSON → store both in `chrome.storage.session` → return `storageKey` to popup
2. **Popup** (real DOM): read from `chrome.storage.session` → `fetch(dataUrl)` → `response.blob()` → `URL.createObjectURL(blob)` → create hidden `<a>` element with `download='filename.png'` → `.click()` → remove → `setTimeout(revokeObjectURL, 5000)`
3. Popup cleans up: `chrome.storage.session.remove(key)`

**Drawback**: `<a download>` only accepts a filename, not a directory path. Files always go to `Downloads/`. Use the `--import` watcher script to move files to the screenshots directory.

**Storage limit**: `chrome.storage.session` has ~1MB per item. Fall back to `chrome.storage.local` (5MB per item, slower) for large screenshots.

## What NOT to Do in v1

- ❌ Don't scrape full DOM data — TradingView uses Canvas for charts, class names change frequently
- ❌ Don't try to auto-detect patterns via DOM — that's what Vision is for
- ❌ Don't build a server/API endpoint — save locally, let Hermes read via /mnt/c/

## Pitfalls

- **DOM class names change** — TradingView updates frequently. Keep DOM scraping to absolute minimum.
- **Vision misreads numbers** — Screenshot analysis can hallucinate exact price values. Cross-reference with DOM-captured price.
- **Multiple monitor setups** — `captureVisibleTab()` captures only the active tab. User must ensure TradingView is the active tab.
- **WSL path access** — Extension saves to Windows path, Hermes reads from `/mnt/c/Users/...`. Ensure WSL has mount access.
