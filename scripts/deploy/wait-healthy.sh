#!/bin/bash
# File: scripts/deploy/wait-healthy.sh
# Live-updating Docker health status display
# Polls container status every 2s with ANSI overwrite animation
# Exits when all containers are healthy or timeout reached
#
# Usage: ./wait-healthy.sh <env> [timeout_seconds]

set -euo pipefail

ENV="${1:?Usage: wait-healthy.sh <env> [timeout]}"
TIMEOUT="${2:-120}"
INTERVAL=2

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
DIM='\033[2m'
NC='\033[0m'

PREFIX="scitex-cloud-${ENV}-"

get_status() {
    docker ps --format '{{.Names}}\t{{.Status}}' 2>/dev/null |
        grep "^${PREFIX}" |
        sed "s/^${PREFIX}//" |
        sort
}

count_healthy() {
    local statuses="$1"
    echo "$statuses" | grep -c "(healthy)" 2>/dev/null || echo 0
}

count_total() {
    local statuses="$1"
    echo "$statuses" | grep -c . 2>/dev/null || echo 0
}

all_healthy() {
    local statuses="$1"
    local total
    total=$(count_total "$statuses")
    local healthy
    healthy=$(count_healthy "$statuses")
    [ "$total" -gt 0 ] && [ "$total" -eq "$healthy" ]
}

format_line() {
    local name="$1"
    local status="$2"

    if echo "$status" | grep -q "(healthy)"; then
        printf "  ${GREEN}✔${NC} %-35s ${GREEN}%s${NC}\n" "$name" "$status"
    elif echo "$status" | grep -q "(health: starting)"; then
        printf "  ${YELLOW}⟳${NC} %-35s ${YELLOW}%s${NC}\n" "$name" "$status"
    elif echo "$status" | grep -q "Restarting"; then
        printf "  ${RED}↻${NC} %-35s ${RED}%s${NC}\n" "$name" "$status"
    else
        printf "  ${DIM}?${NC} %-35s ${DIM}%s${NC}\n" "$name" "$status"
    fi
}

elapsed=0
line_count=0

while [ "$elapsed" -lt "$TIMEOUT" ]; do
    statuses=$(get_status)
    total=$(count_total "$statuses")
    healthy=$(count_healthy "$statuses")

    # Move cursor up to overwrite previous output
    if [ "$line_count" -gt 0 ]; then
        printf "\033[%dA" "$line_count"
    fi

    # Header
    if all_healthy "$statuses"; then
        printf "\r${GREEN}🐳 Docker: %d/%d healthy${NC}                    \n" "$healthy" "$total"
    else
        printf "\r${CYAN}🐳 Docker: %d/%d healthy${NC} ${DIM}(${elapsed}s)${NC}            \n" "$healthy" "$total"
    fi

    # Container lines
    line_count=1
    while IFS=$'\t' read -r name status; do
        [ -z "$name" ] && continue
        format_line "$name" "$status"
        line_count=$((line_count + 1))
    done <<<"$statuses"

    if all_healthy "$statuses"; then
        echo ""
        echo -e "${GREEN}✅ All containers healthy${NC}"
        exit 0
    fi

    sleep "$INTERVAL"
    elapsed=$((elapsed + INTERVAL))
done

echo ""
echo -e "${RED}⚠ Timeout: not all containers healthy after ${TIMEOUT}s${NC}"
echo -e "${YELLOW}  Run 'make status' to check current state${NC}"
exit 1
