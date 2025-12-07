#!/bin/bash
# Master Status Check Script
# Orchestrates all status checks for make status
# This is the single reliable source for admin's short-term memory

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

source "${SCRIPT_DIR}/../scripts/lib/colors.sh" 2>/dev/null || {
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;36m'; NC='\033[0m'
}

# ============================================
# Environment Status
# ============================================
echo -e "${BLUE}📊 Environment Status:${NC}"
RUNNING=$(docker ps --format '{{.Names}}' 2>/dev/null | \
    grep -oE 'scitex-cloud-(dev|prod|nas)-' | \
    sed 's/scitex-cloud-//' | \
    sed 's/-//' | \
    sort -u | \
    tr '\n' ' ' | \
    xargs || echo "")

if [ -n "$RUNNING" ]; then
    echo -e "  ${BLUE}Active environment:${NC} $RUNNING"
else
    echo -e "  ${YELLOW}⚠️  No active environment${NC}"
fi
echo ""

# ============================================
# Running Containers
# ============================================
echo -e "${BLUE}🐳 Running Containers:${NC}"
CONTAINERS=$(docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null | \
    grep -E "scitex-cloud-(dev|prod|nas)-" || echo "")
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
"${PROJECT_ROOT}/scripts/check_file_sizes.sh" || true
