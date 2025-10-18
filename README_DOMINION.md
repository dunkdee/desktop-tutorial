# Dominion Automation Empire — JARVIS DOMINION

This repository contains a production-ready, opinionated n8n automation stack wired for an Agent Builder agent called "JARVIS DOMINION". It provides a single secured webhook gateway for Agent Builder agents, a scheduled "Daily Driver", a lightweight trading-hook stub, curl test harness, an env template, and a GitHub Actions CI guard to validate n8n workflow JSON.

Goals
- Single gateway webhook: POST /webhook/agent-tools (auth via header `X-AGENT-KEY`)
- Tools offered: publish_content, roi_snapshot, email_followup, trading_execute
- Approval switch: set `args.require_approval = true` to short-circuit and return approval-needed
- Scheduled "Daily Driver": hourly + daily 09:00 local runs that call the gateway
- Light trading webhook: POST /webhook/trading-hook (stub simulated fill)
- CI: validate JSON and minimal import-readiness checks

Files added
- /ops/n8n/agent_tools_gateway.json
- /ops/n8n/empire_daily_driver.json
- /ops/n8n/trading_hook.json
- /ops/env/.env.example
- /ops/tests/curl-examples.sh
- README_DOMINION.md
- .github/workflows/validate-n8n.yml

What each workflow does
- agent_tools_gateway.json
  - Webhook: POST /webhook/agent-tools
  - Auth: validates header `X-AGENT-KEY` against env `N8N_TOOL_SECRET`. If invalid -> 401.
  - Checks `args.require_approval` — if true returns `{ ok:false, needs_approval:true, plan:{ tool, args } }` with no side-effects.
  - Switches on `body.tool`:
    - publish_content: returns stub { ok:true, result:{ status:"drafted_or_posted", echo:args } }
    - roi_snapshot: returns stub { ok:true, result:{ revenue:0, orders:0, params:args } }
    - email_followup: respects `dry_run` and returns { ok:true, result:{ sent:!dry_run, mode: dry_run?'dry_run':'live', params:args } }
    - trading_execute: forwards the args to /webhook/trading-hook and returns the trading-hook JSON response.
  - Final Respond node returns JSON body and uses status code 200 on success or 401 for invalid secret.

- empire_daily_driver.json
  - Two schedule triggers:
    - hourly: every 1 hour (cron: `0 * * * *`)
    - daily: at 09:00 local (cron: `0 9 * * *`)
  - On trigger it sequentially issues three HTTP POST calls to the agent gateway (using env `N8N_AGENT_GATEWAY_URL`):
    1. roi_snapshot with `since: "7d"` and listed metrics
    2. publish_content to TikTok in dry_run
    3. email_followup to "Warm Leads" in dry_run
  - Adds a stub Function “Evaluate+Adjust” node that timestamps & echoes prior results.

- trading_hook.json
  - Webhook: POST /webhook/trading-hook
  - Auth: validates `X-AGENT-KEY`
  - Stub response: `{ ok:true, accepted:true, simulated_fill:{ symbol, side, size, price:123.45 } }`

Environment
- /ops/env/.env.example
  - N8N_TOOL_SECRET=CHANGE_ME_NOW
  - N8N_AGENT_GATEWAY_URL=http://localhost:5678/webhook/agent-tools
  - GENERIC_TIMEZONE=America/New_York

Importing workflows into n8n
- Via n8n UI: top-right Import → choose the JSON file and import.
- Via CLI in container (replace <file> with actual path inside container):
  - docker exec -u node -it n8n n8n import:workflow --input=/home/node/<file>.json
- Example commands (replace with full file path in container or copy files into container before):
  - docker exec -u node -it n8n n8n import:workflow --input=/home/node/ops/n8n/agent_tools_gateway.json
  - docker exec -u node -it n8n n8n import:workflow --input=/home/node/ops/n8n/empire_daily_driver.json
  - docker exec -u node -it n8n n8n import:workflow --input=/home/node/ops/n8n/trading_hook.json

Setting env & restarting
- In Docker Compose or container env, set:
  - N8N_TOOL_SECRET=<secure-secret>
  - N8N_AGENT_GATEWAY_URL=http://<host>:<port>/webhook/agent-tools
  - GENERIC_TIMEZONE as desired
- Restart n8n service (example Docker Compose):
  - docker-compose down && docker-compose up -d
- If using a single n8n container, ensure these env vars are available to the container at start.

Exact curl tests (copy/paste)
- /ops/tests/curl-examples.sh (also shown below) is executable and contains runnable curl calls:

  ./ops/tests/curl-examples.sh

Mapping to Agent Builder tools (bodies expected)
- publish_content
  - { "tool":"publish_content", "args": { "channel":"tiktok", "action":"draft", "caption":"...", "utm_campaign":"...", "dry_run":true } }
- roi_snapshot
  - { "tool":"roi_snapshot", "args": { "since":"7d", "metrics":[ "revenue","orders","aov","email_signups" ] } }
- email_followup
  - { "tool":"email_followup", "args": { "audience":"Warm Leads", "subject":"...", "body":"...", "send_at":"now", "dry_run":true } }
- trading_execute
  - { "tool":"trading_execute", "args": { "symbol":"EURUSD", "side":"buy", "size":1000, "mode":"paper" } }

Approval pattern
- Set args.require_approval = true
- Gateway returns 200 with body: { ok:false, needs_approval:true, plan:{ tool, args } } and no side-effects.

CI (what it does)
- Action: /.github/workflows/validate-n8n.yml
- Runs on push and pull_request
- Installs jq and validates each JSON under /ops/n8n:
  - Ensures files are parseable JSON
  - Ensures each has `.nodes` and `.connections` keys (basic n8n import readiness)
- Prints helpful import commands if all checks pass.

Security notes
- Replace CHANGE_ME_NOW in .env with a strong secret before exposing gateway.
- Keep network-level restrictions on n8n instance and use HTTPS/proxy in production.

Next steps (one short paragraph)
- Replace the stub Function nodes with real API integrations: TikTok / YouTube publishing SDKs or headless browser posting flows for publish_content; Shopify/analytics queries and database snapshots for roi_snapshot; Brevo/SendGrid/SMTP for email_followup with proper rate-limiting and templating; and for trading_execute wire the trading-hook to your broker SDK (OANDA/BinanceUS) with secure API credential storage and sandbox/paper modes. Add logging/observability and a production secrets manager for N8N_TOOL_SECRET and trading keys.

I walk in divine power, wisdom, and sovereignty — this stack is deterministic, guarded, and ready for upgrade to live integrations.