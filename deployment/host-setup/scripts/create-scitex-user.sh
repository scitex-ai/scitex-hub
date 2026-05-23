#!/bin/bash
# Create scitex system user on host for SLURM job execution
# This user MUST exist on all SLURM compute nodes for job credential validation

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/colors.sh" 2>/dev/null || {
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;36m'; NC='\033[0m'
}

SCITEX_UID=1000
SCITEX_USER="scitex"

echo -e "${BLUE}Creating ${SCITEX_USER} user on host...${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root or with sudo${NC}"
    echo -e "Usage: sudo $0"
    exit 1
fi

# Check if user already exists
if id "${SCITEX_USER}" &>/dev/null; then
    actual_uid=$(id -u "${SCITEX_USER}")
    if [ "$actual_uid" -eq "$SCITEX_UID" ]; then
        echo -e "${GREEN}✓ User '${SCITEX_USER}' already exists with correct UID ${SCITEX_UID}${NC}"
        exit 0
    else
        echo -e "${RED}✗ User '${SCITEX_USER}' exists but has wrong UID: ${actual_uid}${NC}"
        echo -e "${YELLOW}Please manually fix this UID conflict${NC}"
        exit 1
    fi
fi

# Check if UID is already taken
if id "$SCITEX_UID" &>/dev/null; then
    existing_user=$(id -nu "$SCITEX_UID")
    echo -e "${RED}✗ UID ${SCITEX_UID} is already taken by user '${existing_user}'${NC}"
    echo -e "${YELLOW}Cannot create '${SCITEX_USER}' with this UID. Please resolve manually.${NC}"
    exit 1
fi

# Create the user
echo -e "${BLUE}Creating system user '${SCITEX_USER}' with UID ${SCITEX_UID}...${NC}"
useradd -r -u "$SCITEX_UID" -m -s /bin/bash -c "SciTeX Hub Service User" "${SCITEX_USER}"

# Verify creation
if id "${SCITEX_USER}" &>/dev/null; then
    actual_uid=$(id -u "${SCITEX_USER}")
    echo -e "${GREEN}✓ User '${SCITEX_USER}' created successfully with UID ${actual_uid}${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  IMPORTANT: SLURM services must be restarted to pick up the new user${NC}"
    echo -e "${BLUE}Next step: ${NC}sudo deployment/host-setup/scripts/restart-slurm-for-new-user.sh"
else
    echo -e "${RED}✗ Failed to create user '${SCITEX_USER}'${NC}"
    exit 1
fi
