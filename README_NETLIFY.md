# Netlify Setup (NO-VM)
1) Connect repo to Netlify (Import project).
2) Set build command + publish dir per framework in Netlify UI:
   - Vite: `npm run build` → publish dir: `dist`
   - Create React App: `npm run build` → publish dir: `build`
   - Next.js (export): `npm run build` → publish dir: `out`
   - Next.js (SSR): Add `@netlify/plugin-nextjs` plugin
3) Add these GitHub Secrets (repo → Settings → Secrets and variables → Actions):
   - NETLIFY_AUTH_TOKEN, NETLIFY_SITE_ID
   - N8N_WEBHOOK_BASE, N8N_WEBHOOK_PATH (optional, defaults to /webhook/clean2), AGENT_HMAC_SECRET
   - (optional) BREVO_API_KEY, DEFAULT_FROM_EMAIL, DEFAULT_FROM_NAME,
     SHOPIFY_STORE_DOMAIN, SHOPIFY_ADMIN_API_TOKEN, SHOPIFY_WEBHOOK_SECRET,
     GUMROAD_TOKEN, OANDA_API_KEY, OANDA_ACCOUNT_ID, OANDA_ENV
4) Run the workflow "Sync Netlify Env from GitHub Secrets".
5) Test:
   curl -sS -X POST "https://<your-site>.netlify.app/api/agent-bridge" \
     -H "Content-Type: application/json" \
     -d '{"test":"message"}'
