#!/bin/bash
# Section 01-env — which environment is active, and is a rebuild running.
#
# Extracted VERBATIM from check-status.sh's inline `check_environment` on
# 2026-08-16. It moved for uniformity, not behaviour: sections.sh maps every
# section to a script so a second orchestrator can run the list without
# importing the first one's shell functions.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
# shellcheck disable=SC2034
source "${SCRIPT_DIR}/../scripts/lib/colors.sh" 2>/dev/null || {
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;36m'
    NC='\033[0m'
}

running=$(docker ps --format '{{.Names}}' 2>/dev/null |
    grep -oE 'scitex-hub-(dev|staging|prod)-' |
    sed 's/scitex-hub-//' | sed 's/-//' |
    sort -u | tr '\n' ' ' | xargs || echo "")

echo "📊 Environment:"
if [ -n "$running" ]; then
    echo "  [OK] Active: $running"
else
    echo -e "  ${YELLOW}[WARN] No active environment${NC}"
fi

# Rebuild detection
rebuild_pid=$(pgrep -f "docker buildx bake\|docker build\|docker-compose.*build\|docker compose.*build" 2>/dev/null | head -1 || true)
if [ -n "$rebuild_pid" ]; then
    echo -e "  ${YELLOW}[WARN] Rebuild in progress (PID: $rebuild_pid)${NC}"
fi
