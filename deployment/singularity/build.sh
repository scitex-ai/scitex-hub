#!/bin/bash
# Timestamp: "2025-11-25 20:00:00 (ywatanabe)"
# File: ./deployment/singularity/build.sh
# ============================================
# Build SciTeX User Workspace Singularity Container
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEF_FILE="$SCRIPT_DIR/scitex-user-workspace.def"
SIF_FILE="$SCRIPT_DIR/scitex-user-workspace.sif"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Building SciTeX User Workspace Container${NC}"
echo -e "${GREEN}============================================${NC}"
echo -e ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root (sudo)${NC}"
    echo -e "Usage: sudo ./build.sh"
    exit 1
fi

# Check if Singularity is installed
if ! command -v singularity &> /dev/null; then
    echo -e "${RED}Error: Singularity is not installed${NC}"
    echo -e "Install with: sudo apt-get install singularity-container"
    exit 1
fi

# Check Singularity version
SING_VERSION=$(singularity --version | awk '{print $NF}')
echo -e "Singularity version: ${GREEN}$SING_VERSION${NC}"

# Check if definition file exists
if [ ! -f "$DEF_FILE" ]; then
    echo -e "${RED}Error: Definition file not found: $DEF_FILE${NC}"
    exit 1
fi

echo -e "Definition file: ${GREEN}$DEF_FILE${NC}"

# Backup existing .sif file if it exists
if [ -f "$SIF_FILE" ]; then
    BACKUP_FILE="$SIF_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${YELLOW}Backing up existing image to: $BACKUP_FILE${NC}"
    cp "$SIF_FILE" "$BACKUP_FILE"
fi

# Check disk space (need at least 2GB free)
FREE_SPACE=$(df -BG "$SCRIPT_DIR" | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "$FREE_SPACE" -lt 2 ]; then
    echo -e "${RED}Warning: Low disk space (${FREE_SPACE}GB free, recommend 2GB+)${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e ""
echo -e "${GREEN}Starting build...${NC}"
echo -e "This will take 5-10 minutes depending on network speed."
echo -e ""

# Build the container
START_TIME=$(date +%s)

if singularity build "$SIF_FILE" "$DEF_FILE"; then
    END_TIME=$(date +%s)
    BUILD_TIME=$((END_TIME - START_TIME))
    BUILD_MINUTES=$((BUILD_TIME / 60))
    BUILD_SECONDS=$((BUILD_TIME % 60))

    echo -e ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}Build completed successfully!${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo -e ""
    echo -e "Image file: ${GREEN}$SIF_FILE${NC}"
    echo -e "Image size: ${GREEN}$(du -h "$SIF_FILE" | cut -f1)${NC}"
    echo -e "Build time: ${GREEN}${BUILD_MINUTES}m ${BUILD_SECONDS}s${NC}"
    echo -e ""
    echo -e "${GREEN}Next steps:${NC}"
    echo -e "1. Test the container: ./test.sh"
    echo -e "2. Copy to production: sudo cp $SIF_FILE /app/deployment/singularity/"
    echo -e "3. Update Django settings: SINGULARITY_IMAGE_PATH=/app/deployment/singularity/scitex-user-workspace.sif"
    echo -e ""
else
    echo -e ""
    echo -e "${RED}Build failed!${NC}"
    echo -e "Check the error messages above for details."
    exit 1
fi

# EOF
