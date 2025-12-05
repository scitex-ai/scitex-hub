#!/bin/bash
# Terminal Readiness Checker
# Tests if terminals will actually work (not just if components exist)
# This catches issues like SLURM needing restart after user creation

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../scripts/lib/colors.sh" 2>/dev/null || {
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;36m'; NC='\033[0m'
}

SCITEX_USER="scitex"
ENV="${1:-nas}"
CONTAINER_NAME="scitex-cloud-${ENV}-django-1"

check_status=0

# Quick test: Can SLURM actually execute jobs as scitex user?
# This catches the "SLURM needs restart" issue
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$" 2>/dev/null; then
    # Container is running, test SLURM job execution
    if timeout 3 docker exec "${CONTAINER_NAME}" su "${SCITEX_USER}" -c "srun --partition=express true" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Terminals ready (SLURM job execution verified)${NC}"
    else
        echo -e "${RED}✗ Terminals NOT ready (SLURM job execution failed)${NC}"
        echo -e "${YELLOW}  Cause: SLURM services likely need restart after user creation${NC}"
        echo -e "${YELLOW}  Fix: sudo deployment/host-setup/scripts/restart-slurm-for-new-user.sh${NC}"
        check_status=1
    fi
else
    echo -e "${YELLOW}⚠ Django container not running - cannot test terminals${NC}"
    check_status=1
fi

exit $check_status
