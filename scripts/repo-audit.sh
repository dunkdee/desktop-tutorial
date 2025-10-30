#!/usr/bin/env bash
# scripts/repo-audit.sh
# Purpose: Produce an audit report for Dominion Empire repos and local /opt/dominion paths.
# Safety: Read-only. Does NOT print secret values. References to secret files are shown as file paths only.
# Run as UID 1000 (recommended):
#   sudo -u "#1000" bash ./scripts/repo-audit.sh
#
# Revert / undo: none required (read-only).
# Testing: run locally; output is written to audit-report.txt
set -euo pipefail
IFS=$'\n\t'

TIMESTAMP=$(date --utc +"%Y%m%dT%H%M%SZ")
OUTFILE="audit-report-${TIMESTAMP}.txt"

echo "Dominion repo audit - $(date --utc +"%Y-%m-%d %H:%M:%SZ" ) (UTC)" > "${OUTFILE}"
echo "" >> "${OUTFILE}"

# Helper: safe print header
hdr() {
  echo "================================================================" >> "${OUTFILE}"
  echo "$1" >> "${OUTFILE}"
  echo "----------------------------------------------------------------" >> "${OUTFILE}"
}

hdr "System info"
echo "User: $(id -un) (uid=$(id -u) gid=$(id -g))" >> "${OUTFILE}"
echo "Hostname: $(hostname -f 2>/dev/null || hostname)" >> "${OUTFILE}"
echo "PWD: $(pwd)" >> "${OUTFILE}"
echo "" >> "${OUTFILE}"

# 1) Find Dockerfiles in repo tree
hdr "Repository: Dockerfile locations (relative paths)"
if find . -maxdepth 6 -type f -name Dockerfile | sed -e 's/^/ - /' | tee -a "${OUTFILE}"; then
  true
else
  echo " - none found" >> "${OUTFILE}"
fi
echo "" >> "${OUTFILE}"

# 2) Check for docker-compose files (including the canonical /opt/dominion path)
hdr "docker-compose.yml checks"
# Look in repo
if find . -maxdepth 6 -type f -name 'docker-compose*.y*ml' | sed -e 's/^/ - /' | tee -a "${OUTFILE}"; then
  true
else
  echo " - none found in repo" >> "${OUTFILE}"
fi
echo "" >> "${OUTFILE}"

# Local /opt/dominion canonical path checks (do not show secret contents)
hdr "Local expected paths (existence checks)"
for path in "/opt/dominion/stack/docker-compose.yml" "/opt/dominion/n8n_data" "/opt/dominion/infra/.env.n8n.secrets"; do
  if [ -e "${path}" ]; then
    echo " - EXISTS: ${path}" >> "${OUTFILE}"
    # If it's a file, show size and perms but not contents
    if [ -f "${path}" ]; then
      echo "   size: $(stat -c%s "${path}") bytes; perms: $(stat -c%a "${path}")" >> "${OUTFILE}"
    fi
  else
    echo " - MISSING: ${path}" >> "${OUTFILE}"
  fi
done
echo "" >> "${OUTFILE}"

# 3) GitHub Actions workflows present in repository
hdr ".github/workflows (CI) files"
if [ -d ".github/workflows" ]; then
  find .github/workflows -maxdepth 1 -type f -name '*.y*ml' -printf " - %f\n" >> "${OUTFILE}" || true
else
  echo " - .github/workflows directory not present" >> "${OUTFILE}"
fi
echo "" >> "${OUTFILE}"

# 4) Search for references to /opt/dominion/infra/.env.n8n.secrets and any .env.* references
hdr "References to canonical secrets file and env usage (paths only)"
# Only show file paths and the matching line with filename and line number; do NOT output variable values
grep -RIn --line-number --exclude-dir=.git --exclude-dir=node_modules --binary-files=without-match "/opt/dominion/infra/.env.n8n.secrets" . 2>/dev/null | sed -e 's/^/ - /' >> "${OUTFILE}" || true
echo "" >> "${OUTFILE}"

