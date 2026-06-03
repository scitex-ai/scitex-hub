#!/bin/bash
# SLURM Configuration Checker
# Validates SLURM is properly configured for SciTeX Hub

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
# shellcheck disable=SC2034
source "${SCRIPT_DIR}/../scripts/lib/colors.sh" 2>/dev/null || {
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;36m'
    NC='\033[0m'
}

echo "⚙️ SLURM:"

# --- Operational check (cluster status via sinfo) ---
if command -v sinfo >/dev/null 2>&1; then
    SLURM_STATUS=$(sinfo --noheader 2>&1 || echo "error")
    if [ -n "$SLURM_STATUS" ] && ! echo "$SLURM_STATUS" | grep -q "error"; then
        echo "  [OK] Cluster: OPERATIONAL"
        sinfo --noheader 2>/dev/null | while read -r line; do echo "    $line"; done
    else
        echo -e "  ${RED}[FAIL] Cluster: NOT RESPONDING${NC}"
        echo -e "    To start: make slurm-start"
    fi
else
    echo -e "  ${YELLOW}[WARN] SLURM not installed${NC}"
fi

# --- Service checks ---
if systemctl is-active --quiet slurmd 2>/dev/null; then
    echo -e "  [OK] slurmd running"
else
    echo -e "  ${RED}[FAIL] slurmd not running${NC}"
    echo -e "    Start: sudo systemctl start slurmd"
fi

if systemctl is-active --quiet slurmctld 2>/dev/null; then
    echo -e "  [OK] slurmctld running"
else
    echo -e "  ${RED}[FAIL] slurmctld not running${NC}"
    echo -e "    Start: sudo systemctl start slurmctld"
fi

# Check express partition time limit
if command -v scontrol &>/dev/null; then
    max_time=$(scontrol show partition express 2>/dev/null | grep -oP 'MaxTime=\K[^ ]+' || echo "UNKNOWN")
    if [ "$max_time" = "04:00:00" ]; then
        echo -e "  [OK] express partition MaxTime: ${max_time}"
    elif [ "$max_time" = "UNKNOWN" ]; then
        echo -e "  ${YELLOW}[WARN] express partition not found${NC}"
    else
        echo -e "  ${YELLOW}[WARN] express partition MaxTime: ${max_time} (expected 04:00:00)${NC}"
        echo -e "    This may cause terminal timeout issues"
    fi
else
    echo -e "  ${YELLOW}[WARN] scontrol not found${NC}"
fi

# Check munge
if systemctl is-active --quiet munge 2>/dev/null; then
    echo -e "  [OK] munge running"
else
    echo -e "  ${RED}[FAIL] munge not running${NC}"
    echo -e "    Start: sudo systemctl start munge"
fi

# Check munge.key - simplified logic
# If munge service is running, the key must exist and be valid
if systemctl is-active --quiet munge 2>/dev/null; then
    # Munge running = key exists and is working
    if [ -r /etc/munge/munge.key ]; then
        # We can read it - check permissions
        key_perms=$(stat -c '%a' /etc/munge/munge.key 2>/dev/null || echo "")
        if [ "$key_perms" = "400" ]; then
            echo -e "  [OK] munge.key permissions: 400"
        else
            echo -e "  ${YELLOW}[WARN] munge.key permissions: ${key_perms} (recommended: 400)${NC}"
        fi
    else
        # Can't read it (permission denied) but munge is running, so it's fine
        echo -e "  [OK] munge.key verified by running service"
    fi
else
    # Munge not running - check if key exists
    if [ -r /etc/munge/munge.key ]; then
        echo -e "  ${YELLOW}[WARN] munge.key exists but service not running${NC}"
    else
        echo -e "  ${RED}[FAIL] munge not configured${NC}"
        echo -e "    Ensure munge is installed and key generated"
    fi
fi

exit 0
