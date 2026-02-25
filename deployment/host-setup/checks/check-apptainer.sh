#!/bin/bash
# Apptainer Container Status Checker
# Validates SIF file, .def hash, data directory, and permissions
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
    xargs || echo "")

DEF_FILE="${PROJECT_ROOT}/deployment/singularity/scitex-cloud-shared-v0.1.0.def"
HASH_FILE="${PROJECT_ROOT}/deployment/singularity/.def-hash"

if echo "$RUNNING" | grep -q "prod"; then
    SIF_PATH="/opt/scitex/singularity/scitex-cloud-shared-v0.1.0.sif"
    DATA_PATH="/opt/scitex/data/users"
else
    # Dev: use project-local paths
    SIF_PATH="${PROJECT_ROOT}/deployment/singularity/scitex-cloud-shared-v0.1.0.sif"
    DATA_PATH="${PROJECT_ROOT}/data/users"
fi

SIF_OK=true

if [ -f "$SIF_PATH" ]; then
    SIF_SIZE=$(du -h "$SIF_PATH" | cut -f1)
    SIF_DATE=$(date -r "$SIF_PATH" "+%Y-%m-%d %H:%M")
    echo "  [OK] SIF: ${SIF_PATH} (${SIF_SIZE}, built ${SIF_DATE})"

    # Check if .def has changed since last build
    if [ -f "$DEF_FILE" ] && [ -f "$HASH_FILE" ]; then
        CURRENT_HASH=$(sha256sum "$DEF_FILE" | awk '{print $1}')
        STORED_HASH=$(cat "$HASH_FILE" 2>/dev/null || echo "")
        if [ "$CURRENT_HASH" != "$STORED_HASH" ]; then
            echo -e "  ${YELLOW}[WARN] .def changed since build -- rebuild recommended${NC}"
            echo -e "    Run: make apptainer-build"
            SIF_OK=false
        fi
    elif [ -f "$DEF_FILE" ] && [ ! -f "$HASH_FILE" ]; then
        echo -e "  ${YELLOW}[WARN] No build hash -- cannot verify SIF matches .def${NC}"
        echo -e "    Run: make apptainer-build  (skips if unchanged)"
    fi

    # Prod: check scitex user can read it
    if echo "$RUNNING" | grep -q "prod"; then
        if ! sudo -u scitex test -r "$SIF_PATH" 2>/dev/null; then
            echo -e "  ${RED}[FAIL] SIF not readable by scitex${NC}"
            SIF_OK=false
        fi
    fi
else
    echo -e "  ${RED}[FAIL] SIF not found: ${SIF_PATH}${NC}"
    echo -e "    Build: make apptainer-build"
    SIF_OK=false
fi

# Check data directory
if [ -d "$DATA_PATH" ]; then
    echo -e "  [OK] Data dir: ${DATA_PATH}"
else
    echo -e "  ${RED}[FAIL] Data dir not found: ${DATA_PATH}${NC}"
    SIF_OK=false
fi

if [ "$SIF_OK" = false ] && echo "$RUNNING" | grep -q "prod"; then
    echo -e "  ${YELLOW}[WARN] Terminal may not work -- fix issues above${NC}"
    echo -e "    Setup: sudo ./deployment/host-setup/scripts/setup-slurm-paths.sh"
fi

exit 0
