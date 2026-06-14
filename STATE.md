# Dominion Empire — STATE.md
> Session memory. Read this first. Update before every push.

## Last Updated
2026-06-14 — Session opened by Claude on `claude/vm-status-check-s0800x`

## North Star
Walk in divine power, wisdom, and sovereignty. Every project aligns with abundance, visibility, victory. Revenue first. One dollar earned beats a perfect system nobody's paying for.

---

## Ground Truth (verified this session)

### Domain / Production
| Target | Status | Notes |
|---|---|---|
| `dominionhealing.org` | **UNKNOWN** | Blocked from this container — requires prod VM or browser check |
| `api.dominionhealing.org/healthz` | **UNKNOWN** | Same — egress blocked from Claude container |
| Gumroad checkout (Divine Sovereignty) | **UNKNOWN** | Can't reach api.gumroad.com from this container |
| Docker stack on prod VM | **UNKNOWN** | No SSH access from this container |
| n8n Gateway | **UNKNOWN** | Gateway URL redacted in session notes |

> **Critical:** This Claude container cannot reach `dominionhealing.org`, `api.gumroad.com`, or any prod service. All live checks must be done on the actual production VM or by the operator in a browser.

### Repo — What Exists and is Code-Complete
| App | Path | Stack | Status |
|---|---|---|---|
| Baby API | `api/app.py` | Flask, port 8080 | Code complete. Checks YouTube, Gumroad, OANDA, Binance, Brevo env vars |
| Dominion Healing web | `web/public/index.html` + nginx | Static HTML/Nginx | Code complete. Marketing landing page |
| Jarvis orchestrator | `apps/jarvis/worker.py` | Python + Redis | Code complete. Redis heartbeat loop |
| FastAPI notify (email) | `apps/api/main.py` | FastAPI + Brevo | Code complete. `/notify` + `/healthz` |
| YouTube pipeline | `apps/youtube/` | Python + Claude Fable 5 | Code complete. Script gen → video → upload |
| TikTok uploader | `apps/tiktok/main.py` | FastAPI | Code complete. Locked to `lawrence72` account |
| Next.js frontend | `apps/frontend/` | Next.js 14 | Dependencies listed. Pages not fully built out |
| n8n workflows | `.github/workflows/` | GitHub Actions | cron-status, deploy, baby CI/CD, netlify sync |

### CI/CD
| Workflow | Trigger | Verified |
|---|---|---|
| `baby.yml` | Push to main → SSH deploy + Docker restart | Not live-tested this session |
| `cron-status.yml` | Every 30 min → n8n gateway smoke test | Depends on `N8N_AGENT_GATEWAY_URL` secret |
| `deploy.yml` | Push/manual → GCP build + push | Depends on GCP secrets |
| `netlify_sync_env.yml` | Manual | Netlify env sync |

---

## In Progress
- [ ] **Divine Sovereignty Gumroad checkout** — Needs live verification on prod VM. Code exists in `api/app.py:/gumroad`. Unknown if product is published and selling.
- [ ] **TikTok worker** — Code complete but OAuth flow not tested. Needs `TIKTOK_CLIENT_ID`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REDIRECT_URI` to be set.
- [ ] **Trading paper-mode tests** — OANDA integration exists in `api/app.py:/oanda`. Not live-tested.
- [ ] **Next.js frontend** — `apps/frontend/pages/` not populated. Shell only.

## Blocked
- Live service health checks — this container's egress policy blocks all prod domains. Must verify from prod VM or browser.

## Completed (confirmed by git history)
- [x] Baby API + Logger Docker service
- [x] Dominion Healing static web (Nginx)
- [x] n8n automation scripts (`n8n-enable.sh`, `n8n-recover.sh`)
- [x] CI/CD workflows (baby, cron-status, deploy, netlify)
- [x] YouTube pipeline (Claude Fable 5 + Higgins)
- [x] Repo audit script (`OPS/repo-audit.sh`)
- [x] Session notes / runbooks

## Parking Lot
- Shopify KPI store
- Domain wiring & SSL (CNAME is set to `dominionhealing.org`)
- Higgins video API key — needed for YouTube pipeline to fully run

---

## Operating Rules (Dewayne's Law)
1. Look first — confirm a file exists before referencing it
2. Read STATE.md + dominion_log.txt at session start
3. Nothing is done until there's real output proving it
4. Use GCP API for VM power; SSH for services; never SSH a powered-off box
5. Make fixes idempotent — running twice must not break anything
6. One revenue action per session before infrastructure polish
7. Update STATE.md + dominion_log.txt + push at end of every session
