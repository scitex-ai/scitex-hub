#!/bin/bash
# Host User Requirements Checker
# Validates that required system users exist with correct UIDs/GIDs

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../scripts/lib/colors.sh" 2>/dev/null || {
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;36m'; NC='\033[0m'
}

# Required users configuration
REQUIRED_SCITEX_UID=1000
REQUIRED_SCITEX_USER="scitex"

check_status=0

echo -e "${BLUE}Checking host user requirements...${NC}"

# Check if scitex user exists with correct UID
if id "${REQUIRED_SCITEX_USER}" &>/dev/null; then
    actual_uid=$(id -u "${REQUIRED_SCITEX_USER}")
    if [ "$actual_uid" -eq "$REQUIRED_SCITEX_UID" ]; then
        echo -e "${GREEN}✓ User '${REQUIRED_SCITEX_USER}' exists with correct UID ${REQUIRED_SCITEX_UID}${NC}"
    else
        echo -e "${RED}✗ User '${REQUIRED_SCITEX_USER}' exists but has wrong UID: ${actual_uid} (expected ${REQUIRED_SCITEX_UID})${NC}"
        echo -e "${YELLOW}  Fix: sudo userdel ${REQUIRED_SCITEX_USER} && sudo useradd -r -u ${REQUIRED_SCITEX_UID} -m -s /bin/bash ${REQUIRED_SCITEX_USER}${NC}"
        check_status=1
    fi
elif id "$REQUIRED_SCITEX_UID" &>/dev/null; then
    existing_user=$(id -nu "$REQUIRED_SCITEX_UID")
    echo -e "${RED}✗ UID ${REQUIRED_SCITEX_UID} is taken by user '${existing_user}' (need '${REQUIRED_SCITEX_USER}')${NC}"
    echo -e "${YELLOW}  This will cause SLURM job credential errors!${NC}"
    echo -e "${YELLOW}  Fix: Either reassign UID ${REQUIRED_SCITEX_UID} to '${REQUIRED_SCITEX_USER}' or change container UID${NC}"
    check_status=1
else
    echo -e "${RED}✗ User '${REQUIRED_SCITEX_USER}' with UID ${REQUIRED_SCITEX_UID} does NOT exist${NC}"
    echo -e "${YELLOW}  This WILL cause terminal failures: 'Error generating job credential'${NC}"
    echo -e "${YELLOW}  Run: deployment/host-setup/scripts/create-scitex-user.sh${NC}"
    check_status=1
fi

# Check if UID 1000 exists (common issue)
if [ "$check_status" -ne 0 ]; then
    echo ""
    echo -e "${YELLOW}Why this matters:${NC}"
    echo -e "  SLURM validates job credentials against /etc/passwd on the compute node."
    echo -e "  The Docker container runs as UID ${REQUIRED_SCITEX_UID}, but if that UID doesn't"
    echo -e "  exist on the host, slurmd will reject jobs with 'Error generating job credential'."
    echo ""
fi

exit $check_status
