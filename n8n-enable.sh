#!/usr/bin/env bash
# n8n-enable.sh
# Purpose: Enable and start n8n automation stack for Dominion Empire.
# Safety: Uses placeholder secrets. Real secrets must be set via environment or secure files.
# Run as UID 1000 (recommended):
#   sudo -u "#1000" bash ./n8n-enable.sh
#
# Prerequisites:
#   - Docker and Docker Compose installed
#   - /opt/dominion directory structure created
#   - Real secrets configured in /opt/dominion/infra/.env.n8n.secrets
#
# Revert / undo: Run n8n-recover.sh to restore from backup
# Testing: run locally with dry-run mode: DRY_RUN=1 bash ./n8n-enable.sh
set -euo pipefail
IFS=$'\n\t'

# Configuration
N8N_VERSION="${N8N_VERSION:-latest}"
N8N_PORT="${N8N_PORT:-5678}"
N8N_DATA_DIR="${N8N_DATA_DIR:-/opt/dominion/n8n_data}"
N8N_SECRETS_FILE="${N8N_SECRETS_FILE:-/opt/dominion/infra/.env.n8n.secrets}"
COMPOSE_FILE="${COMPOSE_FILE:-/opt/dominion/stack/docker-compose.yml}"
DRY_RUN="${DRY_RUN:-0}"

echo "========================================"
echo "n8n Automation Stack Enabler"
echo "========================================"
echo "User: $(id -un) (uid=$(id -u))"
echo "Date: $(date --utc +"%Y-%m-%d %H:%M:%S UTC")"
echo "Dry run: ${DRY_RUN}"
echo ""

# Safety check: verify we're not running as root
if [ "$(id -u)" -eq 0 ]; then
  echo "⚠️  WARNING: Running as root. Recommended to run as UID 1000."
  echo "   Use: sudo -u \"#1000\" bash ./n8n-enable.sh"
  echo ""
fi

# Function to create directory structure
setup_directories() {
  echo "📁 Setting up directory structure..."
  
  local dirs=(
    "/opt/dominion"
    "/opt/dominion/stack"
    "/opt/dominion/n8n_data"
    "/opt/dominion/infra"
  )
  
  for dir in "${dirs[@]}"; do
    if [ ! -d "${dir}" ]; then
      if [ "${DRY_RUN}" -eq 1 ]; then
        echo "   [DRY] Would create: ${dir}"
      else
        if mkdir -p "${dir}" 2>/dev/null; then
          echo "   ✓ Created: ${dir}"
        else
          echo "   ⚠️  Cannot create ${dir} (may need sudo)"
        fi
      fi
    else
      echo "   ✓ Exists: ${dir}"
    fi
  done
  echo ""
}

# Function to create placeholder secrets file
create_secrets_template() {
  echo "🔐 Checking secrets file..."
  
  if [ -f "${N8N_SECRETS_FILE}" ]; then
    echo "   ✓ Secrets file exists: ${N8N_SECRETS_FILE}"
    echo "   ⚠️  Using existing secrets (NOT overwriting)"
  else
    echo "   Creating placeholder secrets template..."
    
    local template="# n8n Secrets Configuration
# WARNING: Replace ALL placeholder values with real secrets!
# This file should NEVER be committed to version control.

# n8n Basic Auth (required)
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=<YOUR_N8N_USERNAME>
N8N_BASIC_AUTH_PASSWORD=<YOUR_N8N_PASSWORD>

# n8n Configuration
N8N_HOST=<YOUR_DOMAIN_OR_IP>
N8N_PORT=${N8N_PORT}
N8N_PROTOCOL=http
N8N_PATH=/

# Database Configuration (SQLite by default)
DB_TYPE=sqlite
DB_SQLITE_DATABASE=${N8N_DATA_DIR}/database.sqlite

# Webhook Configuration
WEBHOOK_URL=http://<YOUR_DOMAIN_OR_IP>:${N8N_PORT}/

# Execution Configuration
EXECUTIONS_PROCESS=main
EXECUTIONS_DATA_SAVE_ON_ERROR=all
EXECUTIONS_DATA_SAVE_ON_SUCCESS=all

# Tool Gateway Secret (for agent integrations)
N8N_TOOL_SECRET=<YOUR_SUPER_SECRET_KEY>

# External Service API Keys (add as needed)
# YOUTUBE_API_KEY=<YOUR_YOUTUBE_KEY>
# GUMROAD_TOKEN=<YOUR_GUMROAD_TOKEN>
# BREVO_API_KEY=<YOUR_BREVO_KEY>
# TIKTOK_CLIENT_ID=<YOUR_TIKTOK_CLIENT_ID>
# TIKTOK_CLIENT_SECRET=<YOUR_TIKTOK_SECRET>
"
    
    if [ "${DRY_RUN}" -eq 1 ]; then
      echo "   [DRY] Would create: ${N8N_SECRETS_FILE}"
    else
      if echo "${template}" > "${N8N_SECRETS_FILE}" 2>/dev/null; then
        chmod 600 "${N8N_SECRETS_FILE}" 2>/dev/null || true
        echo "   ✓ Created template: ${N8N_SECRETS_FILE}"
        echo "   ⚠️  IMPORTANT: Edit this file and replace all <PLACEHOLDER> values!"
      else
        echo "   ⚠️  Cannot create ${N8N_SECRETS_FILE} (may need sudo)"
      fi
    fi
  fi
  echo ""
}

