#!/usr/bin/env python3
"""
Patch Hermes mcp_tool.py to prevent _rpc_lock deadlock.

Background refresh triggered by ToolListChangedNotification can hang on
session.list_tools(), holding _rpc_lock forever. All subsequent tool calls
deadlock. This patch adds a 15-second timeout to list_tools() during refresh.

Safe to reapply — detects if already patched.
"""

import re, sys

MCP_TOOL_PATH = "/root/.hermes/hermes-agent/tools/mcp_tool.py"
MARKER = "# Use a timeout so a stuck list_tools doesn't wedge _rpc_lock"

OLD = """            # 1. Fetch current tool list from server
            async with self._rpc_lock:
                tools_result = await self.session.list_tools()"""

NEW = """            # 1. Fetch current tool list from server
            # Use a timeout so a stuck list_tools doesn't wedge _rpc_lock
            # and deadlock all subsequent tool calls.
            async with self._rpc_lock:
                try:
                    tools_result = await asyncio.wait_for(
                        self.session.list_tools(), timeout=15,
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        "MCP server '%s': tool refresh timed out --- "
                        "releasing _rpc_lock so tool calls can proceed",
                        self.name,
                    )
                    return"""


def is_patched(path: str = MCP_TOOL_PATH) -> bool:
    with open(path) as f:
        return MARKER in f.read()


def apply(path: str = MCP_TOOL_PATH) -> bool:
    if is_patched(path):
        print("[PATCH] Already applied — nothing to do.")
        return True

    with open(path) as f:
        content = f.read()

    if OLD not in content:
        print("[PATCH] ERROR: target text not found — Hermes version may have changed.")
        return False

    new_content = content.replace(OLD, NEW, 1)
    with open(path, "w") as f:
        f.write(new_content)

    print("[PATCH] Applied successfully.")
    return True


if __name__ == "__main__":
    ok = apply()
    sys.exit(0 if ok else 1)
