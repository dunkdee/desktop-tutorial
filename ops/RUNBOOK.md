# Dominion Ark Runbook

## Prod URLs
- Site: https://dominionhealing.org
- API:  https://api.dominionhealing.org/healthz

## Deploy
- Merge to `main` → Deploy (prod) runs automatically
- Re-run last job if you just updated secrets

## Server
SSH: `${PROD_SSH_USER}@${PROD_HOST}`
Path: `/opt/dominions-ark`

## Compose
    cd /opt/dominions-ark
    docker compose ps
    docker compose logs -f caddy
    docker compose logs -f api

## Secrets (set in Actions → Environments → prod)
- BREVO_API_KEY, OANDA_API_KEY, BINANCE_API_KEY, BINANCE_API_SECRET, COINGECKO_API_KEY, GUMROAD_TOKEN
- TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET
- YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, GOOGLE_MAPS_KEY

## Incident
- Rollback: revert last commit, push → CI redeploys last good build
- Hotfix: branch from main, PR, merge after checks