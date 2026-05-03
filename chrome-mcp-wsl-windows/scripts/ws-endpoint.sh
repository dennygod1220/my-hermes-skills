#!/bin/bash
# Chrome DevTools MCP - WSL→Windows WebSocket Bridge
# Reads the Chrome DevToolsActivePort from Windows dynamically
# and launches chrome-devtools-mcp with correct WebSocket endpoint.
#
# Usage: ws-endpoint.sh [--slim|--no-category-network ...]
# Extra args are forwarded to chrome-devtools-mcp

DEVPORT_FILE="/mnt/c/Users/denny/AppData/Local/Google/Chrome/User Data/DevToolsActivePort"

if [ ! -f "$DEVPORT_FILE" ]; then
    echo "DevToolsActivePort not found at $DEVPORT_FILE" >&2
    echo "Make sure Chrome has remote debugging enabled at chrome://inspect/#remote-debugging" >&2
    exit 1
fi

PORT=$(head -1 "$DEVPORT_FILE")
WSPATH=$(tail -1 "$DEVPORT_FILE")
WS_IP=$(grep nameserver /etc/resolv.conf | awk '{print $2}')

exec /root/.hermes/node/bin/chrome-devtools-mcp \
    --wsEndpoint "ws://${WS_IP}:${PORT}${WSPATH}" \
    --no-usage-statistics \
    "$@"
