#!/bin/bash
# Install scitex-slurm-perms systemd service
# This ensures SLURM path permissions are fixed on every boot
#
# Usage: sudo ./install-slurm-perms-service.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="scitex-slurm-perms.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE_FILE}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: Must run as root (sudo)${NC}"
    exit 1
fi

echo -e "${YELLOW}Installing scitex-slurm-perms service...${NC}"

# Copy service file
cp "${SCRIPT_DIR}/${SERVICE_FILE}" "${SERVICE_PATH}"
echo -e "  ${GREEN}✓${NC} Copied service file to ${SERVICE_PATH}"

# Reload systemd
systemctl daemon-reload
echo -e "  ${GREEN}✓${NC} Reloaded systemd daemon"

# Enable service
systemctl enable "${SERVICE_FILE}"
echo -e "  ${GREEN}✓${NC} Enabled service for boot"

# Start service now
systemctl start "${SERVICE_FILE}"
echo -e "  ${GREEN}✓${NC} Started service"

# Verify
if systemctl is-active --quiet "${SERVICE_FILE}"; then
    echo -e ""
    echo -e "${GREEN}✅ Service installed and running${NC}"
    echo -e "   SLURM permissions will be fixed automatically on every boot."
else
    echo -e ""
    echo -e "${RED}❌ Service failed to start${NC}"
    echo -e "   Check: systemctl status ${SERVICE_FILE}"
    exit 1
fi
