#!/bin/bash
# Install the restart-safe systemd drop-ins for every SLURM-stack unit on this host.
#
# Each stock unit (mariadb, munge, slurmdbd, slurmctld, slurmd) either has no
# Restart= policy or restarts only on signals. One lost boot race or one missing
# directory then leaves the daemon `failed` forever. On the SciTeX cluster that
# kept slurmctld + slurmdbd down for 8 weeks (2026-10-02 .. 2026-11-26), so
# SLURM accounting recorded nothing. See the *-resilience.conf files for each
# incident.
#
# Only units that exist on this host are touched, so the same script runs on the
# controller (all five) and on a worker (munge + slurmd).
#
# Usage: sudo ./install-slurm-resilience.sh [--no-start]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNITS=(mariadb munge slurmdbd slurmctld slurmd)
START=1
[ "${1:-}" = "--no-start" ] && START=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: Must run as root (sudo)${NC}"
    exit 1
fi

installed=()
for unit in "${UNITS[@]}"; do
    if ! systemctl cat "${unit}.service" >/dev/null 2>&1; then
        echo -e "  - ${unit}: not installed on this host, skipped"
        continue
    fi
    src="${SCRIPT_DIR}/${unit}-resilience.conf"
    dir="/etc/systemd/system/${unit}.service.d"
    install -d -m 0755 "${dir}"
    install -m 0644 "${src}" "${dir}/10-scitex-resilience.conf"
    echo -e "  ${GREEN}✓${NC} ${dir}/10-scitex-resilience.conf"
    installed+=("${unit}")
done

systemctl daemon-reload
echo -e "  ${GREEN}✓${NC} Reloaded systemd"

# Show what actually took effect, rather than asserting it.
echo -e "\n${YELLOW}Effective settings:${NC}"
for unit in "${installed[@]}"; do
    echo "  ${unit}: $(systemctl show "${unit}" -p Restart --value) restart, $(systemctl show "${unit}" -p ActiveState --value)"
done

[ "${START}" -eq 1 ] || exit 0

# Start in dependency order; a unit that is already running is left alone
# (restarting slurmd/slurmctld is never needed to apply a drop-in).
rc=0
for unit in "${installed[@]}"; do
    if ! systemctl is-active --quiet "${unit}"; then
        echo -e "${YELLOW}${unit} is not running — starting it${NC}"
        systemctl reset-failed "${unit}" 2>/dev/null || true
        if ! systemctl start "${unit}"; then
            echo -e "${RED}❌ ${unit} failed to start — journalctl -u ${unit} -n 40${NC}"
            rc=1
        fi
    fi
done
exit "${rc}"
