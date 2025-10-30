#!/usr/bin/env bash
# n8n-recover.sh
# Purpose: Backup and recover n8n automation data for Dominion Empire.
# Safety: Read-only for backup operations. Restore requires confirmation.
# Run as UID 1000 (recommended):
#   sudo -u "#1000" bash ./n8n-recover.sh backup
#   sudo -u "#1000" bash ./n8n-recover.sh restore <backup-file>
#
# Prerequisites:
#   - n8n services running (for backup)
#   - Backup file available (for restore)
#
# Revert / undo: Restoring creates a pre-restore backup automatically
# Testing: run backup command with DRY_RUN=1 bash ./n8n-recover.sh backup
set -euo pipefail
IFS=$'\n\t'

# Configuration
N8N_DATA_DIR="${N8N_DATA_DIR:-/opt/dominion/n8n_data}"
BACKUP_DIR="${BACKUP_DIR:-/opt/dominion/backups}"
N8N_CONTAINER_NAME="${N8N_CONTAINER_NAME:-n8n}"
DRY_RUN="${DRY_RUN:-0}"

# Functions
usage() {
  cat <<EOF
Usage: $0 <command> [options]

Commands:
  backup              Create a backup of n8n data
  restore <file>      Restore from a backup file
  list                List available backups
  verify <file>       Verify a backup file
  
Options:
  DRY_RUN=1          Run in dry-run mode (no changes)
  
Examples:
  $0 backup
  $0 restore /opt/dominion/backups/n8n-backup-20231030.tar.gz
  $0 list
  $0 verify /opt/dominion/backups/n8n-backup-20231030.tar.gz

Environment Variables:
  N8N_DATA_DIR       Path to n8n data directory (default: /opt/dominion/n8n_data)
  BACKUP_DIR         Path to backup directory (default: /opt/dominion/backups)
  DRY_RUN           Set to 1 for dry-run mode (default: 0)
EOF
  exit 1
}

print_header() {
  echo "========================================"
  echo "$1"
  echo "========================================"
  echo "User: $(id -un) (uid=$(id -u))"
  echo "Date: $(date --utc +"%Y-%m-%d %H:%M:%S UTC")"
  echo "Dry run: ${DRY_RUN}"
  echo ""
}

# Safety check: verify we're not running as root
check_user() {
  if [ "$(id -u)" -eq 0 ]; then
    echo "⚠️  WARNING: Running as root. Recommended to run as UID 1000."
    echo "   Use: sudo -u \"#1000\" bash ./n8n-recover.sh $1"
    echo ""
  fi
}

# Backup function
do_backup() {
  print_header "n8n Backup"
  check_user "backup"
  
  # Check if data directory exists
  if [ ! -d "${N8N_DATA_DIR}" ]; then
    echo "❌ Error: n8n data directory not found: ${N8N_DATA_DIR}"
    echo "   Make sure n8n is set up and data directory exists."
    exit 1
  fi
  
  # Create backup directory if it doesn't exist
  if [ ! -d "${BACKUP_DIR}" ]; then
    echo "📁 Creating backup directory: ${BACKUP_DIR}"
    if [ "${DRY_RUN}" -eq 1 ]; then
      echo "   [DRY] Would create: ${BACKUP_DIR}"
    else
      if mkdir -p "${BACKUP_DIR}" 2>/dev/null; then
        echo "   ✓ Created: ${BACKUP_DIR}"
      else
        echo "   ⚠️  Cannot create ${BACKUP_DIR} (may need sudo)"
        exit 1
      fi
    fi
  fi
  
  # Generate backup filename with timestamp
  local timestamp=$(date --utc +"%Y%m%dT%H%M%SZ")
  local backup_file="${BACKUP_DIR}/n8n-backup-${timestamp}.tar.gz"
  
  echo "📦 Creating backup..."
  echo "   Source: ${N8N_DATA_DIR}"
  echo "   Target: ${backup_file}"
  echo ""
  
  if [ "${DRY_RUN}" -eq 1 ]; then
    echo "   [DRY] Would create tarball of: ${N8N_DATA_DIR}"
    echo "   [DRY] Would save to: ${backup_file}"
  else
    # Create tarball (exclude any lock files or temporary files)
    if tar -czf "${backup_file}" \
         --exclude='*.lock' \
         --exclude='*.tmp' \
         -C "$(dirname "${N8N_DATA_DIR}")" \
         "$(basename "${N8N_DATA_DIR}")"; then
      
      local size=$(stat -c%s "${backup_file}" 2>/dev/null || echo "unknown")
      local size_mb=$((size / 1024 / 1024))
      
      echo "   ✓ Backup created successfully"
      echo "   File: ${backup_file}"
      echo "   Size: ${size_mb} MB"
      echo ""
      
      # Create a metadata file
      local metadata_file="${backup_file}.meta"
      cat > "${metadata_file}" <<EOF
# Backup Metadata
Timestamp: ${timestamp}
Date: $(date --utc +"%Y-%m-%d %H:%M:%S UTC")
User: $(id -un) (uid=$(id -u))
Hostname: $(hostname)
Source: ${N8N_DATA_DIR}
Size: ${size} bytes (${size_mb} MB)
Checksum: $(sha256sum "${backup_file}" | awk '{print $1}')
EOF
      echo "   ✓ Metadata saved: ${metadata_file}"
    else
      echo "   ❌ Backup failed"
      exit 1
    fi
  fi
  
  echo ""
  echo "✅ Backup Complete"
  echo ""
  echo "To restore this backup:"
  echo "   bash ./n8n-recover.sh restore ${backup_file}"
  echo ""
}

