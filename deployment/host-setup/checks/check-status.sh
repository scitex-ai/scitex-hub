#!/bin/bash
# Master Status Check Script
# Orchestrates all status checks for make status
# This is the single reliable source for admin's short-term memory

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

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
    echo "$CONTAINERS" | while read line; do echo "  $line"; done
else
    echo -e "  ${YELLOW}No scitex-cloud containers running${NC}"
fi
echo ""

# ============================================
# Service Health (delegate to script)
# ============================================
"${SCRIPT_DIR}/check-services.sh" || true

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
        sinfo --noheader 2>/dev/null | while read line; do echo "    $line"; done
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
# Production SLURM Path Check
# ============================================
if echo "$RUNNING" | grep -q "prod"; then
    echo ""
    echo -e "${BLUE}🔐 SLURM Paths (/opt/scitex):${NC}"

    # Check if /opt/scitex is set up
    SIF_PATH="/opt/scitex/singularity/scitex-user-workspace.sif"
    DATA_PATH="/opt/scitex/data/users"

    SETUP_OK=true

    # Check SIF file exists and is readable
    if [ -f "$SIF_PATH" ]; then
        # Check if scitex user can read it
        if sudo -u scitex test -r "$SIF_PATH" 2>/dev/null; then
            echo -e "   ${GREEN}✅ Container: ${SIF_PATH}${NC}"
        else
            echo -e "   ${RED}❌ Container exists but not readable by scitex${NC}"
            SETUP_OK=false
        fi
    else
        echo -e "   ${RED}❌ Container not found: ${SIF_PATH}${NC}"
        SETUP_OK=false
    fi

    # Check data directory exists and is writable
    if [ -d "$DATA_PATH" ]; then
        echo -e "   ${GREEN}✅ Data dir: ${DATA_PATH}${NC}"
    else
        echo -e "   ${RED}❌ Data dir not found: ${DATA_PATH}${NC}"
        SETUP_OK=false
    fi

    # Show setup guidance if needed
    if [ "$SETUP_OK" = false ]; then
        echo ""
        echo -e "   ${YELLOW}⚠️  SLURM paths not configured (terminal will fail)${NC}"
        echo -e "   ${YELLOW}Setup:${NC} ${GREEN}sudo ./deployment/host-setup/scripts/setup-slurm-paths.sh${NC}"
        echo -e "   Then: ${GREEN}make env=prod restart${NC}"
    fi
fi
