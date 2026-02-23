#!/bin/bash
# File: ./deployment/singularity/build.sh
# ============================================
# Build SciTeX Apptainer Container (Smart Rebuild)
# ============================================
# Uses SHA256 hash of .def file to skip rebuilds when unchanged.
# Pass --force to rebuild regardless.

# NOTE: Canonical way: scitex container build
# This script remains for Makefile compatibility.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEF_FILE="$SCRIPT_DIR/scitex-cloud-shared-v0.1.0.def"
SIF_FILE="$SCRIPT_DIR/scitex-cloud-shared-v0.1.0.sif"
HASH_FILE="$SCRIPT_DIR/.def-hash"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

FORCE=false
if [ "$1" = "--force" ] || [ "$1" = "-f" ]; then
    FORCE=true
fi

# ============================================
# Pre-flight checks
# ============================================

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root (sudo)${NC}"
    echo -e "Usage: sudo $0 [--force]"
    exit 1
fi

# Check if apptainer is installed (prefer apptainer, fall back to singularity)
if command -v apptainer &>/dev/null; then
    CONTAINER_CMD="apptainer"
elif command -v singularity &>/dev/null; then
    CONTAINER_CMD="singularity"
else
    echo -e "${RED}Error: Neither apptainer nor singularity is installed${NC}"
    echo -e "Install: sudo apt-get install apptainer"
    exit 1
fi

VERSION=$($CONTAINER_CMD --version 2>&1 | head -1)
echo -e "${CYAN}Container tool:${NC} $CONTAINER_CMD ($VERSION)"

# Check if definition file exists
if [ ! -f "$DEF_FILE" ]; then
    echo -e "${RED}Error: Definition file not found: $DEF_FILE${NC}"
    exit 1
fi

# ============================================
# Smart rebuild: hash-based change detection
# ============================================
CURRENT_HASH=$(sha256sum "$DEF_FILE" | awk '{print $1}')

if [ "$FORCE" = false ] && [ -f "$SIF_FILE" ] && [ -f "$HASH_FILE" ]; then
    STORED_HASH=$(cat "$HASH_FILE" 2>/dev/null || echo "")
    if [ "$CURRENT_HASH" = "$STORED_HASH" ]; then
        SIF_SIZE=$(du -h "$SIF_FILE" | cut -f1)
        SIF_DATE=$(date -r "$SIF_FILE" "+%Y-%m-%d %H:%M")
        echo -e "${GREEN}✅ Apptainer SIF is up-to-date${NC}"
        echo -e "   Image: ${SIF_FILE} (${SIF_SIZE}, built ${SIF_DATE})"
        echo -e "   Hash:  ${CURRENT_HASH:0:12}..."
        echo -e "   Use ${YELLOW}--force${NC} to rebuild anyway"
        exit 0
    fi
    echo -e "${YELLOW}⚠️  .def file changed — rebuild needed${NC}"
    echo -e "   Old hash: ${STORED_HASH:0:12}..."
    echo -e "   New hash: ${CURRENT_HASH:0:12}..."
elif [ ! -f "$SIF_FILE" ]; then
    echo -e "${YELLOW}⚠️  No SIF file found — initial build${NC}"
elif [ "$FORCE" = true ]; then
    echo -e "${YELLOW}⚠️  Force rebuild requested${NC}"
fi

echo -e ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Building SciTeX Apptainer Container${NC}"
echo -e "${GREEN}============================================${NC}"
echo -e ""
echo -e "Definition: ${GREEN}$DEF_FILE${NC}"

# Backup existing .sif file if it exists
if [ -f "$SIF_FILE" ]; then
    BACKUP_FILE="$SIF_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${YELLOW}Backing up existing image to: $(basename "$BACKUP_FILE")${NC}"
    cp "$SIF_FILE" "$BACKUP_FILE"
fi

# Check disk space (need at least 6GB free for build)
FREE_SPACE=$(df -BG "$SCRIPT_DIR" | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "$FREE_SPACE" -lt 6 ]; then
    echo -e "${RED}Warning: Low disk space (${FREE_SPACE}GB free, recommend 6GB+)${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e ""
echo -e "${GREEN}Starting build...${NC}"
echo -e "This may take 15-30 minutes (downloads npm + Python packages)."
echo -e ""

# Build the container
START_TIME=$(date +%s)

if $CONTAINER_CMD build --force "$SIF_FILE" "$DEF_FILE"; then
    END_TIME=$(date +%s)
    BUILD_TIME=$((END_TIME - START_TIME))
    BUILD_MINUTES=$((BUILD_TIME / 60))
    BUILD_SECONDS=$((BUILD_TIME % 60))

    # Store hash for future change detection
    echo "$CURRENT_HASH" >"$HASH_FILE"

    echo -e ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}Build completed successfully!${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo -e ""
    echo -e "Image file: ${GREEN}$SIF_FILE${NC}"
    echo -e "Image size: ${GREEN}$(du -h "$SIF_FILE" | cut -f1)${NC}"
    echo -e "Build time: ${GREEN}${BUILD_MINUTES}m ${BUILD_SECONDS}s${NC}"
    echo -e "Def hash:   ${GREEN}${CURRENT_HASH:0:12}...${NC}"
    echo -e ""
    # Auto-freeze: extract pinned versions for reproducibility
    echo -e "${GREEN}Running freeze to capture installed versions...${NC}"
    if bash "$SCRIPT_DIR/freeze.sh" "$SIF_FILE"; then
        echo -e "${GREEN}✅ Version lock files generated${NC}"
    else
        echo -e "${YELLOW}⚠️  Freeze failed (non-critical) — run manually: ./freeze.sh${NC}"
    fi

    echo -e ""
    echo -e "${GREEN}Next steps:${NC}"
    echo -e "  Test:    sudo ./test.sh"
    echo -e "  Restart: make env=dev restart"
    echo -e ""
else
    echo -e ""
    echo -e "${RED}Build failed!${NC}"
    echo -e "Check the error messages above for details."
    exit 1
fi

# EOF
