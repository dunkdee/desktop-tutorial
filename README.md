# Dominion Ecosystem Operating Guide

This repository now runs as a single deployable stack with clear startup, verification, and incident-response workflows.

## 1) One-command startup

```bash
bash scripts/launch-ecosystem.sh
```

What this does:
- verifies Docker + Docker Compose are available
- bootstraps `.env` from `.env.production.example` (first run only)
- builds and starts the stack in detached mode
- runs health checks for API and web services
- prints the active container table

## 2) Core service endpoints

- Baby API: `http://localhost:8080/`
- Baby API integrations: 
  - `http://localhost:8080/youtube`
  - `http://localhost:8080/gumroad`
  - `http://localhost:8080/oanda`
  - `http://localhost:8080/binance`
- Dominion web: `http://localhost/`
- Dominion web health: `http://localhost/health`

## 3) Daily operator commands (no fluff)

```bash
# check running services

docker compose ps

# stream logs

docker compose logs -f baby-api dominion-web

# restart stack

docker compose up -d --build

# hard reset (includes volumes)

docker compose down -v && docker compose up -d --build
```

## 4) Audit and governance

Run this before major releases:

```bash
bash scripts/repo-audit.sh
```

It creates a timestamped audit report with:
- compose and Dockerfile inventory
- CI workflow presence
- local path checks for canonical infrastructure paths
- secret-reference scans (without printing secret values)

## 5) CI/CD reliability

`/.github/workflows/deploy.yml` is configured to build and push the images that actually exist in this repo:
- `apps/api`
- `apps/jarvis`

This removes path drift and aligns automation with the current repository structure.

## 6) What was missing to be elite (now addressed)

To run like an enterprise-grade delivery system, you need hard gates before deploy.

Added now:
- `.github/workflows/elite-build.yml` that runs on PRs and `main` pushes
- syntax checks for shell + Python
- compose schema validation (`docker compose config`)
- deterministic image builds for `web`, `apps/api`, and `apps/jarvis`
- concurrency control to auto-cancel stale runs on the same branch

Result: deployment failures move left into CI instead of appearing after release.
