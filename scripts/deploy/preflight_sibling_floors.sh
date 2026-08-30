#!/bin/bash
# One entry point for the sibling floor + import preflight, shared by every
# caller that recreates containers.
#
# WHY A WRAPPER AND NOT FOUR COPIES OF A PYTHON INVOCATION.
# rebuild.sh, `make restart`, `make reload`, `make rebuild-no-cache` and
# scripts/deploy/compose.sh all recreate containers, and a gate that lives in
# only one of them is bypassed by the other four. `make ENV=prod restart` is
# precisely what deletes the container-level hotfixes that are keeping
# production alive today. They all call this file, so "which interpreter" and
# "what if python3 is missing" are answered once.
#
# Usage: preflight_sibling_floors.sh <env> [extra driver args...]
#
# Exit codes are the driver's: 0 satisfied | 1 REFUSED | 2 target unreachable
# | 3 bad usage. Callers must let a non-zero abort them -- that is the point.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRIVER="$SCRIPT_DIR/preflight_sibling_floors.py"

RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

if [ $# -lt 1 ]; then
    echo "Usage: $0 <dev|staging|prod> [extra args...]" >&2
    exit 3
fi

ENV="$1"
shift

PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PYTHON="$candidate"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    # Deliberately NOT a skip. A missing interpreter means the gate did not run,
    # and "the gate did not run" must never be reported as "the gate passed" --
    # that is the failure mode this whole preflight exists to remove.
    echo -e "${RED}❌ DEPLOY REFUSED -- no python3 on this host, so the sibling floor" >&2
    echo -e "   preflight could not run.${NC}" >&2
    echo -e "${YELLOW}   Install python3 on the deploy host. Skipping the check is not an" >&2
    echo -e "   option: it is exactly what let 2026-08-18 and 2026-08-22 reach production.${NC}" >&2
    exit 2
fi

exec "$PYTHON" "$DRIVER" --env "$ENV" "$@"

# EOF
