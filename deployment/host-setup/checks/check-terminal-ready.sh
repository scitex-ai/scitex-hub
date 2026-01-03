#!/bin/bash
# Terminal Readiness Checker
# Tests if terminals will actually work (not just if components exist)
# This catches issues like SLURM needing restart after user creation
# Environment-aware: dev uses root, NAS uses scitex user

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../scripts/lib/colors.sh" 2>/dev/null || {
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;36m'; NC='\033[0m'
}

ENV="${1:-}"
if [ -z "$ENV" ]; then
    # Auto-detect from running containers
    RUNNING=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -oE 'scitex-cloud-(dev|nas)-' | head -1 | sed 's/scitex-cloud-//' | sed 's/-//' || echo "")
    ENV="${RUNNING:-dev}"
fi

CONTAINER_NAME="scitex-cloud-${ENV}-django-1"

# Determine which user to test as based on environment
if [ "$ENV" = "nas" ]; then
    TEST_USER="scitex"
    USER_CMD="su ${TEST_USER} -c"
else
    # Dev runs as root - test directly
    TEST_USER="root"
    USER_CMD=""
fi

check_status=0

# Check terminal readiness with smart detection
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$" 2>/dev/null; then
    # Container is running

    # First check: Are there running terminal jobs? (proves terminals work)
    RUNNING_TERMINALS=$(squeue -h --name=terminal --state=R 2>/dev/null | wc -l)
    if [ "$RUNNING_TERMINALS" -gt 0 ]; then
        echo -e "${GREEN}✓ Terminals ready (${RUNNING_TERMINALS} active session(s))${NC}"
        exit 0
    fi

    # Second check: Can SLURM execute jobs? (3s timeout, may fail if resources busy)
    if [ -n "$USER_CMD" ]; then
        TEST_CMD="timeout 3 docker exec ${CONTAINER_NAME} ${USER_CMD} \"srun --partition=express true\""
    else
        TEST_CMD="timeout 3 docker exec ${CONTAINER_NAME} srun --partition=express true"
    fi

    if eval "$TEST_CMD" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Terminals ready (SLURM job execution verified)${NC}"
    else
        # Job may have timed out due to resource contention, check queue status
        QUEUED_JOBS=$(squeue -h --name=true 2>/dev/null | wc -l)
        if [ "$QUEUED_JOBS" -gt 0 ]; then
            echo -e "${YELLOW}⚠ Terminals: SLURM busy (jobs queued, but controller responding)${NC}"
            check_status=0  # Not a failure - just busy
        else
            echo -e "${RED}✗ Terminals NOT ready (SLURM job execution failed)${NC}"
            echo -e "${YELLOW}  Cause: SLURM services likely need restart after user creation${NC}"
            echo -e "${YELLOW}  Fix: sudo deployment/host-setup/scripts/restart-slurm-for-new-user.sh${NC}"
            check_status=1
        fi
    fi
else
    echo -e "${YELLOW}⚠ Django container not running - cannot test terminals${NC}"
    check_status=1
fi

exit $check_status
