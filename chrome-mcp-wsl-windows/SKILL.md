---
name: chrome-mcp-wsl-windows
description: Connect Hermes Agent (running in WSL) to Chrome running on the Windows host via chrome-devtools-mcp.
version: 2.1.0
author: auto-generated
tags:
  - wsl
  - chrome
  - mcp
  - windows
  - devtools
---

# Chrome MCP from WSL to Windows

Connect Hermes Agent running in WSL2 to Chrome DevTools on the Windows host via `chrome-devtools-mcp`.

## Architecture

Chrome 144+ remote debugging (enabled via `chrome://inspect/#remote-debugging` toggle) uses a **WebSocket-only** protocol. It does NOT expose the classic HTTP REST API endpoints (`/json/version`, `/json/list`). The connection info is stored in Chrome's `DevToolsActivePort` file on Windows.

```
Windows Chrome (127.0.0.1:PORT)  →  Portproxy (0.0.0.0:PORT)  →  WSL (172.x.x.x:PORT)
```

## Prerequisites

- Chrome 144+ on Windows with "Allow remote debugging" enabled at `chrome://inspect/#remote-debugging`
- Node.js in WSL (for `chrome-devtools-mcp`)
- Windows admin access (for portproxy + firewall rules)

## Setup

### 1. Install chrome-devtools-mcp in WSL

```bash
npm install -g chrome-devtools-mcp
```

### 2. Install websocket-client in WSL (for Python CDP fallback)

```bash
pip3 install --break-system-packages websocket-client
```

### 3. Windows Firewall Rule (admin PowerShell, ONE TIME)

```powershell
netsh advfirewall firewall add rule name="Chrome MCP WSL" dir=in protocol=tcp localport=64544 action=allow
```

> ⚠️ Use the **actual port** from DevToolsActivePort. Chrome changes ports on every profile restart. Run `netsh advfirewall firewall show rule name="Chrome MCP WSL"` to verify the current port, then add a new rule if the port changed.

### 4. Portproxy (admin PowerShell, PER PROFILE / PER PORT)

Read Chrome's debug port from Windows:

```powershell
Get-Content "$env:LOCALAPPDATA\Google\Chrome\User Data\DevToolsActivePort"
```

Then add a portproxy rule (repeat for each new port when switching profiles):

```powershell
netsh interface portproxy add v4tov4 listenport=<PORT> listenaddress=0.0.0.0 connectport=<PORT> connectaddress=127.0.0.1
```

**VERIFY** the rule is active:

```powershell
netsh interface portproxy show all
# Expected: 0.0.0.0        <PORT>       127.0.0.1       <PORT>
```

Common pitfalls:
- **Firewall still blocks after rule?** The portproxy listener binds to `0.0.0.0:<PORT>` via svchost. Verify with `netsh interface portproxy show all`.
- **Old portproxy rule still active?** Remove stale rules with `netsh interface portproxy delete v4tov4 listenport=<OLDPORT> listenaddress=0.0.0.0`.
- **Every Chrome profile change = new port.** Always re-check DevToolsActivePort. Check BEFORE connecting.

### 5. WSL Config

Create the dynamic WebSocket endpoint script at `/root/.hermes/scripts/ws-endpoint.sh`:

```bash
cat > /root/.hermes/scripts/ws-endpoint.sh << 'SCRIPT'
#!/bin/bash
DEVPORT_FILE="/mnt/c/Users/denny/AppData/Local/Google/Chrome/User Data/DevToolsActivePort"
if [ -f "$DEVPORT_FILE" ]; then
    PORT=$(head -1 "$DEVPORT_FILE")
    WSPATH=$(tail -1 "$DEVPORT_FILE")
    WS_IP=$(grep nameserver /etc/resolv.conf | awk '{print $2}')
    exec /root/.hermes/node/bin/chrome-devtools-mcp \
        --wsEndpoint "ws://${WS_IP}:${PORT}${WSPATH}" \
        --no-category-network \
        --no-category-performance \
        --no-usage-statistics \
        "$@"
else
    echo "DevToolsActivePort not found" >&2
    exit 1
fi
SCRIPT
chmod +x /root/.hermes/scripts/ws-endpoint.sh
```

Config in `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  chrome:
    command: bash
    args:
      - /root/.hermes/scripts/ws-endpoint.sh
```

**⚠️  CRITICAL: Use `--no-category-network --no-category-performance` for WSL→Windows connections.** The full toolset sends `Network.enable` which times out through the portproxy relay when many tabs are open. These flags skip the slow domain enables and expose 24 tools (vs 3 in `--slim`, vs 33 in full mode).

