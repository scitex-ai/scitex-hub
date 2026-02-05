#!/bin/bash
# Host User Requirements Checker
# Validates that required system users exist with correct UIDs/GIDs
# Environment-aware: dev uses existing UID 1000 user, prod requires 'scitex' user

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../scripts/lib/colors.sh" 2>/dev/null || {
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;36m'; NC='\033[0m'
}

# Determine environment from argument or running containers
ENV="${1:-}"
if [ -z "$ENV" ]; then
    # Auto-detect from running containers
    RUNNING=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -oE 'scitex-cloud-(dev|prod)-' | head -1 | sed 's/scitex-cloud-//' | sed 's/-//' || echo "")
    ENV="${RUNNING:-dev}"
fi

# Required UID for SLURM jobs
REQUIRED_UID=1000

check_status=0

echo -e "${BLUE}Checking host user requirements...${NC}"

# Get user at UID 1000
existing_user=$(id -nu "$REQUIRED_UID" 2>/dev/null || echo "")

if [ -z "$existing_user" ]; then
    # No user at UID 1000 - this is a problem for both environments
    echo -e "${RED}✗ No user exists with UID ${REQUIRED_UID}${NC}"
    echo -e "${YELLOW}  SLURM jobs will fail with 'Error generating job credential'${NC}"
    if [ "$ENV" = "prod" ]; then
        echo -e "${YELLOW}  Fix: sudo deployment/host-setup/scripts/create-scitex-user.sh${NC}"
    else
        echo -e "${YELLOW}  Fix: Create a user with UID ${REQUIRED_UID} (or use existing user)${NC}"
    fi
    check_status=1
elif [ "$ENV" = "prod" ]; then
    # Production environment: Requires 'scitex' user specifically
    if [ "$existing_user" = "scitex" ]; then
        echo -e "${GREEN}✓ User 'scitex' exists with UID ${REQUIRED_UID}${NC}"
    else
        echo -e "${RED}✗ UID ${REQUIRED_UID} is taken by user '${existing_user}' (production requires 'scitex')${NC}"
        echo -e "${YELLOW}  This will cause SLURM job credential errors!${NC}"
        echo -e "${YELLOW}  Fix: Reassign UID ${REQUIRED_UID} to 'scitex' user${NC}"
        check_status=1
    fi
else
    # Dev environment: Any user at UID 1000 is acceptable
    # Container will sync to use host's UID 1000 user
    echo -e "${GREEN}✓ UID ${REQUIRED_UID} exists (user: '${existing_user}')${NC}"
    if [ "$existing_user" != "scitex" ]; then
        echo -e "${YELLOW}  Note: Dev mode - container will sync with host UID${NC}"
    fi
fi

# Show explanation if there's an issue
if [ "$check_status" -ne 0 ]; then
    echo ""
    echo -e "${YELLOW}Why this matters:${NC}"
    echo -e "  SLURM validates job credentials against /etc/passwd on the compute node."
    echo -e "  The Docker container runs as UID ${REQUIRED_UID}, but if that UID doesn't"
    echo -e "  exist on the host, slurmd will reject jobs with 'Error generating job credential'."
    echo ""
fi

exit $check_status