# Restore function
do_restore() {
  local backup_file="$1"
  
  print_header "n8n Restore"
  check_user "restore"
  
  # Verify backup file exists
  if [ ! -f "${backup_file}" ]; then
    echo "❌ Error: Backup file not found: ${backup_file}"
    exit 1
  fi
  
  echo "📋 Restore Information:"
  echo "   Backup file: ${backup_file}"
  echo "   Target directory: ${N8N_DATA_DIR}"
  echo ""
  
  # Show metadata if available
  local metadata_file="${backup_file}.meta"
  if [ -f "${metadata_file}" ]; then
    echo "📝 Backup Metadata:"
    cat "${metadata_file}" | sed 's/^/   /'
    echo ""
  fi
  
  # Verify tarball
  echo "🔍 Verifying backup file integrity..."
  if tar -tzf "${backup_file}" > /dev/null 2>&1; then
    echo "   ✓ Backup file is valid"
  else
    echo "   ❌ Backup file is corrupted or invalid"
    exit 1
  fi
  echo ""
  
  # Safety confirmation
  if [ "${DRY_RUN}" -eq 0 ]; then
    echo "⚠️  WARNING: This will replace current n8n data!"
    echo ""
    echo "   Current data location: ${N8N_DATA_DIR}"
    echo "   Backup will be created at: ${BACKUP_DIR}/pre-restore-backup-$(date --utc +"%Y%m%dT%H%M%SZ").tar.gz"
    echo ""
    read -p "   Type 'yes' to continue: " confirm
    
    if [ "${confirm}" != "yes" ]; then
      echo "   Restore cancelled."
      exit 0
    fi
    echo ""
  fi
  
  # Create pre-restore backup
  if [ -d "${N8N_DATA_DIR}" ] && [ "${DRY_RUN}" -eq 0 ]; then
    echo "💾 Creating pre-restore backup..."
    local pre_backup="${BACKUP_DIR}/pre-restore-backup-$(date --utc +"%Y%m%dT%H%M%SZ").tar.gz"
    
    if tar -czf "${pre_backup}" \
         --exclude='*.lock' \
         --exclude='*.tmp' \
         -C "$(dirname "${N8N_DATA_DIR}")" \
         "$(basename "${N8N_DATA_DIR}")"; then
      echo "   ✓ Pre-restore backup created: ${pre_backup}"
    else
      echo "   ⚠️  Pre-restore backup failed (continuing anyway)"
    fi
    echo ""
  fi
  
  # Stop n8n services before restore
  echo "🛑 Stopping n8n services..."
  if [ "${DRY_RUN}" -eq 1 ]; then
    echo "   [DRY] Would stop ${N8N_CONTAINER_NAME} container"
  else
    if command -v docker &> /dev/null; then
      docker stop "${N8N_CONTAINER_NAME}" 2>/dev/null || echo "   ⚠️  ${N8N_CONTAINER_NAME} container not running or already stopped"
    fi
  fi
  echo ""
  
  # Restore data
  echo "📥 Restoring data..."
  if [ "${DRY_RUN}" -eq 1 ]; then
    echo "   [DRY] Would extract: ${backup_file}"
    echo "   [DRY] Would extract to: $(dirname "${N8N_DATA_DIR}")"
  else
    # Remove old data directory
    if [ -d "${N8N_DATA_DIR}" ]; then
      rm -rf "${N8N_DATA_DIR}" || {
        echo "   ❌ Failed to remove old data directory"
        exit 1
      }
    fi
    
    # Extract backup
    if tar -xzf "${backup_file}" -C "$(dirname "${N8N_DATA_DIR}")"; then
      echo "   ✓ Data restored successfully"
    else
      echo "   ❌ Restore failed"
      exit 1
    fi
  fi
  echo ""
  
  # Start n8n services
  echo "🚀 Starting n8n services..."
  if [ "${DRY_RUN}" -eq 1 ]; then
    echo "   [DRY] Would start ${N8N_CONTAINER_NAME} container"
  else
    if command -v docker &> /dev/null; then
      if docker start "${N8N_CONTAINER_NAME}" 2>/dev/null; then
        echo "   ✓ ${N8N_CONTAINER_NAME} container started"
        sleep 3
        docker ps --filter "name=${N8N_CONTAINER_NAME}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
      else
        echo "   ⚠️  Could not start ${N8N_CONTAINER_NAME} container"
        echo "   You may need to start it manually: docker start ${N8N_CONTAINER_NAME}"
      fi
    fi
  fi
  echo ""
  
  echo "✅ Restore Complete"
  echo ""
  echo "Next steps:"
  echo "   1. Verify n8n is running: docker ps | grep ${N8N_CONTAINER_NAME}"
  echo "   2. Check logs: docker logs ${N8N_CONTAINER_NAME}"
  echo "   3. Access n8n UI and verify workflows"
  echo ""
}

