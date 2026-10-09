#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# Color formatting
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

show_help() {
  cat << EOF
Usage: ./run-dev.sh <command> [args...]

Commands:
  api         Run FastAPI in dev mode (packages/api)
  web         Run the Vite frontend (packages/web)
  consumer    Run the dispatch consumer (packages/dispatch-consumer)
  docker      Run all services in Docker Compose (dev mode)
  help        Show this help message

Examples:
  ./run-dev.sh api
  ./run-dev.sh web
  ./run-dev.sh consumer
  ./run-dev.sh docker
EOF
}

TARGET="${1:-help}"
shift || true

case "$TARGET" in
  api)
    log_info "Starting FastAPI dev server..."
    exec uv run fastapi dev packages/api/main.py "$@"
    ;;

  web)
    if [ ! -d "packages/web/node_modules" ]; then
      log_info "Installing web dependencies..."
      npm install --prefix packages/web
    fi
    log_info "Starting Vite frontend dev server..."
    exec npm run dev --prefix packages/web -- "$@"
    ;;

  consumer)
    log_info "Starting dispatch consumer..."
    exec uv run --directory packages/dispatch-consumer python main.py "$@"
    ;;

  docker|compose)
    log_info "Starting Docker Compose development environment..."
    exec docker compose up "$@"
    ;;

  help|-h|--help)
    show_help
    ;;

  *)
    log_error "Unknown command: '$TARGET'"
    echo ""
    show_help
    exit 1
    ;;
esac
