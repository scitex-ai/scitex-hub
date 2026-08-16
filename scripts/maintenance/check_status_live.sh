#!/bin/bash
# Live Status Checker — sequential, with progress shown as each section lands.
#
# Same sections as `make status`, in the same order, from the same registry
# (deployment/host-setup/checks/sections.sh). The difference is presentation
# only: `make status` fans out in parallel and prints each chunk when it is
# ready, this prints them in registry order and tells you what it is waiting on.
#
# WHY IT NO LONGER HAS ITS OWN LIST. It used to hand-inline bash for five
# sections — environment, containers, SLURM, the scitex user, terminal — which
# meant a check added to `make status` did not appear here. Ten sections were
# missing that way, DISK AMONG THEM, so on 2026-08-09 a volume at 100% was
# invisible to this command while `make status` would have said so. Adding a
# check is now one line in sections.sh and both surfaces get it.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CHECKS_DIR="${PROJECT_ROOT}/deployment/host-setup/checks"

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m'

SECTIONS_SCRIPT_DIR="${CHECKS_DIR}"
SECTIONS_PROJECT_ROOT="${PROJECT_ROOT}"
export SECTIONS_SCRIPT_DIR SECTIONS_PROJECT_ROOT
# shellcheck source=deployment/host-setup/checks/sections.sh
source "${CHECKS_DIR}/sections.sh"

main() {
    # The environment argument is accepted for backwards compatibility with
    # `make status-live ENV=x` and is deliberately unused: the section scripts
    # read the environment themselves, and a second opinion here is how the
    # two lists drifted apart in the first place.
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║           SciTeX Hub - Live Status                  ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════╝${NC}"
    echo ""

    local name command output
    while IFS=$'\t' read -r name command; do
        [ -n "$name" ] || continue

        # Show what is running, then overwrite the line with its output, so a
        # section that hangs is visible as the thing being waited on rather
        # than as silence.
        echo -n -e "${CYAN}⏳ ${name}...${NC}"
        output=$("$command" 2>&1) || true
        echo -e "\r\033[K${output}"
        echo ""
    done < <(status_sections)

    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}Status check complete!${NC} $(date '+%Y-%m-%d %H:%M:%S')"
}

main "${1:-prod}"