hdr "References to common n8n env var names (filename:lineno:matching-line-summary)"
# List occurrences of common env names but redact values
GREP_LIST="N8N_BASIC_AUTH_ACTIVE|N8N_HOST|N8N_PORT|N8N_PROTOCOL|DB_TYPE|DB_SQLITE_DATABASE|DB_POSTGRESDB_HOST|WEBHOOK_URL|EXECUTIONS_PROCESS"
grep -RIn --line-number --exclude-dir=.git --exclude-dir=node_modules --binary-files=without-match -E "${GREP_LIST}" . 2>/dev/null \
  | sed -E 's/(:[0-9]+:)(.*)/\1<matching-line-suppressed>/' \
  | sed -e 's/^/ - /' >> "${OUTFILE}" || true
echo "" >> "${OUTFILE}"

# 5) List any Docker Compose services referencing 'n8n'
hdr "docker-compose service snippets (search for 'n8n' in compose files)"
find . -maxdepth 6 -type f -name 'docker-compose*.y*ml' -print0 | xargs -0 -n1 grep -In --line-number -E "n8n|N8N" 2>/dev/null | sed -e 's/^/ - /' >> "${OUTFILE}" || true
# Also check canonical path
if [ -f "/opt/dominion/stack/docker-compose.yml" ]; then
  echo "" >> "${OUTFILE}"
  echo "Canonical compose (/opt/dominion/stack/docker-compose.yml) -> service names:" >> "${OUTFILE}"
  grep -E "^[[:space:]]{0,}[^#[:space:]][^:]*:" /opt/dominion/stack/docker-compose.yml 2>/dev/null | sed -e 's/^/ - /' >> "${OUTFILE}" || true
fi
echo "" >> "${OUTFILE}"

# 6) Check for expected backup files in /opt/dominion/n8n_data (don't list contents)
hdr "Local DB backup files (in /opt/dominion/n8n_data) - names only"
if [ -d "/opt/dominion/n8n_data" ]; then
  ls -1 /opt/dominion/n8n_data | sed -e 's/^/ - /' >> "${OUTFILE}" || true
else
  echo " - /opt/dominion/n8n_data not present" >> "${OUTFILE}"
fi
echo "" >> "${OUTFILE}"

# 7) Quick git status summary (if in a git repo)
hdr "Git status (branch, uncommitted changes summary)"
if [ -d .git ]; then
  git rev-parse --abbrev-ref HEAD 2>/dev/null | awk '{print " - branch: "$0}' >> "${OUTFILE}" || true
  git status --porcelain --untracked-files=no | sed -e 's/^/ - /' | head -n 50 >> "${OUTFILE}" || true
else
  echo " - not a git repo (no .git)" >> "${OUTFILE}"
fi
echo "" >> "${OUTFILE}"

# 8) Recommendations (high-level)
hdr "Recommendations (automated suggestions)"
cat >> "${OUTFILE}" <<'EOF'
 - Ensure /opt/dominion/infra/.env.n8n.secrets exists and is mounted into n8n container as file (do NOT commit values).
 - If no Dockerfile found for services that should be containerized, create small Dockerfiles and CI build steps.
 - Add .github/workflows/build-and-deploy.yml (CI) to build images and run health-checked import step.
 - Keep regular DB backups in /opt/dominion/n8n_data and verify restore process (see docs/runbook.md).
 - Ensure sensitive files are listed in .gitignore and not committed.
EOF

echo "" >> "${OUTFILE}"
echo "Audit report written to: ${OUTFILE}"
echo ""
echo "Next steps (examples):" >> "${OUTFILE}"
echo " - Run: sudo -u \"#1000\" bash ./scripts/repo-audit.sh" >> "${OUTFILE}"
echo " - Create PRs adding Dockerfile/CI/etc per recommendations" >> "${OUTFILE}"

# Also print summary to stdout
cat "${OUTFILE}"
