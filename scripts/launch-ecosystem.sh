#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

info() { echo "[INFO] $*"; }
err() { echo "[ERROR] $*" >&2; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    err "Required command not found: $1"
    exit 1
  }
}

require_cmd docker
require_cmd curl

if ! docker compose version >/dev/null 2>&1; then
  err "Docker Compose v2 plugin is required (docker compose ...)."
  exit 1
fi

if [[ ! -f .env ]]; then
  if [[ -f .env.production.example ]]; then
    info "No .env found. Bootstrapping from .env.production.example"
    cp .env.production.example .env
    info "Populate .env with real secrets before production deployment."
  else
    err "No .env and no .env.production.example found."
    exit 1
  fi
fi

info "Starting ecosystem (build + detach)..."
docker compose up -d --build

check_url() {
  local name="$1"
  local url="$2"
  local retries="${3:-20}"
  local delay="${4:-3}"

  for ((i=1; i<=retries; i++)); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      info "$name is healthy: $url"
      return 0
    fi
    sleep "$delay"
  done

  err "$name failed health check: $url"
  return 1
}

check_url "Baby API" "http://localhost:8080/"
check_url "Dominion Web" "http://localhost/health"

info "Stack is up. Active services:"
docker compose ps
