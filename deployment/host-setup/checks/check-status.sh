#!/bin/bash
# Master Status Check Script
# Orchestrates all status checks for make status
# This is the single reliable source for admin's short-term memory

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../scripts/lib/colors.sh" 2>/dev/null || {
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;36m'
    NC='\033[0m'
}

# ============================================
# Environment Status
# ============================================
echo -e "${BLUE}📊 Environment Status:${NC}"
RUNNING=$(docker ps --format '{{.Names}}' 2>/dev/null |
    grep -oE 'scitex-cloud-(dev|staging|prod)-' |
    sed 's/scitex-cloud-//' |
    sed 's/-//' |
    sort -u |
    tr '\n' ' ' |
    xargs || echo "")

if [ -n "$RUNNING" ]; then
    echo -e "  ${BLUE}Active environment:${NC} $RUNNING"
else
    echo -e "  ${YELLOW}⚠️  No active environment${NC}"
fi

# ============================================
# Rebuild Detection
# ============================================
REBUILD_PID=$(pgrep -f "docker buildx bake\|docker build\|docker-compose.*build\|docker compose.*build" 2>/dev/null | head -1 || true)
if [ -n "$REBUILD_PID" ]; then
    echo -e "  ${YELLOW}🔄 Rebuild in progress (PID: $REBUILD_PID) — containers will restart when done${NC}"
fi
echo ""

# ============================================
# Running Containers
# ============================================
echo -e "${BLUE}🐳 Running Containers:${NC}"
CONTAINERS=$(docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null |
    grep -E "scitex-cloud-(dev|staging|prod)-" || echo "")
if [ -n "$CONTAINERS" ]; then
    echo "$CONTAINERS" | while read -r line; do echo "  $line"; done
else
    echo -e "  ${YELLOW}No scitex-cloud containers running${NC}"
fi
echo ""

# ============================================
# Migration Status
# ============================================
"${SCRIPT_DIR}/check-migrations.sh" || true

# ============================================
# Visitor Pool Status
# ============================================
"${SCRIPT_DIR}/check-visitor-pool.sh" || true
echo ""

# ============================================
# SLURM Status
# ============================================
echo -e "${BLUE}🖥️  SLURM Status:${NC}"
if command -v sinfo >/dev/null 2>&1; then
    SLURM_STATUS=$(sinfo --noheader 2>&1 || echo "error")
    if [ -n "$SLURM_STATUS" ] && ! echo "$SLURM_STATUS" | grep -q "error"; then
        echo -e "  ${GREEN}✅ SLURM Cluster: OPERATIONAL${NC}"
        sinfo --noheader 2>/dev/null | while read -r line; do echo "    $line"; done
    else
        echo -e "  ${RED}❌ SLURM Cluster: NOT RESPONDING${NC}"
        echo -e "  ${YELLOW}💡 To start: make slurm-start${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠️  SLURM not installed${NC}"
fi
echo ""

# ============================================
# Host Requirements (delegate to scripts)
# ============================================
echo -e "${BLUE}🔍 Checking host requirements...${NC}"
echo ""
"${SCRIPT_DIR}/check-users.sh" || true
echo ""
"${SCRIPT_DIR}/check-slurm.sh" || true
echo ""

# ============================================
# Terminal Functionality
# ============================================
echo -e "${BLUE}🖥️  Terminal Functionality:${NC}"
"${SCRIPT_DIR}/check-terminal-ready.sh" || true

# ============================================
# Timestamp
# ============================================
echo ""
date
echo ""

# ============================================
# File Size Warnings
# ============================================
"${PROJECT_ROOT}/scripts/maintenance/check_file_sizes.sh" || true

# ============================================
# Apptainer SIF Status (all environments)
# ============================================
echo ""
echo -e "${BLUE}📦 Apptainer Container:${NC}"

# Determine SIF path based on environment
DEF_FILE="${PROJECT_ROOT}/deployment/singularity/scitex-cloud-shared-v0.1.0.def"
HASH_FILE="${PROJECT_ROOT}/deployment/singularity/.def-hash"

if echo "$RUNNING" | grep -q "prod"; then
    SIF_PATH="/opt/scitex/singularity/scitex-cloud-shared-v0.1.0.sif"
    DATA_PATH="/opt/scitex/data/users"
else
    # Dev: read from env file or use default
    SIF_PATH="${PROJECT_ROOT}/deployment/singularity/scitex-cloud-shared-v0.1.0.sif"
    DATA_PATH="${PROJECT_ROOT}/data/users"
fi

SIF_OK=true

if [ -f "$SIF_PATH" ]; then
    SIF_SIZE=$(du -h "$SIF_PATH" | cut -f1)
    SIF_DATE=$(date -r "$SIF_PATH" "+%Y-%m-%d %H:%M")
    echo -e "  ${GREEN}✅ SIF: ${SIF_PATH} (${SIF_SIZE}, built ${SIF_DATE})${NC}"

    # Check if .def has changed since last build
    if [ -f "$DEF_FILE" ] && [ -f "$HASH_FILE" ]; then
        CURRENT_HASH=$(sha256sum "$DEF_FILE" | awk '{print $1}')
        STORED_HASH=$(cat "$HASH_FILE" 2>/dev/null || echo "")
        if [ "$CURRENT_HASH" != "$STORED_HASH" ]; then
            echo -e "  ${YELLOW}⚠️  .def file changed since last build — rebuild recommended${NC}"
            echo -e "  ${YELLOW}   Run: make apptainer-build${NC}"
            SIF_OK=false
        fi
    elif [ -f "$DEF_FILE" ] && [ ! -f "$HASH_FILE" ]; then
        echo -e "  ${YELLOW}⚠️  No build hash found — cannot verify SIF matches .def${NC}"
        echo -e "  ${YELLOW}   Run: make apptainer-build  (skips if unchanged)${NC}"
    fi

    # Prod: check scitex user can read it
    if echo "$RUNNING" | grep -q "prod"; then
        if ! sudo -u scitex test -r "$SIF_PATH" 2>/dev/null; then
            echo -e "  ${RED}❌ SIF not readable by scitex user${NC}"
            SIF_OK=false
        fi
    fi
else
    echo -e "  ${RED}❌ SIF not found: ${SIF_PATH}${NC}"
    echo -e "  ${YELLOW}   Build: make apptainer-build${NC}"
    SIF_OK=false
fi

# Check data directory
if [ -d "$DATA_PATH" ]; then
    echo -e "  ${GREEN}✅ Data dir: ${DATA_PATH}${NC}"
else
    echo -e "  ${RED}❌ Data dir not found: ${DATA_PATH}${NC}"
    SIF_OK=false
fi

if [ "$SIF_OK" = false ] && echo "$RUNNING" | grep -q "prod"; then
    echo ""
    echo -e "  ${YELLOW}⚠️  Terminal may not work — fix issues above${NC}"
    echo -e "  ${YELLOW}   Setup: sudo ./deployment/host-setup/scripts/setup-slurm-paths.sh${NC}"
fi

# ============================================
# Service Health (slow — HTTP checks, runs last)
# ============================================
echo ""
"${SCRIPT_DIR}/check-services.sh" || true
