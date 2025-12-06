#!/bin/bash
# SLURM Configuration Checker
# Validates SLURM is properly configured for SciTeX Cloud

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../scripts/lib/colors.sh" 2>/dev/null || {
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;36m'; NC='\033[0m'
}

check_status=0

echo -e "${BLUE}Checking SLURM configuration...${NC}"

# Check if SLURM is running
if systemctl is-active --quiet slurmd; then
    echo -e "${GREEN}✓ slurmd service is running${NC}"
else
    echo -e "${RED}✗ slurmd service is NOT running${NC}"
    echo -e "${YELLOW}  Start: sudo systemctl start slurmd${NC}"
    check_status=1
fi

if systemctl is-active --quiet slurmctld; then
    echo -e "${GREEN}✓ slurmctld service is running${NC}"
else
    echo -e "${RED}✗ slurmctld service is NOT running${NC}"
    echo -e "${YELLOW}  Start: sudo systemctl start slurmctld${NC}"
    check_status=1
fi

# Check express partition time limit
if command -v scontrol &>/dev/null; then
    max_time=$(scontrol show partition express 2>/dev/null | grep -oP 'MaxTime=\K[^ ]+' || echo "UNKNOWN")
    if [ "$max_time" = "04:00:00" ]; then
        echo -e "${GREEN}✓ express partition MaxTime is correct: ${max_time}${NC}"
    elif [ "$max_time" = "UNKNOWN" ]; then
        echo -e "${YELLOW}⚠ express partition not found or scontrol unavailable${NC}"
        check_status=1
    else
        echo -e "${YELLOW}⚠ express partition MaxTime: ${max_time} (expected 04:00:00)${NC}"
        echo -e "${YELLOW}  This may cause terminal timeout issues${NC}"
        check_status=1
    fi
else
    echo -e "${YELLOW}⚠ scontrol command not found${NC}"
    check_status=1
fi

# Check munge
if systemctl is-active --quiet munge; then
    echo -e "${GREEN}✓ munge service is running${NC}"
else
    echo -e "${RED}✗ munge service is NOT running${NC}"
    echo -e "${YELLOW}  Start: sudo systemctl start munge${NC}"
    check_status=1
fi

# Check munge.key - simplified logic
# If munge service is running, the key must exist and be valid
if systemctl is-active --quiet munge; then
    # Munge running = key exists and is working
    if [ -r /etc/munge/munge.key ]; then
        # We can read it - check permissions
        key_perms=$(stat -c '%a' /etc/munge/munge.key 2>/dev/null)
        if [ "$key_perms" = "400" ]; then
            echo -e "${GREEN}✓ munge.key has correct permissions (400)${NC}"
        else
            echo -e "${YELLOW}⚠ munge.key permissions: ${key_perms} (recommended: 400)${NC}"
        fi
    else
        # Can't read it (permission denied) but munge is running, so it's fine
        echo -e "${GREEN}✓ munge.key exists (verified by running munge service)${NC}"
    fi
else
    # Munge not running - check if key exists
    if [ -r /etc/munge/munge.key ]; then
        echo -e "${YELLOW}⚠ munge.key exists but munge service not running${NC}"
    else
        echo -e "${RED}✗ munge authentication not configured${NC}"
        echo -e "${YELLOW}  Fix: Ensure munge is installed and key generated${NC}"
        check_status=1
    fi
fi

exit $check_status
