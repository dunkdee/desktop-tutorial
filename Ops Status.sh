#!/usr/bin/env bash
set -euo pipefail
GATEWAY="${GATEWAY:-http://localhost:5678/webhook/agent-tools}"
SECRET="${N8N_TOOL_SECRET:-CHANGE_ME_NOW}"

echo "== n8n Gateway probe =="
code=$(curl -s -o /tmp/probe.json -w "%{http_code}" -X POST "$GATEWAY" \
 -H "X-AGENT-KEY: $SECRET" -H "Content-Type: application/json" \
 -d '{"tool":"roi_snapshot","args":{"since":"7d","metrics":["revenue","orders"]}}' || true)
echo "HTTP $code"
jq . /tmp/probe.json || cat /tmp/probe.json
