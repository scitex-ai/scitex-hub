#!/bin/bash
# Setup SLURM-accessible paths for SciTeX Cloud
#
# Creates /opt/scitex with proper permissions for SLURM jobs.
# This avoids NAS ACL issues with home directories.
#
# Usage: sudo ./setup-slurm-paths.sh
#
# Paths created:
#   /opt/scitex/singularity/  - Apptainer/Singularity container images
#   /opt/scitex/data/users/   - User workspace data

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

# Source SIF location
SOURCE_SIF="${PROJECT_ROOT}/deployment/singularity/scitex-cloud-shared-v0.1.0.sif"

# Target locations
TARGET_BASE="/opt/scitex"
TARGET_SINGULARITY="${TARGET_BASE}/singularity"
TARGET_DATA="${TARGET_BASE}/data/users"
TARGET_SIF="${TARGET_SINGULARITY}/scitex-cloud-shared-v0.1.0.sif"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}SciTeX SLURM Path Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: Must run as root (sudo)${NC}"
    exit 1
fi

# Check source SIF exists
if [ ! -f "$SOURCE_SIF" ]; then
    echo -e "${RED}Error: Source SIF not found: ${SOURCE_SIF}${NC}"
    echo -e "${YELLOW}Build it first: cd deployment/singularity && sudo ./build.sh${NC}"
    exit 1
fi

echo -e "${YELLOW}Creating directory structure...${NC}"

# Create directories
mkdir -p "${TARGET_SINGULARITY}"
mkdir -p "${TARGET_DATA}"
echo -e "  ${GREEN}✓${NC} Created ${TARGET_BASE}"

# Copy SIF file
echo -e "${YELLOW}Copying Singularity container...${NC}"
if [ -f "$TARGET_SIF" ]; then
    SOURCE_SIZE=$(stat -c%s "$SOURCE_SIF")
    TARGET_SIZE=$(stat -c%s "$TARGET_SIF")
    if [ "$SOURCE_SIZE" -eq "$TARGET_SIZE" ]; then
        echo -e "  ${GREEN}✓${NC} SIF already up to date (skipping copy)"
    else
        cp "$SOURCE_SIF" "$TARGET_SIF"
        echo -e "  ${GREEN}✓${NC} Updated SIF (size changed)"
    fi
else
    cp "$SOURCE_SIF" "$TARGET_SIF"
    echo -e "  ${GREEN}✓${NC} Copied SIF to ${TARGET_SIF}"
fi

# Set permissions - world readable for SLURM access
echo -e "${YELLOW}Setting permissions...${NC}"
chmod -R a+rX "${TARGET_BASE}"
chmod a+rx "${TARGET_SINGULARITY}"
chmod a+r "${TARGET_SIF}"
# Data directory needs write access for users
chmod 1777 "${TARGET_DATA}" # Sticky bit like /tmp
echo -e "  ${GREEN}✓${NC} Permissions set (world-readable, data dir writable)"

# Verify
echo ""
echo -e "${BLUE}Verification:${NC}"
ls -la "${TARGET_BASE}/"
echo ""
ls -la "${TARGET_SINGULARITY}/"
echo ""

# Check if scitex user can access
if id "scitex" &>/dev/null; then
    echo -e "${YELLOW}Testing access as 'scitex' user...${NC}"
    if sudo -u scitex test -r "$TARGET_SIF"; then
        echo -e "  ${GREEN}✓${NC} User 'scitex' can read SIF file"
    else
        echo -e "  ${RED}✗${NC} User 'scitex' cannot read SIF file"
        exit 1
    fi
fi

# Copy existing user data if present
OLD_USER_DATA="${PROJECT_ROOT}/data/users"
if [ -d "$OLD_USER_DATA" ] && [ "$(ls -A "$OLD_USER_DATA" 2>/dev/null)" ]; then
    echo -e "${YELLOW}Copying existing user data...${NC}"
    cp -a "$OLD_USER_DATA"/* "$TARGET_DATA"/ 2>/dev/null || true
    chown -R scitex:scitex "$TARGET_DATA"/ 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} User data copied to ${TARGET_DATA}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Next step:"
echo -e "  Restart services: ${GREEN}make env=prod stop && make env=prod start${NC}"
echo ""
