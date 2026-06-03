#!/bin/bash
# Test if terminal connections will work
# Verifies that SLURM can execute jobs as the scitex user (UID 1000)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/colors.sh" 2>/dev/null || {
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;36m'; NC='\033[0m'
}

SCITEX_UID=1000
SCITEX_USER="scitex"
ENV="${1:-prod}"  # Default to prod environment

echo -e "${BLUE}Testing terminal connection prerequisites...${NC}"
echo ""

# Test 1: Check if scitex user exists on host
echo -e "${BLUE}Test 1: Checking if scitex user exists on host...${NC}"
if id "${SCITEX_USER}" &>/dev/null; then
    actual_uid=$(id -u "${SCITEX_USER}")
    if [ "$actual_uid" -eq "$SCITEX_UID" ]; then
        echo -e "${GREEN}✓ User '${SCITEX_USER}' exists with correct UID ${SCITEX_UID}${NC}"
    else
        echo -e "${RED}✗ User '${SCITEX_USER}' has wrong UID: ${actual_uid} (expected ${SCITEX_UID})${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ User '${SCITEX_USER}' does not exist${NC}"
    echo -e "${YELLOW}  Run: sudo deployment/host-setup/scripts/create-scitex-user.sh${NC}"
    exit 1
fi

# Test 2: Check SLURM services
echo ""
echo -e "${BLUE}Test 2: Checking SLURM services...${NC}"
all_running=true

if systemctl is-active --quiet slurmd 2>/dev/null; then
    echo -e "${GREEN}✓ slurmd is running${NC}"
else
    echo -e "${RED}✗ slurmd is NOT running${NC}"
    all_running=false
fi

if systemctl is-active --quiet slurmctld 2>/dev/null; then
    echo -e "${GREEN}✓ slurmctld is running${NC}"
else
    echo -e "${RED}✗ slurmctld is NOT running${NC}"
    all_running=false
fi

if [ "$all_running" = false ]; then
    echo -e "${YELLOW}  Fix: make slurm-start${NC}"
    exit 1
fi

# Test 3: Check if Docker container is running
echo ""
echo -e "${BLUE}Test 3: Checking if Django container is running...${NC}"
CONTAINER_NAME="scitex-hub-${ENV}-django-1"
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${GREEN}✓ Container ${CONTAINER_NAME} is running${NC}"
else
    echo -e "${RED}✗ Container ${CONTAINER_NAME} is NOT running${NC}"
    echo -e "${YELLOW}  Start: make ENV=${ENV} start${NC}"
    exit 1
fi

# Test 4: Test SLURM job submission from container
echo ""
echo -e "${BLUE}Test 4: Testing SLURM job submission from container...${NC}"
echo -e "${BLUE}Running: docker exec ${CONTAINER_NAME} su scitex -c 'srun --partition=express whoami'${NC}"

# Run with timeout to avoid hanging
if timeout 10 docker exec "${CONTAINER_NAME}" su scitex -c "srun --partition=express whoami" >/dev/null 2>&1; then
    echo -e "${GREEN}✓ SLURM job executed successfully${NC}"
    echo -e "${GREEN}✓ Terminals should work!${NC}"
else
    exit_code=$?
    if [ $exit_code -eq 124 ]; then
        echo -e "${RED}✗ SLURM job timed out (likely credential error)${NC}"
    else
        echo -e "${RED}✗ SLURM job failed${NC}"
    fi
    echo ""
    echo -e "${YELLOW}This usually means SLURM needs to be restarted after creating the user:${NC}"
    echo -e "${BLUE}  sudo deployment/host-setup/scripts/restart-slurm-for-new-user.sh${NC}"
    echo ""
    echo -e "${YELLOW}To see the actual error:${NC}"
    echo -e "${BLUE}  docker exec ${CONTAINER_NAME} su scitex -c 'srun --partition=express whoami'${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     ✅ All Tests Passed - Terminals Should Work!      ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Test terminals at: https://scitex.ai${NC}"
