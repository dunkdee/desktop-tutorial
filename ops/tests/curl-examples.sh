#!/usr/bin/env bash
set -euo pipefail
: "${N8N_TOOL_SECRET:=CHANGE_ME_NOW}"
: "${GATEWAY:=http://localhost:5678/webhook/agent-tools}"

echo "Calling roi_snapshot..."
curl -sS -X POST "$GATEWAY" \
 -H "X-AGENT-KEY: $N8N_TOOL_SECRET" -H "Content-Type: application/json" \
 -d '{"tool":"roi_snapshot","args":{"since":"7d","metrics":["revenue","orders"]}}' | jq .

echo "Calling publish_content..."
curl -sS -X POST "$GATEWAY" \
 -H "X-AGENT-KEY: $N8N_TOOL_SECRET" -H "Content-Type: application/json" \
 -d '{"tool":"publish_content","args":{"channel":"tiktok","action":"draft","caption":"test","dry_run":true}}' | jq .

echo "Calling email_followup..."
curl -sS -X POST "$GATEWAY" \
 -H "X-AGENT-KEY: $N8N_TOOL_SECRET" -H "Content-Type: application/json" \
 -d '{"tool":"email_followup","args":{"audience":"Warm Leads","subject":"Hi","body":"Value + soft CTA","send_at":"now","dry_run":true}}' | jq .

echo "Calling trading_execute..."
curl -sS -X POST "$GATEWAY" \
 -H "X-AGENT-KEY: $N8N_TOOL_SECRET" -H "Content-Type: application/json" \
 -d '{"tool":"trading_execute","args":{"symbol":"EURUSD","side":"buy","size":1000,"mode":"paper"}}' | jq .
