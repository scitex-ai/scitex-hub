#!/bin/bash
# Section 02-docker — container inventory, plus crash-loop detection.
#
# Extracted VERBATIM from check-status.sh's inline `check_docker` on
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

containers=$(docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null |
    grep -E "scitex-hub-(dev|staging|prod)-" || echo "")

echo "🐳 Docker:"
if [ -n "$containers" ]; then
    echo "$containers" | while read -r line; do echo "  $line"; done
else
    echo -e "  ${YELLOW}[WARN] No containers running${NC}"
fi

# Crash-loop detection: containers restarting with low uptime while others are stable
looping=""
while IFS= read -r line; do
    name=$(echo "$line" | awk '{print $1}')
    status=$(echo "$line" | cut -d' ' -f2-)
    # Match "Up N seconds" (under 60s) — sign of restart loop
    if echo "$status" | grep -qE "Up [0-9]+ seconds"; then
        looping="${looping}${name}\n"
    fi
done <<<"$containers"

if [ -n "$looping" ]; then
    # Only flag as loop if some containers are healthy (stable for minutes+)
    has_stable=$(echo "$containers" | grep -cE "Up [0-9]+ (minutes|hours|days)" || true)
    if [ "$has_stable" -gt 0 ]; then
        echo ""
        echo -e "  ${RED}[CRASH-LOOP] These containers keep restarting:${NC}"
        echo -e "$looping" | while read -r c; do
            [ -n "$c" ] && echo -e "    ${RED}→ $c${NC}"
        done
        echo -e "  ${YELLOW}Check logs: docker compose logs <service> --tail 50${NC}"
    fi
fi