# List backups function
do_list() {
  print_header "n8n Backup List"
  
  if [ ! -d "${BACKUP_DIR}" ]; then
    echo "📁 Backup directory not found: ${BACKUP_DIR}"
    echo "   No backups available."
    exit 0
  fi
  
  echo "📋 Available backups in: ${BACKUP_DIR}"
  echo ""
  
  # Find all backup files
  local count=0
  while IFS= read -r -d '' backup; do
    count=$((count + 1))
    local size=$(stat -c%s "${backup}" 2>/dev/null || echo "0")
    local size_mb=$((size / 1024 / 1024))
    local date=$(stat -c%y "${backup}" 2>/dev/null | cut -d' ' -f1,2 | cut -d'.' -f1)
    
    echo "[$count] $(basename "${backup}")"
    echo "    Size: ${size_mb} MB"
    echo "    Date: ${date}"
    
    # Show metadata if available
    local meta="${backup}.meta"
    if [ -f "${meta}" ]; then
      if grep -q "Checksum:" "${meta}"; then
        local checksum=$(grep "Checksum:" "${meta}" | cut -d' ' -f2)
        echo "    SHA256: ${checksum:0:16}..."
      fi
    fi
    echo ""
  done < <(find "${BACKUP_DIR}" -name "n8n-backup-*.tar.gz" -type f -print0 | sort -rz)
  
  if [ ${count} -eq 0 ]; then
    echo "   No backups found."
  else
    echo "Total: ${count} backup(s)"
  fi
  echo ""
}

# Verify backup function
do_verify() {
  local backup_file="$1"
  
  print_header "n8n Backup Verification"
  
  if [ ! -f "${backup_file}" ]; then
    echo "❌ Error: Backup file not found: ${backup_file}"
    exit 1
  fi
  
  echo "🔍 Verifying: ${backup_file}"
  echo ""
  
  # Check file size
  local size=$(stat -c%s "${backup_file}" 2>/dev/null || echo "0")
  local size_mb=$((size / 1024 / 1024))
  echo "   Size: ${size_mb} MB"
  
  # Verify tarball integrity
  echo ""
  echo "   Testing archive integrity..."
  if tar -tzf "${backup_file}" > /dev/null 2>&1; then
    echo "   ✓ Archive is valid and can be extracted"
  else
    echo "   ❌ Archive is corrupted or invalid"
    exit 1
  fi
  
  # List contents
  echo ""
  echo "   Archive contents:"
  tar -tzf "${backup_file}" | head -20 | sed 's/^/      /'
  local total_files=$(tar -tzf "${backup_file}" | wc -l)
  echo "      ... (${total_files} files total)"
  
  # Check metadata
  local metadata_file="${backup_file}.meta"
  if [ -f "${metadata_file}" ]; then
    echo ""
    echo "   Metadata file found:"
    cat "${metadata_file}" | sed 's/^/      /'
    
    # Verify checksum if present
    if grep -q "Checksum:" "${metadata_file}"; then
      echo ""
      echo "   Verifying checksum..."
      local expected=$(grep "Checksum:" "${metadata_file}" | awk '{print $2}')
      local actual=$(sha256sum "${backup_file}" | awk '{print $1}')
      
      if [ "${expected}" = "${actual}" ]; then
        echo "   ✓ Checksum verified: ${actual:0:16}..."
      else
        echo "   ⚠️  Checksum mismatch!"
        echo "      Expected: ${expected:0:16}..."
        echo "      Actual:   ${actual:0:16}..."
      fi
    fi
  else
    echo ""
    echo "   ⚠️  Metadata file not found: ${metadata_file}"
  fi
  
  echo ""
  echo "✅ Verification Complete"
  echo ""
}

# Main execution
main() {
  if [ $# -eq 0 ]; then
    usage
  fi
  
  local command="$1"
  shift
  
  case "${command}" in
    backup)
      do_backup
      ;;
    restore)
      if [ $# -eq 0 ]; then
        echo "❌ Error: restore requires a backup file argument"
        echo ""
        usage
      fi
      do_restore "$1"
      ;;
    list)
      do_list
      ;;
    verify)
      if [ $# -eq 0 ]; then
        echo "❌ Error: verify requires a backup file argument"
        echo ""
        usage
      fi
      do_verify "$1"
      ;;
    *)
      echo "❌ Error: Unknown command: ${command}"
      echo ""
      usage
      ;;
  esac
}

# Run main function
main "$@"
