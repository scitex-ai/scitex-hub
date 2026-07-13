#!/bin/bash
# Install the slurmctld resilience drop-in.
#
# Makes slurmctld (a) start only after name resolution is up, and (b) restart on
# failure. Without this, one lost boot race leaves slurmctld `failed` forever —
# which silently drops every scitex.ai visitor to a read-only workspace, because
# the visitor-slot re-clean cannot verify a container teardown without SLURM.
# See slurmctld-resilience.conf for the incident.
#
# Usage: sudo ./install-slurmctld-resilience.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DROPIN_SRC="${SCRIPT_DIR}/slurmctld-resilience.conf"
DROPIN_DIR="/etc/systemd/system/slurmctld.service.d"
DROPIN_PATH="${DROPIN_DIR}/10-scitex-resilience.conf"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: Must run as root (sudo)${NC}"
    exit 1
fi

if ! systemctl list-unit-files slurmctld.service >/dev/null 2>&1; then
    echo -e "${RED}Error: slurmctld.service not found — is SLURM installed?${NC}"
    exit 1
fi

echo -e "${YELLOW}Installing slurmctld resilience drop-in...${NC}"

install -d -m 0755 "${DROPIN_DIR}"
install -m 0644 "${DROPIN_SRC}" "${DROPIN_PATH}"
echo -e "  ${GREEN}✓${NC} Installed ${DROPIN_PATH}"

systemctl daemon-reload
echo -e "  ${GREEN}✓${NC} Reloaded systemd"

# Show what actually took effect, rather than asserting it.
echo -e "\n${YELLOW}Effective settings:${NC}"
systemctl show slurmctld -p Restart -p RestartUSec -p After \
    | sed 's/^/  /' \
    | grep -E 'Restart|network-online' || true

if ! systemctl is-active --quiet slurmctld; then
    echo -e "\n${YELLOW}slurmctld is not running — starting it${NC}"
    systemctl start slurmctld || {
        echo -e "${RED}❌ slurmctld failed to start${NC}"
        echo -e "   Look at: journalctl -u slurmctld -n 40"
        echo -e "   and:     tail -40 /var/log/slurm/slurmctld.log"
        exit 1
    }
fi

if sinfo >/dev/null 2>&1; then
    echo -e "\n${GREEN}✅ slurmctld is up and the controller is reachable${NC}"
else
    echo -e "\n${RED}❌ slurmctld is active but sinfo cannot reach the controller${NC}"
    echo -e "   Visitor slots will quarantine and every visitor will be READ-ONLY."
    exit 1
fi
