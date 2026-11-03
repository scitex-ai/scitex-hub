#!/bin/bash
# Single source of truth for the per-environment docker-compose invocation.
#
# Sourcing this file and calling `resolve_compose_env <env>` exports:
#   DOCKER_DIR   — the directory compose must run from
#   COMPOSE_CMD  — the compose command INCLUDING its --env-file / -f flags
#
# WHY THIS EXISTS (incident hub-prod-outage-celery-log-permission, 2026-07-09/10):
# the env→(dir, --env-file, -f overlay) mapping used to live only inside
# rebuild.sh. Anyone doing a one-off `docker compose up -d --force-recreate`
# by hand had to remember `--env-file ../envs/.env.prod`, and forgetting it
# silently substitutes BLANK strings for every SCITEX_HUB_* variable (compose
# only warns). During that incident the omission also caused compose to treat
# postgres/pgbouncer config as "changed" and recreate services that were never
# targeted. Manual invocations must go through `scripts/deploy/compose.sh`
# instead, which reads this mapping.
#
# Fails loud on an unknown environment — never defaults to a bare
# `docker compose` for an env it does not recognise.

resolve_compose_env() {
    local env="$1"
    local project_root="$2"

    if [ -z "$env" ] || [ -z "$project_root" ]; then
        echo "resolve_compose_env: usage: resolve_compose_env <env> <project_root>" >&2
        return 2
    fi

    case "$env" in
    staging)
        DOCKER_DIR="$project_root/deployment/docker"
        export SCITEX_ENV=staging
        COMPOSE_CMD="docker compose --env-file $project_root/deployment/docker/envs/.env.staging -f docker-compose.yml -f docker-compose.staging.yml"
        ;;
    prod)
        # --env-file feeds SCITEX_HUB_*_PROD vars at compose-time (cloudflared
        # token, ports). Symmetric with staging. Closes RC-6's compose-time-
        # substitution sibling gap surfaced in the 2026-06-06 cutover
        # (docs/incidents/2026-06-06-prod-cutover-cloud-to-hub.md).
        #
        # ABSOLUTE path (not the old cwd-relative ../envs/.env.prod): compose
        # resolves --env-file relative to the CALLER's cwd, so a relative path
        # only works when every caller happens to cd into DOCKER_DIR first. When
        # it does NOT, --env-file silently loads nothing and every ${VAR:?}
        # guard in docker_prod/docker-compose.yml aborts the build (e.g.
        # `make ENV=prod rebuild` failing on SCITEX_HUB_POSTGRES_PASSWORD while
        # `rebuild.sh` run by hand worked — card hub-make-rebuild-drops-env-file).
        # An absolute path is cwd-independent, so the sanctioned deploy path and
        # any manual `compose.sh` call resolve the same env-file every time.
        DOCKER_DIR="$project_root/deployment/docker/docker_prod"
        COMPOSE_CMD="docker compose --env-file $project_root/deployment/docker/envs/.env.prod"
        ;;
    dev)
        DOCKER_DIR="$project_root/deployment/docker/docker_dev"
        COMPOSE_CMD="docker compose"
        ;;
    *)
        echo "resolve_compose_env: invalid environment '$env' (want: dev, staging, prod)" >&2
        return 1
        ;;
    esac

    # This is an image identity, never a URL or a place for registry credentials.
    # Keep diagnostics fixed: rejected input can contain sensitive shell data.
    if [ "${SCITEX_HUB_APP_IMAGE+x}" = x ]; then
        if [ "$env" = dev ]; then
            echo "resolve_compose_env: application image override is supported only for prod/staging" >&2
            return 2
        fi
        if ! [[ "$SCITEX_HUB_APP_IMAGE" =~ ^[A-Za-z0-9][A-Za-z0-9._:/@-]{0,1023}$ ]] ||
            [[ "$SCITEX_HUB_APP_IMAGE" = *"://"* ]] ||
            [[ "$SCITEX_HUB_APP_IMAGE" = *@*@* ]] ||
            { [[ "$SCITEX_HUB_APP_IMAGE" = *"@"* ]] && ! [[ "$SCITEX_HUB_APP_IMAGE" =~ @sha256:[a-f0-9]{64}$ ]]; } ||
            { [[ "$SCITEX_HUB_APP_IMAGE" = sha256:* ]] && ! [[ "$SCITEX_HUB_APP_IMAGE" =~ ^sha256:[a-f0-9]{64}$ ]]; }; then
            echo "resolve_compose_env: invalid application image override (value withheld)" >&2
            return 2
        fi
        export SCITEX_HUB_APP_IMAGE
    fi

    # Derived, not a caller override: a candidate must test its baked graph.
    # Ordinary staging preserves its existing editable boot behavior.
    # Export the resolved image too: dotenv files must not introduce an
    # unvalidated image after this resolver has derived the Python mode.
    SCITEX_HUB_RESOLVED_APP_IMAGE=""
    case "$env" in
    prod) SCITEX_HUB_RESOLVED_APP_IMAGE="${SCITEX_HUB_APP_IMAGE-scitex-hub-prod-django:latest}" ;;
    staging) SCITEX_HUB_RESOLVED_APP_IMAGE="${SCITEX_HUB_APP_IMAGE-scitex-hub-staging-django:latest}" ;;
    esac
    export SCITEX_HUB_RESOLVED_APP_IMAGE
    SCITEX_HUB_RESOLVED_PYTHON_MODE=editable
    SCITEX_HUB_RESOLVED_FRONTEND_MODE=build
    if [ "$env" = prod ] || [ "${SCITEX_HUB_APP_IMAGE+x}" = x ]; then
        SCITEX_HUB_RESOLVED_PYTHON_MODE=image-only
        SCITEX_HUB_RESOLVED_FRONTEND_MODE=baked
    fi
    export SCITEX_HUB_RESOLVED_PYTHON_MODE SCITEX_HUB_RESOLVED_FRONTEND_MODE

    if [ ! -d "$DOCKER_DIR" ]; then
        echo "resolve_compose_env: docker directory not found: $DOCKER_DIR" >&2
        return 1
    fi

    export DOCKER_DIR COMPOSE_CMD
}

# EOF
