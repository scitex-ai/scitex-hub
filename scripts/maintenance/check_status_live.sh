#!/bin/bash
# Live Status Checker with Spinners
# Shows real-time status updates for SciTeX Cloud

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Spinner characters
SPINNER_CHARS="⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

# Show spinner while running command
# Usage: run_with_spinner "Checking containers" command args...
run_with_spinner() {
    local message="$1"
    shift
    local cmd=("$@")

    # Start spinner
    echo -n -e "${CYAN}⏳ ${message}...${NC} "

    # Run command in background
    local output
    local status
    output=$("${cmd[@]}" 2>&1) && status=0 || status=$?

    # Clear spinner line
    echo -e "\r\033[K${CYAN}${message}${NC}"

    # Return output and status
    echo "$output"
    return $status
}

# Quick check (no spinner, just fast output)
quick_check() {
    local message="$1"
    local check_cmd="$2"

    if eval "$check_cmd" >/dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} ${message}"
        return 0
    else
        echo -e "  ${RED}✗${NC} ${message}"
        return 1
    fi
}

# Main status check
main() {
    local ENV="${1:-prod}"

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║           SciTeX Cloud - Live Status                  ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Environment Status
    echo -e "${CYAN}📊 Environment Status:${NC}"
    RUNNING=$(docker ps --format '{{.Names}}' 2>/dev/null | \
        grep -oE 'scitex-cloud-(dev|prod)-' | \
        sed 's/scitex-cloud-//' | sed 's/-//' | \
        sort -u | tr '\n' ' ' | xargs || true)

    if [ -n "$RUNNING" ]; then
        echo -e "  ${CYAN}Active:${NC} ${GREEN}$RUNNING${NC}"
    else
        echo -e "  ${YELLOW}⚠️  No active environment${NC}"
    fi
    echo ""

    # Container Status
    echo -e "${CYAN}🐳 Container Status:${NC}"
    CONTAINERS=$(docker ps --format "{{.Names}}" 2>/dev/null | grep "scitex-cloud-$ENV-" || true)

    if [ -z "$CONTAINERS" ]; then
        echo -e "  ${YELLOW}No containers running${NC}"
    else
        while IFS= read -r container; do
            # Get container health
            HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "running")
            STATUS=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "unknown")

            if [ "$STATUS" = "running" ] && { [ "$HEALTH" = "healthy" ] || [ "$HEALTH" = "" ]; }; then
                echo -e "  ${GREEN}✓${NC} ${container}"
            elif [ "$STATUS" = "running" ]; then
                echo -e "  ${YELLOW}⚠${NC} ${container} (${HEALTH})"
            else
                echo -e "  ${RED}✗${NC} ${container} (${STATUS})"
            fi
        done <<< "$CONTAINERS"
    fi
    echo ""

    # SLURM Status
    echo -e "${CYAN}🖥️  SLURM Status:${NC}"
    if command -v sinfo >/dev/null 2>&1; then
        SLURM_STATUS=$(sinfo --noheader 2>&1 || true)
        if [ -n "$SLURM_STATUS" ] && ! echo "$SLURM_STATUS" | grep -q "error"; then
            echo -e "  ${GREEN}✓ SLURM Cluster: OPERATIONAL${NC}"
            sinfo --noheader 2>/dev/null | while read -r line; do
                echo "    $line"
            done
        else
            echo -e "  ${RED}✗ SLURM Cluster: NOT RESPONDING${NC}"
            echo -e "  ${YELLOW}💡 Run: make slurm-start${NC}"
        fi
    else
        echo -e "  ${YELLOW}⚠️  SLURM not installed${NC}"
    fi
    echo ""

    # Host Requirements (with spinners)
    echo -e "${CYAN}🔍 Host Requirements:${NC}"

    # User check
    if id scitex >/dev/null 2>&1; then
        UID_CHECK=$(id -u scitex)
        if [ "$UID_CHECK" -eq 1000 ]; then
            echo -e "  ${GREEN}✓${NC} scitex user (UID 1000)"
        else
            echo -e "  ${YELLOW}⚠${NC} scitex user exists but wrong UID: $UID_CHECK"
        fi
    else
        echo -e "  ${RED}✗${NC} scitex user missing"
        echo -e "    ${YELLOW}Fix: deployment/host-setup/scripts/create-scitex-user.sh${NC}"
    fi

    # SLURM services
    quick_check "slurmd service" "systemctl is-active --quiet slurmd"
    quick_check "slurmctld service" "systemctl is-active --quiet slurmctld"
    quick_check "munge service" "systemctl is-active --quiet munge"

    # Terminal functionality test
    echo ""
    echo -e "${CYAN}🖥️  Terminal Functionality:${NC}"
    if docker ps --format '{{.Names}}' | grep -q "^scitex-cloud-${ENV}-django-1$" 2>/dev/null; then
        echo -n -e "  ${CYAN}⏳ Testing SLURM job execution...${NC}"

        if timeout 3 docker exec "scitex-cloud-${ENV}-django-1" su scitex -c "srun --partition=express true" >/dev/null 2>&1; then
            echo -e "\r\033[K  ${GREEN}✓ Terminals ready (SLURM verified)${NC}"
        else
            echo -e "\r\033[K  ${RED}✗ Terminals NOT ready${NC}"
            echo -e "    ${YELLOW}Fix: sudo deployment/host-setup/scripts/restart-slurm-for-new-user.sh${NC}"
        fi
    else
        echo -e "  ${YELLOW}⚠ Django container not running - cannot test${NC}"
    fi

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}Status check complete!${NC} $(date '+%Y-%m-%d %H:%M:%S')"
}

# Run main
main "${1:-prod}"
