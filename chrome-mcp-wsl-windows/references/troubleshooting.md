# Chrome MCP WSL Troubleshooting Log

## Session Background

Initial connection attempt from Hermes Agent (WSL2) to Chrome (Windows 11). Chrome 147.0.7727.138, chrome-devtools-mcp 0.23.0.

## Error Progression

### Phase 1: --autoConnect fails
```
Error: Could not find DevToolsActivePort for chrome at /root/.config/google-chrome/DevToolsActivePort
```
**Root cause:** `--autoConnect` searches for a local Chrome process in WSL. Chrome is on Windows, not WSL. The DevToolsActivePort file is at `C:\Users\denny\AppData\Local\Google\Chrome\User Data\DevToolsActivePort` on Windows.

### Phase 2: --browserUrl on wrong port (52555 → 9222)
```
Error: Failed to fetch browser webSocket URL from http://localhost:52555/json/version: fetch failed
Error: Failed to fetch browser webSocket URL from http://localhost:52555/json/version: HTTP Not Found
Error: Connection reset by peer
```
**Root cause:** Port 52555 is Chrome's real debug port, but bound to 127.0.0.1 — unreachable from WSL. Also, Chrome 144+ remote debugging uses WebSocket-only protocol — `/json/version` HTTP endpoint returns 404.

Port 9222 was actually **svchost.exe** (PID 5512), not Chrome. Accepts TCP connections but resets HTTP — not a CDP endpoint.

### Phase 3: Portproxy + --browserUrl
```
Error: Could not connect to Chrome. Check if Chrome is running.
Cause: Failed to fetch browser webSocket URL from http://172.27.16.1:52555/json/version: HTTP Not Found
```
**Progress:** Portproxy forwards correctly (WSL can reach Windows port). But HTTP endpoints don't exist.

### Phase 4: --wsEndpoint succeeds for WebSocket handshake
```
Python websockets.connect('ws://172.27.16.1:52555/devtools/browser/<uuid>') → Connected!
Browser.getVersion → Chrome/147.0.7727.138
```
**Key insight:** Direct WebSocket works. chrome-devtools-mcp needs `--wsEndpoint`.

### Phase 5: Network.enable times out through portproxy
```
Error: Network.enable timed out. Increase the 'protocolTimeout' setting.
```
**Root cause:** The portproxy relay adds latency. `Network.enable` requires Chrome to enumerate all tabs' network state — with 20+ tabs this times out.

**Fix:** `--no-category-network` and `--no-category-performance` flags skip these domain enables. `--slim` is the nuclear option (3 tools only).

### Phase 6: Slim mode works, full mode works with fewer tabs
```
mcp_chrome_screenshot → Took a screenshot
mcp_chrome_evaluate script=document.title → "MNQ1! 27,782.75 ▲ +0.67%"
```
**Final state:** Working connection. Full mode (28 tools) works when tabs are few; `--slim` or `--no-category-network` for many-tab sessions.

## Key Diagnostics Commands

```powershell
# Check Chrome debug port
Get-Content "$env:LOCALAPPDATA\Google\Chrome\User Data\DevToolsActivePort"

# Check portproxy rules
netsh interface portproxy show all

# Check firewall rules
netsh advfirewall firewall show rule name="Chrome MCP WSL"

# Check actual listening port (verify it's Chrome, not svchost)
netstat -ano | Select-String ':52555'

# Add portproxy (admin)
netsh interface portproxy add v4tov4 listenport=<PORT> listenaddress=0.0.0.0 connectport=<PORT> connectaddress=127.0.0.1
```

```bash
# From WSL: get Windows host IP
grep nameserver /etc/resolv.conf | awk '{print $2}'

# From WSL: test WebSocket directly
python3 -c "
import asyncio, websockets, json, subprocess
ns = subprocess.run(['grep','nameserver','/etc/resolv.conf'],capture_output=True,text=True).stdout.split()[1]
async def t():
    async with websockets.connect(f'ws://{ns}:<PORT>/devtools/browser/<UUID>', ping_timeout=5) as ws:
        await ws.send(json.dumps({'id':1,'method':'Browser.getVersion','params':{}}))
        print(await asyncio.wait_for(ws.recv(), 5))
asyncio.run(t())
"

# Check MCP server logs
tail -20 /root/.hermes/logs/mcp-stderr.log
```

## Chrome Profile Switching

When the user switches Chrome profiles:
1. All Chrome windows close and reopen under the new profile
2. The debug port **changes** (e.g., 52555 → 54096 → 49745)
3. The WebSocket UUID also changes
4. Portproxy rule needed for the NEW port
5. The ws-endpoint.sh script handles the new port automatically on `/reload-mcp`
