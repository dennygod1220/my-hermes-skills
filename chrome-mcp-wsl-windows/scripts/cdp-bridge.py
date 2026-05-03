#!/usr/bin/env python3
"""
CDP Bridge — Direct Chrome DevTools Protocol over WebSocket.

Bypasses chrome-devtools-mcp when it fails due to the _rpc_lock deadlock
(or Network.enable timeout when many tabs/workers are open).

NOTE: Chrome 147+ prompts "Allow" once per new WebSocket connection from an
unknown client.  The persistent MCP connection avoids this; each ad-hoc
Python CDP script triggers it.  Use MCP for routine use; resort to CDP
bridge only when MCP is down.

Usage:
  python3 cdp-bridge.py list-pages             # List all targets
  python3 cdp-bridge.py eval <targetId> <js>   # Evaluate JS on a page
  python3 cdp-bridge.py screenshot <targetId> <output.png>  # Screenshot
  python3 cdp-bridge.py new-tab <url>          # Open a new tab
  python3 cdp-bridge.py close <targetId>       # Close a target
  python3 cdp-bridge.py test                   # Quick connectivity test

Dependencies: pip3 install websockets
"""

import asyncio
import base64
import json
import sys
from pathlib import Path


# ── Paths ──────────────────────────────────────────────────────────────
DEVPORT_FILE = Path("/mnt/c/Users/denny/AppData/Local/Google/Chrome/User Data/DevToolsActivePort")
WSL_RESOLV = Path("/etc/resolv.conf")


def get_ws_url() -> str:
    """Read DevToolsActivePort and construct the browser-level WebSocket URL."""
    if not DEVPORT_FILE.exists():
        print(f"Error: DevToolsActivePort not found at {DEVPORT_FILE}", file=sys.stderr)
        print("Make sure Chrome remote debugging is enabled (chrome://inspect/#remote-debugging)", file=sys.stderr)
        sys.exit(1)

    lines = DEVPORT_FILE.read_text().strip().splitlines()
    if len(lines) < 2:
        print(f"Error: {DEVPORT_FILE} has {len(lines)} lines, expected 2 (port + ws path)", file=sys.stderr)
        sys.exit(1)

    port = lines[0].strip()
    ws_path = lines[1].strip()

    ns_line = next((l for l in WSL_RESOLV.read_text().splitlines() if l.startswith("nameserver")), None)
    if not ns_line:
        print("Error: Could not find nameserver in /etc/resolv.conf", file=sys.stderr)
        sys.exit(1)
    host_ip = ns_line.split()[1]

    return f"ws://{host_ip}:{port}{ws_path}"


def _connect():
    """Context manager for WebSocket connection."""
    import websockets
    return websockets.connect(get_ws_url(), ping_timeout=10, max_size=2**20, close_timeout=5)


# ── CDP helper ─────────────────────────────────────────────────────────

async def cdp_call(ws, msg_id: int, method: str, params: dict = None,
                   session_id: str = None, timeout: float = 10) -> dict:
    """Send a CDP command and wait for the response with matching id.

    Chrome may emit *events* (Runtime.executionContextCreated, etc.) between
    sending a command and receiving its response.  This helper skips those
    events and only returns the response whose ``id`` matches ``msg_id``.
    """
    cmd = {"id": msg_id, "method": method}
    if params:
        cmd["params"] = params
    if session_id:
        cmd["sessionId"] = session_id
    await ws.send(json.dumps(cmd))

    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout))
        if msg.get("id") == msg_id:
            return msg
        # Events (notifications without matching id) are silently skipped


async def _attach(ws, target_id: str, timeout: float = 5) -> str:
    """Attach to a target and return sessionId.

    Chrome may send a ``Target.attachedToTarget`` *event* before the command
    response, especially when ``flatten=True``.  Handles both formats.
    """
    resp = await cdp_call(ws, 1, "Target.attachToTarget",
                          {"targetId": target_id, "flatten": True},
                          timeout=timeout)
    sid = resp.get("result", {}).get("sessionId")
    if not sid:
        raise RuntimeError(f"Attach response has no sessionId: {resp}")
    return sid


# ── Commands ───────────────────────────────────────────────────────────

