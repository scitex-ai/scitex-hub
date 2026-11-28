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

# Compose interpolates every service's build args for ANY command (ps, logs,
# up --no-build), and the release compose files require
# SCITEX_HUB_DEPENDENCY_RESOLUTION (`:?set by protected rebuild`). It is not a
# secret and does not belong in .env.<env>: it is the committed release input
# deployment/docker/dependency-resolution.nonce, the same value rebuild.sh
# passes to the image build. Derive it here the same way, never from the
# caller's environment, so a manual build cannot carry a different value.
if ! SCITEX_HUB_DEPENDENCY_RESOLUTION="$("$SCRIPT_DIR/resolve_dependency_resolution.sh" "$ENV")"; then
    echo "[compose.sh] Error: cannot derive SCITEX_HUB_DEPENDENCY_RESOLUTION for env=$ENV." >&2
    echo "[compose.sh] It comes from deployment/docker/dependency-resolution.nonce (one line, [A-Za-z0-9._-]+)." >&2
    echo "[compose.sh] Restore that file from the release branch; do not set the variable by hand." >&2
    exit 1
fi
export SCITEX_HUB_DEPENDENCY_RESOLUTION

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
        if [ "$1" != "up" ]; then
            echo "[compose.sh] DEPLOY REFUSED: pre-up global Compose overrides are not modelled by the dependency preflight. Declare them in compose_env.sh so config and recreate use the same contract." >&2
            exit 2
        fi
        # The preflight interrogates the hub APPLICATION image (Django, Celery).
        # It is skipped only when up_needs_app_preflight.py PROVES that every
        # service this `up` starts -- dependencies included unless --no-deps --
        # is a literal third-party image the hub does not build (gitea, nginx).
        # A bare `up`, an unknown option, an unparseable file, a missing python:
        # anything short of that proof runs the preflight, exactly as before.
        verdict=""
        if command -v python3 >/dev/null 2>&1; then
            verdict="$(python3 "$SCRIPT_DIR/up_needs_app_preflight.py" "$DOCKER_DIR" "$COMPOSE_CMD" "$@" || true)"
        fi
        if [ "$verdict" = "skip" ]; then
            echo "[compose.sh] sibling floor + import preflight not needed: no service built from the application image is started" >&2
        else
            echo "[compose.sh] running the sibling floor + import preflight before 'up'" >&2
            "$SCRIPT_DIR/preflight_sibling_floors.sh" "$ENV"
        fi
        break
    fi
done

cd "$DOCKER_DIR"
echo "[compose.sh] env=$ENV dir=$DOCKER_DIR" >&2
echo "[compose.sh] \$ $COMPOSE_CMD $*" >&2
exec $COMPOSE_CMD "$@"

# EOF
