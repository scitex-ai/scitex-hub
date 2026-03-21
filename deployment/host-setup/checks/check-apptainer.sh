#!/bin/bash
# Apptainer Container Status Checker
# Validates SIF/sandbox, .def hash, data directory, and permissions
# Auto-detects environment from running containers

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

# shellcheck source=/dev/null
# shellcheck disable=SC2034
source "${SCRIPT_DIR}/../scripts/lib/colors.sh" 2>/dev/null || {
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;36m'
    NC='\033[0m'
}

echo "🔲 Apptainer:"

# Auto-detect environment from running containers
RUNNING=$(docker ps --format '{{.Names}}' 2>/dev/null |
    grep -oE 'scitex-cloud-(dev|staging|prod)-' |
    sed 's/scitex-cloud-//' |
    sed 's/-//' |
    sort -u |
    tr '\n' ' ' |
    xargs) || RUNNING=""

DEF_FILE="${PROJECT_ROOT}/deployment/singularity/scitex-cloud-shared-v0.1.0.def"
HASH_FILE="${PROJECT_ROOT}/deployment/singularity/.def-hash"
SINGULARITY_DIR="${PROJECT_ROOT}/deployment/singularity"

# Always check project-local paths first (NAS uses project dir for all envs)
# Fall back to /opt/scitex/ system paths if project paths don't exist
CONTAINER_PATH="${SINGULARITY_DIR}/current-sandbox"
SIF_PATH="${SINGULARITY_DIR}/scitex-cloud-shared-v0.1.0.sif"
DATA_PATH="${PROJECT_ROOT}/data/users"

if echo "$RUNNING" | grep -q "prod"; then
    # Prod: prefer project paths, fall back to /opt/scitex/
    if [ ! -L "$CONTAINER_PATH" ] && [ ! -d "$CONTAINER_PATH" ] && [ ! -f "$SIF_PATH" ]; then
        CONTAINER_PATH="/opt/scitex/singularity/current-sandbox"
        SIF_PATH="/opt/scitex/singularity/scitex-cloud-shared-v0.1.0.sif"
    fi
    DATA_PATH="/opt/scitex/data/users"
fi

CONTAINER_OK=true

# Check sandbox directory first (preferred mode)
if [ -L "$CONTAINER_PATH" ] && [ -d "$CONTAINER_PATH" ]; then
    ACTIVE_TARGET=$(readlink "$CONTAINER_PATH")
    SANDBOX_DATE=$(date -r "$CONTAINER_PATH" "+%Y-%m-%d %H:%M" 2>/dev/null || echo "unknown")
    echo "  [OK] Sandbox: ${ACTIVE_TARGET} (modified ${SANDBOX_DATE})"

    # Count available sandboxes for rollback
    SANDBOX_COUNT=$(find "$SINGULARITY_DIR" -maxdepth 1 -type d -name 'sandbox-*' 2>/dev/null | wc -l)
    if [ "$SANDBOX_COUNT" -gt 1 ]; then
        echo "  [OK] Rollback: ${SANDBOX_COUNT} sandboxes available"
    fi

    # Check if .def has changed since last build
    if [ -f "$DEF_FILE" ] && [ -f "$HASH_FILE" ]; then
        CURRENT_HASH=$(sha256sum "$DEF_FILE" | awk '{print $1}')
        STORED_HASH=$(cat "$HASH_FILE" 2>/dev/null || echo "")
        if [ "$CURRENT_HASH" != "$STORED_HASH" ]; then
            echo -e "  ${YELLOW}[WARN] .def changed since build -- rebuild recommended${NC}"
            echo -e "    Run: make apptainer-sandbox --force"
        fi
    fi

    # Prod: check scitex user can read it
    if echo "$RUNNING" | grep -q "prod"; then
        if ! sudo -n -u scitex test -r "$CONTAINER_PATH" 2>/dev/null; then
            # Check if it was a sudo auth failure vs actual permission issue
            if ! sudo -n true 2>/dev/null; then
                echo -e "  ${YELLOW}[WARN] Cannot check scitex read permission (sudo not cached)${NC}"
                echo -e "    Run: sudo -v && make ENV=prod status"
            else
                echo -e "  ${RED}[FAIL] Sandbox not readable by scitex${NC}"
                CONTAINER_OK=false
            fi
        fi
    fi
elif [ -d "$CONTAINER_PATH" ]; then
    # Non-symlink sandbox (unversioned legacy)
    SANDBOX_DATE=$(date -r "$CONTAINER_PATH" "+%Y-%m-%d %H:%M" 2>/dev/null || echo "unknown")
    echo -e "  ${YELLOW}[WARN] Unversioned sandbox: ${CONTAINER_PATH} (modified ${SANDBOX_DATE})${NC}"
    echo -e "    Rebuild with: make apptainer-sandbox --force"
elif [ -f "$SIF_PATH" ]; then
    SIF_DATE=$(date -r "$SIF_PATH" "+%Y-%m-%d %H:%M" 2>/dev/null || echo "unknown")
    echo -e "  ${YELLOW}[WARN] Using SIF (not sandbox): ${SIF_PATH} (built ${SIF_DATE})${NC}"
    echo -e "    Convert: make apptainer-sandbox"
else
    echo -e "  ${RED}[FAIL] No container found (sandbox or SIF)${NC}"
    echo -e "    Build: make apptainer-sandbox"
    CONTAINER_OK=false
fi

# Check data directory
if [ -d "$DATA_PATH" ]; then
    echo -e "  [OK] Data dir: ${DATA_PATH}"
else
    echo -e "  ${RED}[FAIL] Data dir not found: ${DATA_PATH}${NC}"
    CONTAINER_OK=false
fi

if [ "$CONTAINER_OK" = false ] && echo "$RUNNING" | grep -q "prod"; then
    echo -e "  ${YELLOW}[WARN] Terminal may not work -- fix issues above${NC}"
    echo -e "    Setup: sudo ./deployment/host-setup/scripts/setup-slurm-paths.sh"
fi

exit 0
