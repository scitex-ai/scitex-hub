#!/bin/bash
# File: ./deployment/singularity/freeze.sh
# ============================================
# Extract pinned versions from built SIF
# ============================================
# After building the SIF with loose versions, run this to:
# 1. Extract pip freeze from the container
# 2. Save as requirements-lock.txt
# 3. Next build uses the lock file for exact reproducibility
#
# Usage: ./freeze.sh [path-to-sif]

# NOTE: Canonical way: scitex container freeze
# This script remains for Makefile compatibility.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIF_FILE="${1:-$SCRIPT_DIR/current.sif}"
LOCK_FILE="$SCRIPT_DIR/requirements-lock.txt"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

if [ ! -f "$SIF_FILE" ]; then
    echo -e "${RED}Error: SIF not found: $SIF_FILE${NC}"
    echo -e "Build first: make apptainer-build"
    exit 1
fi

# Detect container tool
if command -v apptainer &>/dev/null; then
    CMD="apptainer"
elif command -v singularity &>/dev/null; then
    CMD="singularity"
else
    echo -e "${RED}Error: Neither apptainer nor singularity installed${NC}"
    exit 1
fi

echo -e "${GREEN}Extracting pip freeze from SIF...${NC}"
$CMD exec "$SIF_FILE" pip freeze >"$LOCK_FILE"

# Also capture system packages and node modules
DPKG_LOCK="$SCRIPT_DIR/dpkg-lock.txt"
NODE_LOCK="$SCRIPT_DIR/node-lock.txt"

echo -e "${GREEN}Extracting dpkg packages...${NC}"
# shellcheck disable=SC2016  # ${Package}/${Version} are dpkg format strings, not shell vars
$CMD exec "$SIF_FILE" dpkg-query -W -f='${Package}=${Version}\n' >"$DPKG_LOCK" 2>/dev/null || true

echo -e "${GREEN}Extracting global npm packages...${NC}"
$CMD exec "$SIF_FILE" npm list -g --depth=0 --json >"$NODE_LOCK" 2>/dev/null || true

# Summary
PIP_COUNT=$(wc -l <"$LOCK_FILE")
DPKG_COUNT=$(wc -l <"$DPKG_LOCK" 2>/dev/null || echo 0)
echo -e ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Freeze complete${NC}"
echo -e "${GREEN}============================================${NC}"
echo -e "  Python packages: ${GREEN}${PIP_COUNT}${NC} → $(basename "$LOCK_FILE")"
echo -e "  System packages: ${GREEN}${DPKG_COUNT}${NC} → $(basename "$DPKG_LOCK")"
echo -e "  Node packages:   → $(basename "$NODE_LOCK")"
echo -e ""
echo -e "Key Python packages:"
grep -E "^(scitex|numpy|scipy|pandas|matplotlib|torch|scikit-learn)==" "$LOCK_FILE" | while read -r line; do
    echo -e "  ${GREEN}$line${NC}"
done
echo -e ""
echo -e "Key CLI tools:"
for tool in claude codex gemini; do
    ver=$($CMD exec "$SIF_FILE" $tool --version 2>/dev/null | head -1 || echo "not found")
    echo -e "  ${GREEN}$tool${NC}: $ver"
done
echo -e ""
echo -e "${YELLOW}Lock files saved. For reproducible rebuild:${NC}"
echo -e "  make apptainer-build  (uses requirements-lock.txt if present)"

# EOF