async def cmd_test() -> None:
    """Quick connectivity test — get Chrome version and target count."""
    async with _connect() as ws:
        resp = await cdp_call(ws, 1, "Browser.getVersion", timeout=5)
        ver = resp.get("result", {}).get("product", "?")
        print(f"✓ Connected — Chrome: {ver}")
        resp = await cdp_call(ws, 2, "Target.getTargets", timeout=5)
        targets = resp.get("result", {}).get("targetInfos", [])
        print(f"✓ Targets: {len(targets)}")


def _print_targets(targets: list) -> None:
    pages = [t for t in targets if t.get("type") == "page"]
    others = [t for t in targets if t.get("type") != "page"]
    print(f"Total targets: {len(targets)} (pages: {len(pages)}, workers/other: {len(others)})")
    print()
    if pages:
        print("── Pages ──")
        for t in pages:
            tid = (t.get("targetId") or "?")[:10]
            title = (t.get("title") or "")[:70]
            url = (t.get("url") or "")[:90]
            print(f"  [{tid}] {title}")
            print(f"         {url}")
        print()
    if others:
        print(f"── Workers & Other ({len(others)}) ──")
        for t in others[:10]:
            tid = (t.get("targetId") or "?")[:10]
            title = (t.get("title") or "")[:50]
            url = (t.get("url") or "")[:80]
            print(f"  [{tid}] {title}")
            if url:
                print(f"         {url}")
        if len(others) > 10:
            print(f"  ... and {len(others) - 10} more")


async def cmd_list_pages() -> None:
    """List all targets with titles and URLs."""
    async with _connect() as ws:
        resp = await cdp_call(ws, 1, "Target.getTargets", timeout=5)
        targets = resp.get("result", {}).get("targetInfos", [])
        _print_targets(targets)


async def cmd_eval(target_id: str, js: str) -> None:
    """Evaluate JavaScript on a specific page target."""
    async with _connect() as ws:
        sid = await _attach(ws, target_id)
        resp = await cdp_call(ws, 2, "Runtime.evaluate",
                              {"expression": js, "returnByValue": True},
                              session_id=sid, timeout=10)
        result = resp.get("result", {}).get("result", {})
        if "value" in result:
            print(result["value"])
        elif "description" in result:
            print(result["description"])
        else:
            print(json.dumps(result, indent=2))


async def cmd_screenshot(target_id: str, output_path: str) -> None:
    """Capture a screenshot of a page target."""
    async with _connect() as ws:
        sid = await _attach(ws, target_id)
        resp = await cdp_call(ws, 2, "Page.captureScreenshot",
                              {"format": "png", "fromSurface": True},
                              session_id=sid, timeout=15)
        data = resp.get("result", {}).get("data")
        if not data:
            print(f"Error capturing screenshot: {json.dumps(resp)[:200]}", file=sys.stderr)
            sys.exit(1)
        Path(output_path).write_bytes(base64.b64decode(data))
        print(f"✓ Screenshot saved to {output_path}")


async def cmd_new_tab(url: str) -> None:
    """Open a new tab with the given URL."""
    async with _connect() as ws:
        resp = await cdp_call(ws, 1, "Target.createTarget", {"url": url}, timeout=5)
        tid = resp.get("result", {}).get("targetId", "?")
        print(f"✓ New tab created — targetId: {tid[:10]}...")


async def cmd_close(target_id: str) -> None:
    """Close a target by ID."""
    async with _connect() as ws:
        resp = await cdp_call(ws, 1, "Target.closeTarget", {"targetId": target_id}, timeout=5)
        if resp.get("result", {}).get("success"):
            print(f"✓ Target {target_id[:10]}... closed")
        else:
            print(f"Error closing target: {json.dumps(resp)[:200]}", file=sys.stderr)


# ── CLI ────────────────────────────────────────────────────────────────

COMMANDS = {
    "test": cmd_test,
    "list-pages": cmd_list_pages,
    "eval": cmd_eval,
    "screenshot": cmd_screenshot,
    "new-tab": cmd_new_tab,
    "close": cmd_close,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(f"Available: {', '.join(COMMANDS)}", file=sys.stderr)
        sys.exit(1)
    args = sys.argv[2:]
    coro = COMMANDS[cmd](*args)
    asyncio.run(coro)


if __name__ == "__main__":
    main()
