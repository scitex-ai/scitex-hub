#!/bin/bash
# Host User Requirements Checker
# Validates that required system users exist with correct UIDs/GIDs
# Environment-aware: dev uses existing UID 1000 user, prod requires 'scitex' user

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
# shellcheck disable=SC2034
source "${SCRIPT_DIR}/../scripts/lib/colors.sh" 2>/dev/null || {
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;36m'
    NC='\033[0m'
}

# Determine environment from argument or running containers
ENV="${1:-}"
if [ -z "$ENV" ]; then
    # Auto-detect from running containers
    RUNNING=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -oE 'scitex-hub-(dev|prod)-' | head -1 | sed 's/scitex-hub-//' | sed 's/-//' || echo "")
    ENV="${RUNNING:-dev}"
fi

# Required UID for SLURM jobs
REQUIRED_UID=1000

echo "🔑 Host Users:"

# Get user at UID 1000
existing_user=$(id -nu "$REQUIRED_UID" 2>/dev/null || echo "")

if [ -z "$existing_user" ]; then
    # No user at UID 1000 - this is a problem for both environments
    echo -e "  ${RED}[FAIL] No user at UID ${REQUIRED_UID}${NC}"
    echo -e "    SLURM jobs will fail with 'Error generating job credential'"
    if [ "$ENV" = "prod" ]; then
        echo -e "    Fix: sudo deployment/host-setup/scripts/create-scitex-user.sh"
    else
        echo -e "    Fix: Create a user with UID ${REQUIRED_UID} (or use existing user)"
    fi
elif [ "$ENV" = "prod" ]; then
    # Production environment: Requires 'scitex' user specifically
    if [ "$existing_user" = "scitex" ]; then
        echo "  [OK] User 'scitex' at UID ${REQUIRED_UID}"
    else
        echo -e "  ${RED}[FAIL] UID ${REQUIRED_UID} taken by wrong user '${existing_user}' (production requires 'scitex')${NC}"
        echo -e "    This will cause SLURM job credential errors!"
        echo -e "    Fix: Reassign UID ${REQUIRED_UID} to 'scitex' user"
    fi
else
    # Dev environment: Any user at UID 1000 is acceptable
    # Container will sync to use host's UID 1000 user
    echo "  [OK] UID ${REQUIRED_UID} exists (user: '${existing_user}')"
    if [ "$existing_user" != "scitex" ]; then
        echo -e "    Note: Dev mode - container will sync with host UID"
    fi
fi

# Show explanation if there's an issue
if [ -z "$existing_user" ] || { [ "$ENV" = "prod" ] && [ "$existing_user" != "scitex" ]; }; then
    echo ""
    echo -e "  ${YELLOW}Why this matters:${NC}"
    echo -e "    SLURM validates job credentials against /etc/passwd on the compute node."
    echo -e "    The Docker container runs as UID ${REQUIRED_UID}, but if that UID doesn't"
    echo -e "    exist on the host, slurmd will reject jobs with 'Error generating job credential'."
fi

exit 0
