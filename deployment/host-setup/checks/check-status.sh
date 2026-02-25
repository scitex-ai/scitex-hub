#!/bin/bash
# Master Status Check — Async Orchestrator
# Runs all sections in parallel; each prints as an atomic chunk.
# This is the single reliable source for admin's short-term memory.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

# shellcheck disable=SC1091
# shellcheck disable=SC2034
source "${SCRIPT_DIR}/../scripts/lib/colors.sh" 2>/dev/null || {
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;36m'
    NC='\033[0m'
}

# ── Temp dir for atomic section output ─────────────────────
TMPDIR_STATUS=$(mktemp -d)
trap 'rm -rf "$TMPDIR_STATUS"' EXIT

# Run a section: capture output to temp file, then print atomically
run_section() {
    local name="$1"
    shift
    "$@" >"${TMPDIR_STATUS}/${name}" 2>&1 || true
    cat "${TMPDIR_STATUS}/${name}"
    echo ""
}

# ── Inline section: Environment + Docker ───────────────────
check_environment() {
    local running
    running=$(docker ps --format '{{.Names}}' 2>/dev/null |
        grep -oE 'scitex-cloud-(dev|staging|prod)-' |
        sed 's/scitex-cloud-//' | sed 's/-//' |
        sort -u | tr '\n' ' ' | xargs || echo "")

    echo "📊 Environment:"
    if [ -n "$running" ]; then
        echo "  [OK] Active: $running"
    else
        echo -e "  ${YELLOW}[WARN] No active environment${NC}"
    fi

    # Rebuild detection
    local rebuild_pid
    rebuild_pid=$(pgrep -f "docker buildx bake\|docker build\|docker-compose.*build\|docker compose.*build" 2>/dev/null | head -1 || true)
    if [ -n "$rebuild_pid" ]; then
        echo -e "  ${YELLOW}[WARN] Rebuild in progress (PID: $rebuild_pid)${NC}"
    fi
}

check_docker() {
    local containers
    containers=$(docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null |
        grep -E "scitex-cloud-(dev|staging|prod)-" || echo "")

    echo "🐳 Docker:"
    if [ -n "$containers" ]; then
        echo "$containers" | while read -r line; do echo "  $line"; done
    else
        echo -e "  ${YELLOW}[WARN] No containers running${NC}"
    fi
}

# ── Launch all sections in parallel ────────────────────────
run_section "01-env" check_environment &
run_section "02-docker" check_docker &
run_section "03-migrations" "${SCRIPT_DIR}/check-migrations.sh" &
run_section "04-visitors" "${SCRIPT_DIR}/check-visitor-pool.sh" &
run_section "05-slurm" "${SCRIPT_DIR}/check-slurm.sh" &
run_section "06-host" "${SCRIPT_DIR}/check-users.sh" &
run_section "07-terminal" "${SCRIPT_DIR}/check-terminal-ready.sh" &
run_section "08-filesizes" "${PROJECT_ROOT}/scripts/maintenance/check_file_sizes.sh" &
run_section "09-apptainer" "${SCRIPT_DIR}/check-apptainer.sh" &
run_section "10-services" "${SCRIPT_DIR}/check-services.sh" &

wait

# ── Timestamp ──────────────────────────────────────────────
echo ""
date
