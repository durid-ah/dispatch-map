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
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

show_help() {
  cat << EOF
Usage: ./run-dev.sh <command> [args...]

Development Commands:
  api           Run FastAPI in dev mode (packages/api)
  web           Run the Vite frontend (packages/web)
  consumer      Run the dispatch consumer (packages/dispatch-consumer)
  docker        Run all services in Docker Compose (dev mode)

Spec-Driven Development (SDD) Commands:
  spec:export   Export OpenAPI schema from FastAPI offline
  spec:types    Export OpenAPI schema and regenerate frontend TypeScript types
  spec:verify   Run the full contract verification pipeline (tests, typegen, build, lint)

Help:
  help          Show this help message

Examples:
  ./run-dev.sh api
  ./run-dev.sh spec:types
  ./run-dev.sh spec:verify
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

  spec:export)
    log_info "Exporting FastAPI OpenAPI JSON schema..."
    uv run python packages/api/export_openapi.py
    log_success "OpenAPI schema exported to packages/api/openapi.json"
    ;;

  spec:types)
    log_info "Exporting FastAPI OpenAPI schema..."
    uv run python packages/api/export_openapi.py
    log_info "Generating TypeScript types for web package..."
    npm run typegen --prefix packages/web
    log_success "TypeScript types regenerated in packages/web/src/types/api.generated.ts"
    ;;

  spec:verify)
    log_info "1/5: Running Python API tests..."
    uv run python -m unittest discover packages/api/tests
    log_info "2/5: Running DB model contract tests..."
    uv run python -m unittest discover packages/db/tests
    log_info "3/5: Running Consumer parser fixture tests..."
    uv run python -m unittest discover packages/dispatch-consumer/tests
    log_info "4/5: Checking OpenAPI schema & TypeScript contract sync..."
    uv run python packages/api/export_openapi.py
    npm run typegen:check --prefix packages/web
    log_info "5/5: Running frontend build & linter..."
    npm run build --prefix packages/web
    npm run lint --prefix packages/web
    echo ""
    log_success "All SDD verification gates passed successfully!"
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
