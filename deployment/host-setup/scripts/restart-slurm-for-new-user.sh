#!/bin/bash
# Restart SLURM services to pick up new users from /etc/passwd
# This must be run after creating new system users that will submit SLURM jobs

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/colors.sh" 2>/dev/null || {
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;36m'; NC='\033[0m'
}

echo -e "${BLUE}Restarting SLURM services to pick up new users...${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root or with sudo${NC}"
    echo -e "Usage: sudo $0"
    exit 1
fi

# Restart slurmd (compute node daemon)
echo -e "${BLUE}Restarting slurmd...${NC}"
if systemctl restart slurmd 2>/dev/null; then
    echo -e "${GREEN}✓ slurmd restarted${NC}"
elif service slurmd restart 2>/dev/null; then
    echo -e "${GREEN}✓ slurmd restarted${NC}"
else
    echo -e "${RED}✗ Failed to restart slurmd${NC}"
    exit 1
fi

# Restart slurmctld (controller daemon)
echo -e "${BLUE}Restarting slurmctld...${NC}"
if systemctl restart slurmctld 2>/dev/null; then
    echo -e "${GREEN}✓ slurmctld restarted${NC}"
elif service slurmctld restart 2>/dev/null; then
    echo -e "${GREEN}✓ slurmctld restarted${NC}"
else
    echo -e "${RED}✗ Failed to restart slurmctld${NC}"
    exit 1
fi

# Wait for services to be ready
echo ""
echo -e "${BLUE}Waiting for services to be ready...${NC}"
sleep 3

# Verify services are running
echo ""
echo -e "${BLUE}Verifying SLURM services...${NC}"
all_good=true

if systemctl is-active --quiet slurmd 2>/dev/null || service slurmd status >/dev/null 2>&1; then
    echo -e "${GREEN}✓ slurmd is running${NC}"
else
    echo -e "${RED}✗ slurmd is NOT running${NC}"
    all_good=false
fi

if systemctl is-active --quiet slurmctld 2>/dev/null || service slurmctld status >/dev/null 2>&1; then
    echo -e "${GREEN}✓ slurmctld is running${NC}"
else
    echo -e "${RED}✗ slurmctld is NOT running${NC}"
    all_good=false
fi

echo ""

if [ "$all_good" = true ]; then
    echo -e "${GREEN}✅ SLURM services restarted successfully${NC}"
    echo ""
    echo -e "${BLUE}SLURM should now recognize new users in /etc/passwd${NC}"
    echo -e "${BLUE}Terminals at https://scitex.ai should now work${NC}"
    exit 0
else
    echo -e "${RED}❌ Some SLURM services failed to restart${NC}"
    echo -e "${YELLOW}Check logs: sudo journalctl -u slurmd -u slurmctld -n 50${NC}"
    exit 1
fi
