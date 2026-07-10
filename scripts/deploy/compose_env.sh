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
        COMPOSE_CMD="docker compose --env-file ./envs/.env.staging -f docker-compose.yml -f docker-compose.staging.yml"
        ;;
    prod)
        # --env-file ../envs/.env.prod feeds SCITEX_HUB_*_PROD vars at
        # compose-time (cloudflared token, ports). Symmetric with staging.
        # Closes RC-6's compose-time-substitution sibling gap surfaced in the
        # 2026-06-06 cutover (docs/incidents/2026-06-06-prod-cutover-cloud-to-hub.md).
        DOCKER_DIR="$project_root/deployment/docker/docker_prod"
        COMPOSE_CMD="docker compose --env-file ../envs/.env.prod"
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

    if [ ! -d "$DOCKER_DIR" ]; then
        echo "resolve_compose_env: docker directory not found: $DOCKER_DIR" >&2
        return 1
    fi

    export DOCKER_DIR COMPOSE_CMD
}

# EOF
