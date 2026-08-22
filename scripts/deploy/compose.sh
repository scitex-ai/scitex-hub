#!/bin/bash
# Run docker compose against an environment with its secrets already wired.
#
# USE THIS INSTEAD OF A BARE `docker compose` FOR ANY MANUAL OPERATION.
# A bare invocation omits `--env-file`, which makes compose substitute BLANK
# strings for every SCITEX_HUB_* variable (it only warns) and can silently
# recreate services you never targeted — see incident
# hub-prod-outage-celery-log-permission (2026-07-09/10).
#
# Usage:
#   scripts/deploy/compose.sh <env> <compose args...>
#
# Examples:
#   scripts/deploy/compose.sh prod ps
#   scripts/deploy/compose.sh prod logs -f django
#   scripts/deploy/compose.sh prod up -d --force-recreate django
#   scripts/deploy/compose.sh staging restart celery_worker
#
# env: dev | staging | prod
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# shellcheck source=./compose_env.sh
source "$SCRIPT_DIR/compose_env.sh"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <env> <compose args...>" >&2
    echo "  env: dev, staging, or prod" >&2
    echo "  e.g. $0 prod ps" >&2
    exit 2
fi

ENV="$1"
shift

resolve_compose_env "$ENV" "$PROJECT_ROOT"

if [ $# -eq 0 ]; then
    echo "Error: no compose arguments given (e.g. 'ps', 'logs -f django')" >&2
    exit 2
fi

# A manual `up` recreates containers just as surely as `make rebuild` does, and
# the hotfixes keeping production alive live only in a container's writable layer
# (measured 2026-08-22 via `docker diff`). Gate the recreate here too, or this
# script becomes the documented way around the gate.
for arg in "$@"; do
    if [ "$arg" = "up" ]; then
        echo "[compose.sh] running the sibling floor + import preflight before 'up'" >&2
        "$SCRIPT_DIR/preflight_sibling_floors.sh" "$ENV"
        break
    fi
done

cd "$DOCKER_DIR"
echo "[compose.sh] env=$ENV dir=$DOCKER_DIR" >&2
echo "[compose.sh] \$ $COMPOSE_CMD $*" >&2
exec $COMPOSE_CMD "$@"

# EOF
