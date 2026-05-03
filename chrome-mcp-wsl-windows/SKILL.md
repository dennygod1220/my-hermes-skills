---
name: chrome-mcp-wsl-windows
description: Connect Hermes Agent (running in WSL) to Chrome running on the Windows host via chrome-devtools-mcp.
version: 2.0.0
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

### 2. Windows Firewall Rule (admin PowerShell, ONE TIME)

```powershell
netsh advfirewall firewall add rule name="Chrome MCP WSL" dir=in protocol=tcp localport=9222 action=allow
```

### 3. Portproxy (admin PowerShell, PER PROFILE / PER PORT)

Read Chrome's debug port from Windows:

```powershell
Get-Content "$env:LOCALAPPDATA\Google\Chrome\User Data\DevToolsActivePort"
```

Then add a portproxy rule (repeat for each new port when switching profiles):

```powershell
netsh interface portproxy add v4tov4 listenport=<PORT> listenaddress=0.0.0.0 connectport=<PORT> connectaddress=127.0.0.1
```

Common pitfalls:
- **Firewall still blocks after rule?** The portproxy listener binds to `0.0.0.0:<PORT>` via svchost. Verify with `netsh interface portproxy show all`.
- **Old portproxy rule still active?** Remove stale rules with `netsh interface portproxy delete v4tov4 listenport=<OLDPORT> listenaddress=0.0.0.0`.
- **Every Chrome profile change = new port.** Always re-check DevToolsActivePort.

### 4. WSL Config

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
      - --slim
```

**⚠️  CRITICAL: Start with `--slim` for WSL→Windows connections.** The full toolset sends `Network.enable` which times out through the portproxy relay when many tabs are open. `--slim` exposes 3 core tools — enough for most browser control.

**If you need more tools** (click, fill, list_pages, etc.) and have fewer than ~10 tabs open, replace `--slim` with `--no-category-network --no-category-performance` to skip the slow domain enables:

```yaml
    args:
      - /root/.hermes/scripts/ws-endpoint.sh
      - --no-category-network
      - --no-category-performance
```

This gives 28 tools (vs 3 in slim, vs 33 in full mode). The tools/ directories are listed under Support Files below.

### 5. Verify

```bash
hermes mcp test chrome
```

In Hermes session:
- `/reload-mcp` to load tools
- `mcp_chrome_screenshot` — take a screenshot
- `mcp_chrome_navigate type=url url=https://example.com` — navigate
- `mcp_chrome_evaluate script=document.title` — execute JS

## Troubleshooting

### "Network.enable timed out"
**Cause:** Portproxy relay latency causes DevTools domain enable commands to time out.
**Fix:** Add `--slim` to the MCP server args. This skips `Network.enable` and `Performance.enable` during init.

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

## Support Files

The skill ships with two support files under its directory:

| File | Type | Purpose |
|------|------|---------|
| `scripts/ws-endpoint.sh` | Script | Runtime launcher — reads DevToolsActivePort dynamically, constructs WebSocket URL, launches chrome-devtools-mcp. Copy to `/root/.hermes/scripts/` for use. |
| `references/troubleshooting.md` | Reference | Full error transcript and diagnostics from the initial WSL→Windows Chrome MCP setup session. Includes every error encountered and the fix. |