# Function to create or update docker-compose.yml
create_compose_file() {
  echo "🐳 Checking Docker Compose configuration..."
  
  if [ -f "${COMPOSE_FILE}" ]; then
    echo "   ✓ Compose file exists: ${COMPOSE_FILE}"
    echo "   ⚠️  Using existing configuration (NOT overwriting)"
  else
    echo "   Creating Docker Compose configuration..."
    
    local compose_config="version: '3.9'

services:
  n8n:
    image: n8nio/n8n:${N8N_VERSION}
    container_name: n8n
    restart: always
    ports:
      - \"${N8N_PORT}:5678\"
    volumes:
      - ${N8N_DATA_DIR}:/home/node/.n8n
    env_file:
      - ${N8N_SECRETS_FILE}
    environment:
      - NODE_ENV=production
      - GENERIC_TIMEZONE=America/New_York
    healthcheck:
      test: [\"CMD-SHELL\", \"wget --no-verbose --tries=1 --spider http://localhost:5678/healthz || exit 1\"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
"
    
    if [ "${DRY_RUN}" -eq 1 ]; then
      echo "   [DRY] Would create: ${COMPOSE_FILE}"
    else
      if echo "${compose_config}" > "${COMPOSE_FILE}" 2>/dev/null; then
        echo "   ✓ Created: ${COMPOSE_FILE}"
      else
        echo "   ⚠️  Cannot create ${COMPOSE_FILE} (may need sudo)"
      fi
    fi
  fi
  echo ""
}

# Function to import workflow
import_workflow() {
  echo "📋 Importing n8n workflow..."
  
  local workflow_source="./n8n workflow"
  local workflow_temp="/tmp/agent_tools_gateway.json"
  
  if [ ! -f "${workflow_source}" ]; then
    echo "   ⚠️  Workflow source not found: ${workflow_source}"
    echo "   Skipping workflow import"
    return
  fi
  
  # Extract JSON from the workflow file (lines between cat and docker commands)
  if [ "${DRY_RUN}" -eq 1 ]; then
    echo "   [DRY] Would extract and import workflow from: ${workflow_source}"
  else
    # Extract JSON content between 'cat > /tmp/agent_tools_gateway.json' and next command
    local extracted_json
    extracted_json=$(awk '/cat > \/tmp\/agent_tools_gateway.json/{flag=1;next}/^#|^docker/{flag=0}flag' "${workflow_source}")
    
    if echo "${extracted_json}" | grep -q "name"; then
      echo "${extracted_json}" > "${workflow_temp}"
      echo "   ✓ Workflow JSON extracted to: ${workflow_temp}"
      echo "   ℹ️  To import into n8n container, run:"
      echo "      docker cp ${workflow_temp} n8n:/home/node/agent_tools_gateway.json"
      echo "      docker exec -u node n8n n8n import:workflow --input=/home/node/agent_tools_gateway.json"
    else
      echo "   ⚠️  Could not extract workflow JSON"
    fi
  fi
  echo ""
}

# Function to start services
start_services() {
  echo "🚀 Starting n8n services..."
  
  if [ ! -f "${COMPOSE_FILE}" ]; then
    echo "   ⚠️  Compose file not found: ${COMPOSE_FILE}"
    echo "   Cannot start services"
    return
  fi
  
  if [ "${DRY_RUN}" -eq 1 ]; then
    echo "   [DRY] Would run: docker compose -f ${COMPOSE_FILE} up -d"
  else
    if command -v docker &> /dev/null; then
      if cd "$(dirname "${COMPOSE_FILE}")" && docker compose up -d; then
        echo "   ✓ Services started"
        echo ""
        echo "   Status:"
        docker compose ps
      else
        echo "   ⚠️  Failed to start services (check Docker installation and permissions)"
      fi
    else
      echo "   ⚠️  Docker not found. Install Docker first."
    fi
  fi
  echo ""
}

# Main execution
main() {
  setup_directories
  create_secrets_template
  create_compose_file
  import_workflow
  start_services
  
  echo "========================================"
  echo "✅ n8n Enable Complete"
  echo "========================================"
  echo ""
  echo "Next steps:"
  echo "  1. Edit ${N8N_SECRETS_FILE} and replace all <PLACEHOLDER> values"
  echo "  2. Restart services: cd $(dirname "${COMPOSE_FILE}") && docker compose restart"
  echo "  3. Access n8n at: http://localhost:${N8N_PORT}"
  echo "  4. Import workflow manually if not done automatically"
  echo "  5. Create backup: bash ./n8n-recover.sh backup"
  echo ""
  echo "Security reminders:"
  echo "  - NEVER commit ${N8N_SECRETS_FILE} to version control"
  echo "  - Use strong passwords for N8N_BASIC_AUTH_PASSWORD"
  echo "  - Use firewall rules to restrict access to port ${N8N_PORT}"
  echo "  - Keep regular backups of ${N8N_DATA_DIR}"
  echo ""
}

# Run main function
main
