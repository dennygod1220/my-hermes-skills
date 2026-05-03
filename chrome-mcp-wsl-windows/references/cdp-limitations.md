# CDP Bridge Limitations

## Per-connection "Allow" Prompt

Each time a Python CDP script opens a new WebSocket to Chrome's DevTools endpoint,
Chrome 147+ shows an "Allow" prompt in the browser (via the
`chrome://inspect/#remote-debugging` page). This is a **per-connection**
authorization — every ad-hoc `cdp-bridge.py` invocation triggers it.

**The persistent MCP connection avoids this.** The MCP server
(chrome-devtools-mcp) opens one WebSocket at startup and keeps it alive, so
Chrome only prompts once.

**Consequence:** Reserve the CDP bridge for diagnostics and one-off operations
when MCP is unreachable. For routine automation, fix the MCP connection instead.

## Interleaved CDP Events

When using CDP directly (not through chrome-devtools-mcp), Chrome emits events
(such as `Runtime.executionContextCreated`) interleaved with command responses.
A naive `await ws.recv()` will read an event instead of the expected response,
causing parse errors.

The `cdp-bridge.py` script handles this via `cdp_call()` — it reads messages in
a loop, skipping events, and returns only the response whose `id` matches the
command's `id`.
