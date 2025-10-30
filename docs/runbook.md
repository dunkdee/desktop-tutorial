# Dominion Empire — n8n Runbook (minimal)

Purpose
- Quick reference to backup, rollback, import workflows, and secret handling for the Dominion Empire n8n deployment.

Prerequisites
- You have shell access to the VM hosting n8n.
- The operator user (UID 1000) has permission to read/write /opt/dominion/n8n_data and run docker/docker-compose.
- Secrets are stored in `/opt/dominion/infra/.env.n8n.secrets` (do NOT commit this file).

Important: Secrets
- Never copy secret values into PRs, logs, or CI config. Use placeholders: `<<SECRET:NAME>>`.
- The canonical secrets file path (local): `/opt/dominion/infra/.env.n8n.secrets`
- Schema (example keys — do not include values):
  - N8N_BASIC_AUTH_ACTIVE=<<SECRET:N8N_BASIC_AUTH_ACTIVE>>
  - N8N_HOST=<<SECRET:N8N_HOST>>
  - DB_TYPE=<<SECRET:DB_TYPE>>
  - DB_* (postgres/sqlite connection strings) = <<SECRET:DB_CONNECTION>>
  - WEBHOOK_URL=<<SECRET:WEBHOOK_URL>>

Rollback and Recovery (file-based backups)
1. Backups
   - Backups are tarballs created under `/opt/dominion/n8n_data/` by the import script:
     - e.g. `/opt/dominion/n8n_data/backup-n8n-20250101T120000Z.tar.gz`

2. Revert command (example)
   - As root / a user with filesystem access:
     - tar xzf /opt/dominion/n8n_data/backup-n8n-YYYYMMDDTHHMMSSZ.tar.gz -C /
     - docker-compose -f /opt/dominion/stack/docker-compose.yml down
     - docker-compose -f /opt/dominion/stack/docker-compose.yml up -d

3. SQLite edits (if any SQL edits required)
   - Follow this pattern to ensure foreign key safety and consistent backups:
     PRAGMA foreign_keys=OFF;
     BEGIN;
     -- your SQL changes here
     COMMIT;
     PRAGMA foreign_keys=ON;
     VACUUM;
   - Always create a timestamped DB backup before running SQL.

Importing Workflows (operator quick command)
- Place JSON workflow files as `/tmp/n8n_import_*.json` on the host.
- Run the import script as UID 1000:
  - sudo -u "#1000" bash ./scripts/health-and-import.sh
- The script will:
  - Wait for `http://127.0.0.1:5678/healthz` (configurable via `$N8N_HEALTH_URL`)
  - Create a timestamped backup of `/opt/dominion/n8n_data`
  - Copy files into the running n8n container and run `n8n import:workflow` as UID 1000

Secrets and CI
- Provide a script (separate PR) to document secret schema and generate a safe mirror file of secret *names* for CI.
- Use repository secrets for CI (e.g., REGISTRY_PASSWORD, DEPLOY_SSH_KEY). Do NOT store secret values in repository files.

CI/CD notes
- Minimal GitHub Action is provided at `.github/workflows/build-and-deploy.yml`.
- The deploy step is intentionally a placeholder: you must supply registry host, credentials, and target host/SSH credentials as secrets.

Testing and Verification
- After imports:
  - Check n8n UI to confirm workflows are visible.
  - For webhook workflows, run the smoke test (trigger the webhook) and observe the execution logs.
  - Monitor container logs: `docker logs -f <container-id-or-name>`

Audit & Troubleshooting
- Use `scripts/repo-audit.sh` to produce an audit-report-*.txt that lists Dockerfiles, compose files, CI status, and secret references.
- If an import fails, restore from the backup tarball and inspect n8n container logs for the import command output.

Contact / Handover
- All changes should be small, auditable, and reversible. If you need assistance, open an issue in the repo with the audit report attached.
