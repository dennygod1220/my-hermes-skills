# TradingView Chart Automation via Chrome MCP

## Overview

Automating TradingView's chart (tradingview.com) from Hermes Agent via Chrome MCP is constrained by two architectural facts:

1. **TradingView renders everything on `<canvas>`** — no DOM elements for individual chart elements (candlesticks, lines, price labels on the chart area itself). You cannot `mcp_chrome_click` a specific price level.
2. **Programmatic JavaScript events (`new MouseEvent(...)`) have `isTrusted=false`** — TradingView's canvas event handlers (and most modern canvas-based SPAs) check `event.isTrusted` and silently ignore untrusted events. Dispatching `mousedown`/`mouseup`/`click`/`pointerdown`/`pointerup` from `mcp_chrome_evaluate_script` does NOT draw on the chart.

## What DOES Work

### Reading Chart State (Read-Only)

The internal chart model is accessible via the watched-value chain on `window._exposed_chartWidgetCollection`:

```js
const cwc = window._exposed_chartWidgetCollection;
const model = cwc._activeChartWidgetModel.value();    // chart widget model
const m_model = model.m_model;                        // internal chart model
const pane = m_model._panes[0];                       // main chart pane (pane 0)
const priceScale = pane._rightPriceScales[0];          // right-side price axis

// Price ↔ pixel coordinate conversion
const yPx = priceScale.priceToCoordinate(27826);       // price → Y within pane
const price = priceScale.coordinateToPrice(150);       // Y → price
```

**Pane layout** (canvases stack vertically):
| Pane | Content | Height |
|------|---------|--------|
| 0 | Main candlestick chart | 438px |
| 1 | Volume | 88px |
| 2 | KDJ | 106px |
| 3 | DI | 129px |
| — | Time axis | 28px |

The main chart canvas is at pixel position `(56, 42)` with dimensions `1749×438`. All 19 canvases overlay the same area in layers.

### Taking Screenshots for Vision Analysis

`mcp_chrome_screenshot` captures the full viewport. Pass `filePath` to save:

```js
mcp_chrome_screenshot({ filePath: "/tmp/tv_snap.png", format: "png" })
```

Then feed to `vision_analyze` for structured chart reading.

## What Does NOT Work

### ❌ Dispatching Mouse Events from JS

```js
// ALL of these are silently ignored by TradingView's canvas handlers:
canvas.dispatchEvent(new MouseEvent('mousedown', { clientX, clientY, ... }));
canvas.dispatchEvent(new PointerEvent('pointerdown', { clientX, clientY, ... }));
element.dispatchEvent(new MouseEvent('click', { clientX, clientY, ... }));
```

Reason: `event.isTrusted === false` for programmatic events. The TradingView charting library rejects them at the handler level. This is a browser security feature — there is no workaround in page JS.

### ❌ Pine Editor Automation (Monaco)

The Pine Editor uses the Monaco editor (same as VS Code). Setting its textarea value via JS native setter + dispatching `input` events does NOT reliably update the editor model. The editor state becomes garbled — partial lines, missing newlines, concatenated code from old and new content.

The editor textarea has class `inputarea monaco-mouse-cursor-text` and is inside the Pine panel container.

### ❌ `mcp_chrome_click(uid)` for Specific Prices

The Canvas element (uid=3_129) covers the entire chart area. `mcp_chrome_click` always clicks at the element's **center** — you can't target a specific Y-coordinate. No sub-element exists at each price level because it's all one canvas.

## What Might Work (Not Tested)

### CDP Input.dispatchMouseEvent

The Chrome DevTools Protocol has `Input.dispatchMouseEvent` which creates **trusted** events (isTrusted=true). This is what the MCP server (`chrome-devtools-mcp`) uses internally for its `mcp_chrome_click` tool. However:

- The current tool only exposes `click(uid)` with center-point coordinates
- The MCP server does not expose a raw "click at (x,y)" tool
- A custom MCP extension or direct CDP WebSocket call would be needed
- The WebSocket URL pattern is: `ws://<WSL_GATEWAY_IP>:<PORT><DEVPATH>` (read from `DevToolsActivePort`)

### Pine Script via "New" Workflow

Instead of editing the existing script, a fresh Pine Script could be created by:
1. Clicking "Pine" → "New" (creates a clean editor)
2. Typing the code character-by-character using `mcp_chrome_type_text` 
3. Clicking "Add to Chart" — but Monaco's input handling makes this unreliable

A more reliable alternative: use `mcp_chrome_evaluate_script` to replace the Monaco editor's model directly via the internal `monaco.editor.getModels()` API (if accessible), rather than the textarea hack.

## Recommended Fallback

For drawing support/resistance lines, tell the user the exact price levels and let them draw manually (Alt+H for horizontal line tool, then click on the price axis at the desired level). The user can draw all lines in ~15 seconds once they know the levels.