If even these 24 tools fail with `ClosedResourceError` (common through portproxy), use the **Python CDP fallback** (see section below).

### 6. Verify

```bash
hermes mcp test chrome
```

Expect:
```
✓ Connected (XXXms)
✓ Tools discovered: 24
```

If `hermes mcp test` succeeds but actual tool calls (list_pages, evaluate_script, take_screenshot) fail with `ClosedResourceError`, this is a known portproxy latency issue — use the Python CDP fallback below.

## Troubleshooting

### MCP tool calls hang after Hermes restart (TimeoutError)

**Symptom:** All chrome MCP tools (`list_pages`, `screenshot`, `evaluate`, etc.) hang indefinitely and return `MCP call failed: TimeoutError`. This happens on the FIRST tool call after Hermes starts, even though `hermes mcp test chrome` succeeds.

**Root cause:** `_rpc_lock` deadlock in Hermes mcp_tool.py — a background `_refresh_tools` task (triggered by `ToolListChangedNotification` from chrome-devtools-mcp) acquires `_rpc_lock` and hangs on `session.list_tools()`, blocking all subsequent tool calls.

**Fix:** Apply the patch first:
```bash
python3 /root/.hermes/profiles/stock_master/skills/my-hermes-skills/chrome-mcp-wsl-windows/scripts/patch-mcp-rpc-lock.py
```

If already patched and still failing, restart the Hermes session (`/new` or `/reload-mcp`).

### "Network.enable timed out"
**Cause:** Portproxy relay latency causes DevTools domain enable commands to time out with many tabs/workers open (common in daily browsing with 20-60+ targets).
**Fix (first):** `--no-category-network --no-category-performance` flags (already set in `ws-endpoint.sh`) skip the slow domain enables during init.
**Fix (last resort, ask user first):** `--slim` mode bypasses all network/performance enables but leaves only 3 tools: navigate, screenshot, evaluate. **⚠️ NEVER switch to `--slim` without asking the user.** The user has explicitly rejected this approach — it breaks use cases that need more tools.
**Do NOT default to Python CDP bridge as a workaround.** Chrome 147+ prompts "Allow" per-connection for CDP WebSocket connections — each ad-hoc Python script triggers a prompt in the browser, which is impractical. Fix the MCP connection instead. See `references/cdp-limitations.md` for details.

### "Could not find DevToolsActivePort"
**Cause:** `--autoConnect` was used but there's no local Chrome in WSL.
**Fix:** Switch to `--wsEndpoint` with the full WebSocket URL from DevToolsActivePort.

### "socket hang up" or "fetch failed"
**Cause:** Portproxy not set up, wrong port, or firewall blocking.
**Fix:** Verify portproxy with `netsh interface portproxy show all` and check the actual port in DevToolsActivePort.

### "HTTP Not Found" on /json/version
**Cause:** Chrome 144+ remote debugging toggle uses WebSocket-only (no HTTP REST API).
**Fix:** Use `--wsEndpoint` instead of `--browserUrl`.

### Chrome shows yellow "automated software control" banner
**Normal.** This means the MCP connection is active.

## Available Slim Tools

With `--slim`:
| Tool | What it does |
|------|-------------|
| `mcp_chrome_navigate` | Navigate to URL, back, forward, or reload |
| `mcp_chrome_screenshot` | Screenshot current page viewport |
| `mcp_chrome_evaluate` | Execute JavaScript in page context |

Without `--slim` (full mode, only works natively — not through portproxy):
All standard CDP tools: click, fill, fill_form, hover, list_pages, select_page, press_key, type_text, close_page, new_page, take_snapshot, etc.

## References

- `scripts/ws-endpoint.sh` — dynamic WebSocket endpoint launcher (copy to `/root/.hermes/scripts/`)
- `references/troubleshooting.md` — full error transcript and diagnostics from initial setup session

## Python CDP Fallback (Direct WebSocket)

When `chrome-devtools-mcp` tools fail with `ClosedResourceError` or `Network.enable timed out` (typically when 20+ tabs/workers are open through the portproxy relay), use direct Python CDP over WebSocket. This bypasses the MCP server entirely.

### Prerequisites

```bash
pip3 install websockets
```

### Quick Test

Run this to verify Chrome is reachable and list all targets:

```bash
cat << 'PYEOF' | python3
import asyncio, json, subprocess
ns = subprocess.run(['grep','nameserver','/etc/resolv.conf'],capture_output=True,text=True).stdout.split()[1]
with open("/mnt/c/Users/denny/AppData/Local/Google/Chrome/User Data/DevToolsActivePort") as f:
    lines = f.read().strip().splitlines()
port = lines[0].strip()
wspath = lines[1].strip()
ws_url = f"ws://{ns}:{port}{wspath}"

async def test():
    import websockets
    async with websockets.connect(ws_url, ping_timeout=10, max_size=2**20) as ws:
        await ws.send(json.dumps({'id':1,'method':'Browser.getVersion','params':{}}))
        resp = json.loads(await asyncio.wait_for(ws.recv(), 5))
        print(f"Chrome: {resp.get('result',{}).get('product','?')}")
        await ws.send(json.dumps({'id':2,'method':'Target.getTargets','params':{}}))
        resp = json.loads(await asyncio.wait_for(ws.recv(), 5))
        targets = resp.get('result',{}).get('targetInfos',[])
        print(f"Targets: {len(targets)}")
        for t in targets[:10]:
            print(f"  [{t.get('targetId','')[:10]}] {t.get('title','')[:60]}")
        if len(targets) > 10:
            print(f"  ... and {len(targets)-10} more")
asyncio.run(test())
PYEOF
```

### Common CDP Commands

**List all targets (tabs, workers, service workers):**
```python
await ws.send(json.dumps({'id':1,'method':'Target.getTargets','params':{}}))
resp = json.loads(await ws.recv())
```

**Execute JavaScript on a specific page target:**
```python
# First attach to a page target
await ws.send(json.dumps({
    'id':1, 'method':'Target.attachToTarget',
    'params':{'targetId':'<targetId_from_Target.getTargets>','flatten':True}
}))
session_id = json.loads(await ws.recv())['result']['sessionId']

# Then evaluate JS in that session
await ws.send(json.dumps({
    'id':2, 'method':'Runtime.evaluate',
    'params':{'expression':'document.title'},
    'sessionId':session_id
}))
```

**Take a screenshot of a page:**
```python
await ws.send(json.dumps({
    'id':3, 'method':'Page.captureScreenshot',
    'params':{'format':'png'},
    'sessionId':session_id
}))
resp = json.loads(await ws.recv())
png_data = base64.b64decode(resp['result']['data'])
```

**Create a new tab:**
```python
await ws.send(json.dumps({
    'id':4, 'method':'Target.createTarget',
    'params':{'url':'https://example.com'}
}))
```

### Script

The skill ships with `scripts/cdp-bridge.py` — a reusable CLI wrapper that implements the above commands. See its docstring for usage.

## Known Issues

### MCP tool calls timeout after Hermes restart

**Symptom:** `mcp_chrome_list_pages` (and all other Chrome MCP tools) hang indefinitely and eventually return `MCP call failed: TimeoutError`. This happens on the FIRST tool call after Hermes starts.

**Root cause:** During Hermes startup, `_discover_tools()` succeeds, but a background `_refresh_tools` task (triggered by `ToolListChangedNotification` from chrome-devtools-mcp) acquires `_rpc_lock` and then hangs on `session.list_tools()`. The lock is never released, so all subsequent `session.call_tool()` calls deadlock behind the same lock.

**Fix (applied 2026-05-03):** Patched `/root/.hermes/hermes-agent/tools/mcp_tool.py` to add a 15-second `asyncio.wait_for` around the `list_tools()` call inside `_refresh_tools`. If it times out, the lock is released and a warning is logged. See `scripts/patch-mcp-rpc-lock.py`.

**Reapply after Hermes update:**
```bash
python3 /root/.hermes/profiles/stock_master/skills/my-hermes-skills/chrome-mcp-wsl-windows/scripts/patch-mcp-rpc-lock.py
```

## Support Files

The skill ships with four support files under its directory:

| File | Type | Purpose |
|------|------|---------|
| `scripts/ws-endpoint.sh` | Script | Runtime launcher — reads DevToolsActivePort dynamically, constructs WebSocket URL, launches chrome-devtools-mcp. Copy to `/root/.hermes/scripts/` for use. |
| `scripts/cdp-bridge.py` | Script | Python CDP bridge — direct WebSocket fallback when MCP tools fail. Supports list-pages, eval, screenshot, new-tab. |
| `scripts/patch-mcp-rpc-lock.py` | Script | Reapply the `_rpc_lock` deadlock fix after Hermes updates. |
| `references/troubleshooting.md` | Reference | Full error transcript and diagnostics from the initial WSL→Windows Chrome MCP setup session. |
| `references/tradingview-automation.md` | Reference | TradingView chart interaction patterns — what works, what doesn't, and why. Use when automating TradingView from Hermes. |
