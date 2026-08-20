#!/bin/bash
# ==============================================================================
# rebuild.sh - Full rebuild of SciTeX Hub environment
# ==============================================================================
# Usage: ./scripts/deploy/rebuild.sh <env>
#   env: dev, staging, or prod
#
# REBUILD_STEPS (single source of truth - used by 'make help-commands'):
#   1. build         - Build new images while the OLD stack keeps serving
#   2. clear-vite    - Clear vite timestamp (forces TypeScript rebuild)
#   3. slurm-clean   - Cancel ALL SLURM jobs and reset node state
#   4. up            - Swap in new containers (recreate only changed services)
#   5. apptainer     - Fix Apptainer sandbox permissions
#   6. cache-purge   - Purge Cloudflare cache
#
# Zero-downtime design (constitution §2 "no surprises"):
#   Images are built FIRST, while the currently-running containers keep
#   serving traffic. Only after the build succeeds does 'up -d' swap the app
#   containers (django + celery). Compose recreates ONLY the services whose
#   image/config changed and leaves nginx / postgres / redis / gitea /
#   cloudflared running, so the site stays reachable across the ~10-min build.
#   During the brief app-container swap, nginx serves its 502/503 maintenance
#   page (common/nginx/error-pages/502.html) instead of a hard error.
#   The old "down before build" took the ENTIRE stack (incl. nginx +
#   cloudflared) offline for the whole build -> 530 on prod, connection-
#   refused on staging. Removing that down is the fix.
#
# No manual steps needed after running this script.
# ==============================================================================

# Print steps and exit (used by Makefile help-commands)
if [ "$1" = "--steps" ]; then
    grep -A8 "^# REBUILD_STEPS" "$0" | grep "^#   [0-9]" | sed 's/^#   //'
    exit 0
fi

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Parse arguments
AUTO_YES=false
ENV=""
for arg in "$@"; do
    case "$arg" in
    --yes | -y) AUTO_YES=true ;;
    *) ENV="$arg" ;;
    esac
done

# Validate environment argument
if [ -z "$ENV" ]; then
    echo -e "${RED}Error: Environment required${NC}"
    echo "Usage: $0 [--yes] <env>"
    echo "  env: dev, staging, or prod"
    echo "  --yes, -y: Skip confirmation prompts"
    exit 1
fi

# Validate environment value
if [[ ! "$ENV" =~ ^(dev|staging|prod)$ ]]; then
    echo -e "${RED}Error: Invalid environment '$ENV'${NC}"
    echo "Valid environments: dev, staging, prod"
    exit 1
fi

# Set docker directory and compose command based on environment.
# The mapping itself lives in compose_env.sh so that manual operations
# (scripts/deploy/compose.sh) and this script cannot drift apart.
# shellcheck source=./compose_env.sh
source "$SCRIPT_DIR/compose_env.sh"
resolve_compose_env "$ENV" "$PROJECT_ROOT"

# Check docker directory exists
if [ ! -d "$DOCKER_DIR" ]; then
    echo -e "${RED}Error: Docker directory not found: $DOCKER_DIR${NC}"
    exit 1
fi

# Preflight: Apptainer + fakeroot (needed by Step 5 to chmod sandbox files
# owned by sub-UIDs from prior --fakeroot sessions). Fail fast here rather
# than masking a silent chmod failure later.
SANDBOX_DIR_PREFLIGHT="$PROJECT_ROOT/deployment/singularity"
if [ -d "$SANDBOX_DIR_PREFLIGHT" ] &&
    find "$SANDBOX_DIR_PREFLIGHT" -maxdepth 1 \( -name "current-sandbox" -o -name "*-sandbox" \) -type d 2>/dev/null | grep -q .; then
    if ! command -v apptainer >/dev/null 2>&1; then
        echo -e "${RED}Error: apptainer not found but sandbox directory exists.${NC}" >&2
        echo -e "${YELLOW}  Install Apptainer or remove $SANDBOX_DIR_PREFLIGHT/current-sandbox${NC}" >&2
        exit 1
    fi
    if ! grep -qE "^${USER}:" /etc/subuid 2>/dev/null; then
        echo -e "${RED}Error: no /etc/subuid entry for user '${USER}'; apptainer --fakeroot will fail.${NC}" >&2
        echo -e "${YELLOW}  Fix: sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 ${USER}${NC}" >&2
        exit 1
    fi
fi
unset SANDBOX_DIR_PREFLIGHT

# Production safety confirmation
if [ "$ENV" = "prod" ] && [ "$AUTO_YES" = false ]; then
    # Non-TTY (e.g., SSH pipe, cron, AI agent): fail fast with instructions
    if [ ! -t 0 ]; then
        echo -e "${RED}Error: Production rebuild requires confirmation but no TTY available.${NC}" >&2
        echo -e "${YELLOW}Re-run with: make ENV=prod YES=1 rebuild${NC}" >&2
        exit 1
    fi
    echo ""
    echo -e "${RED}⚠️  WARNING: Production rebuild!${NC}"
    echo -e "${YELLOW}   Images build with the site still serving; the app${NC}"
    echo -e "${YELLOW}   containers then swap in briefly. nginx serves a${NC}"
    echo -e "${YELLOW}   maintenance page during the short (~1-2 min) django recreate.${NC}"
    echo ""
    printf "Type 'yes' to confirm: "
    read -r confirm
    if [ "$confirm" != "yes" ]; then
        echo -e "${YELLOW}❌ Rebuild cancelled${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${CYAN}🔄 Rebuilding ${ENV} environment...${NC}"

# Compose must run from the environment's docker directory.
cd "$DOCKER_DIR"
DJANGO_CONTAINER="scitex-hub-${ENV}-django-1"

# Step 1: Build images WHILE THE OLD STACK KEEPS SERVING.
# CRITICAL (constitution §2 "no surprises"): we deliberately do NOT
# 'docker compose down' before building. The previous containers — nginx,
# cloudflared, django, postgres, redis, gitea — stay UP and keep serving
# traffic for the entire ~10-min build. Only after the build succeeds does
# Step 4 ('up -d') swap the app containers, so the site stays reachable during
# a rebuild (prod: no more 530; staging: no connection-refused for the whole
# build). 'docker compose build' touches images only, never the running
# containers, so serving is unaffected here.
echo -e "${CYAN}  1. Building Docker images (old stack still serving; CPU-limited to keep SSH alive)...${NC}"
export DOCKER_BUILDKIT=1
# nice -n 10: lower priority so SSH/system processes win CPU contention
# shellcheck disable=SC2086  # COMPOSE_CMD intentionally word-splits (e.g. "docker compose")
nice -n 10 $COMPOSE_CMD build

# Step 2: Clear vite timestamp (forces TypeScript rebuild on the new container)
echo -e "${CYAN}  2. Clearing vite timestamp (forces TypeScript rebuild)...${NC}"
# Prod uses external volumes named scitex-hub-nas_* (per docker_prod/docker-compose.yml
# `external: true, name: scitex-hub-nas_*` declarations); dev/staging use auto-created
# project-namespaced scitex-hub-${ENV}_*. Without this branch, the prod path silently
# no-op'd on a volume that doesn't exist — surfaced 2026-06-06 cutover postmortem.
if [ "$ENV" = "prod" ]; then
    STATIC_VOL="scitex-hub-nas_static_volume"
else
    STATIC_VOL="scitex-hub-${ENV}_static_volume"
fi
docker run --rm -v "${STATIC_VOL}:/staticfiles" alpine \
    rm -f /staticfiles/vite/.build-timestamp 2>/dev/null || true

# Step 3: Clean SLURM state — deliberately the LAST thing before the swap.
#
# ORDERING IS THE POINT (incident 2026-07-24, card
# hub-rebuild-cancels-slurm-before-fragile-build): this block used to run FIRST,
# before the build. Cancelling every running job is IRREVERSIBLE and destroys
# users' in-flight compute; the build is the step most likely to FAIL (e.g. the
# env-file interpolation failure in hub-make-rebuild-drops-env-file). Running the
# irreversible step ahead of the fragile one meant every failed deploy attempt
# cost users their running jobs for a deploy that never happened — and on
# 2026-07-24 it did exactly that: `make ENV=prod YES=1 rebuild` cancelled all
# SLURM jobs, then aborted in the build.
#
# The cancellation exists to prevent STALE JOB IDs surviving the container swap,
# so its only real requirement is "before the swap". Moving it here preserves
# that intent exactly while making a failed build cost nothing: if the build
# aborts, `set -e` exits above this point and no job is ever cancelled.
echo -e "${CYAN}  3. Cleaning SLURM state (build succeeded; safe to cancel now)...${NC}"
if docker ps --format '{{.Names}}' | grep -q "^${DJANGO_CONTAINER}$"; then
    docker exec "$DJANGO_CONTAINER" bash -c '
        if command -v scancel &>/dev/null; then
            # Cancel ALL jobs to prevent stale job IDs after rebuild
            scancel --state=COMPLETING 2>/dev/null || true
            scancel --state=PENDING 2>/dev/null || true
            scancel --state=RUNNING 2>/dev/null || true
            scancel -u root 2>/dev/null || true
            scancel -u scitex 2>/dev/null || true
            for node in $(sinfo -h -o"%N" 2>/dev/null); do
                scontrol update NodeName="$node" State=resume 2>/dev/null || true
            done
            echo "SLURM state cleaned (all jobs cancelled)"
        else
            echo "SLURM not available, skipping"
        fi
    ' 2>/dev/null || echo -e "${YELLOW}   SLURM cleanup skipped (container not accessible)${NC}"
else
    echo -e "${YELLOW}   Django container not running — SLURM cleanup skipped${NC}"
fi

# Step 4: Swap in the new containers ("swap-last" half of build-first/swap-last).
# 'up -d' recreates ONLY the services whose image or config changed — i.e. the
# freshly-built app image (django + celery_worker + celery_beat, which share
# scitex-hub-${ENV}-django:latest). Pulled/unchanged services (nginx, postgres,
# redis, gitea, cloudflared, umami, pgbouncer) are left running untouched, so
# on prod nginx + the Cloudflare tunnel never drop. Migrations run in the
# django entrypoint on recreate.
#   - prod: while the new django boots, nginx has no healthy upstream and
#     serves its 502/503 maintenance page (common/nginx/error-pages/502.html,
#     a dark "Service is starting up" page) instead of a hard error. nginx
#     re-resolves django's IP via Docker DNS (resolver 127.0.0.11), so it
#     picks up the recreated container automatically.
#   - staging: django is exposed directly (no nginx/reverse proxy, by design),
#     so it shows a brief connection-refused ONLY for the seconds the new
#     django boots — not for the whole build as before.
# --remove-orphans preserves the orphan cleanup the old 'down --remove-orphans'
# used to do. If a container is ever genuinely wedged, recover with a targeted
#   $COMPOSE_CMD up -d --force-recreate <service>
# rather than a blanket 'down' (which would reintroduce full downtime).
echo -e "${CYAN}  4. Swapping in new containers (only changed services recreated)...${NC}"
# shellcheck disable=SC2086  # COMPOSE_CMD intentionally word-splits
$COMPOSE_CMD up -d --remove-orphans

# Step 5: Fix Apptainer sandbox permissions (must be readable by scitex user)
echo -e "${CYAN}  5. Fixing Apptainer sandbox permissions...${NC}"
SANDBOX_DIR="$PROJECT_ROOT/deployment/singularity"
if [ -d "$SANDBOX_DIR" ]; then
    # Find current sandbox directory
    CURRENT_SANDBOX=$(find "$SANDBOX_DIR" -maxdepth 1 -name "current-sandbox" -o -name "*-sandbox" 2>/dev/null | head -1)
    if [ -n "$CURRENT_SANDBOX" ] && [ -d "$CURRENT_SANDBOX" ]; then
        # Use apptainer --fakeroot to chmod: inside the sandbox, fakeroot
        # owns sub-UID files left behind by prior --fakeroot sessions, so
        # chmod succeeds without sudo.
        #
        # --no-home and --no-mount home,tmp,cwd are CRITICAL: without them
        # apptainer bind-mounts the host $HOME / $TMPDIR / $CWD into the
        # namespace, and `chmod -R /` would walk into host files (e.g.
        # ~/.scitex/scholar/cache) that we neither own nor want to touch.
        # --contain additionally uses a minimal /tmp, /var/tmp.
        # Skip /proc, /sys, /dev — kernel pseudo-filesystems that apptainer
        # auto-mounts inside the namespace and whose perms cannot be changed.
        # -xdev also prevents crossing into any nested mount.
        # Skip symlinks (-not -type l): chmod dereferences, so a dangling
        # symlink (e.g. /etc/alternatives/nawk.1.gz) hard-fails the whole
        # step; symlink permissions are ignored on Linux anyway.
        # Skip /.singularity.d — apptainer's own runtime dir is mounted
        # read-only ('/.singularity.d/libs: Read-only file system') and
        # is never read by the scitex user.
        # (2026-07-08 prod rebuild: those two benign cases aborted this
        # step with exit 1, which killed the remaining deploy steps.)
        #
        # chmod's exit code is NOT the gate: apptainer bind-targets it
        # cannot touch (/etc/hosts, /usr/share/zoneinfo/... — 2026-07-22
        # prod rebuild) fail chmod with EPERM while already being a+rX,
        # which is a false-negative. The gate below verifies the actual
        # invariant instead: no file in the sandbox lacks world-read
        # (files also need world-x when owner-x). chmod stays best-effort.
        apptainer exec \
            --fakeroot --writable \
            --contain --no-home --no-mount home,tmp,cwd \
            "$CURRENT_SANDBOX" \
            find / -xdev \
            -not -path '/proc*' -not -path '/sys*' -not -path '/dev*' \
            -not -path '/.singularity.d*' \
            -not -type l \
            -exec chmod a+rX {} + 2>&1 \
            || echo -e "${YELLOW}   ⚠️ chmod reported errors; verifying the readability invariant directly...${NC}"
        UNREADABLE=$(apptainer exec \
            --contain --no-home --no-mount home,tmp,cwd \
            "$CURRENT_SANDBOX" \
            find / -xdev \
            -not -path '/proc*' -not -path '/sys*' -not -path '/dev*' \
            -not -path '/.singularity.d*' \
            -not -type l \
            '(' -not -perm -o=r -o '(' -perm -u=x -not -perm -o=x ')' ')' \
            -print 2>/dev/null | head -20)
        if [ -n "$UNREADABLE" ]; then
            echo -e "${RED}   ❌ Sandbox has files the scitex user cannot read (first 20):${NC}" >&2
            echo "$UNREADABLE" >&2
            exit 1
        fi
        echo "   Sandbox permissions verified (world-readable)"
    else
        echo -e "${YELLOW}   No sandbox directory found${NC}"
    fi
else
    echo -e "${YELLOW}   Singularity directory not found${NC}"
fi

# Step 6: Purge Cloudflare cache
echo -e "${CYAN}  6. Purging Cloudflare cache...${NC}"
CACHE_PURGE_SCRIPT="$PROJECT_ROOT/deployment/docker/common/scripts/cloudflare_cache_purge.sh"
if [ -x "$CACHE_PURGE_SCRIPT" ]; then
    "$CACHE_PURGE_SCRIPT" all 2>/dev/null || echo -e "${YELLOW}   ⚠️ Cache purge skipped (no API credentials)${NC}"
else
    echo -e "${YELLOW}   ⚠️ Cache purge script not found${NC}"
fi

# ==============================================================================
# Step 7: VERIFY THE SERVICE IS ACTUALLY UP — this script must not be able to
#         report success while the site is down.
# ==============================================================================
# WHY THIS EXISTS (incident 2026-07-30). Every step above could succeed and the
# site still be dead. `docker compose up -d` is NOT atomic: if one container
# refuses removal, compose ABORTS the remaining sequence. Measured that day:
#
#     Container scitex-hub-prod-django-1  Recreated     <- created, never STARTED
#     Container scitex-hub-prod-ws_ssh_proxy-1  Recreate ...
#     Error response from daemon: cannot remove container
#       "/scitex-hub-prod-celery_worker-1": container is running
#
# django sat in state `Created` — built from the right commit and never started.
# nginx had no backend, so scitex.ai served 503 for ~9 minutes, and this script
# had already printed "rebuild complete" and exited 0. The same abort also left
# celery_beat and celery_worker_vis in `Created` for about an hour, unnoticed,
# and celery_worker_vis is the visitor-provisioning worker.
#
# NOTE ON wait-healthy.sh: it polls `docker ps`, which does NOT list `Created`
# containers at all. Run alone it would have reported every container healthy
# during that outage, because the broken one was invisible to it. Hence the
# explicit `docker ps -a` check below — it is not redundant with the health wait.
echo ""
echo -e "${CYAN}  7. Verifying the service is actually up...${NC}"

VERIFY_FAILED=0

# 7a. No container may be left in `Created` — that is the abort signature.
STRANDED="$($COMPOSE_CMD ps -a --status=created --format '{{.Name}}' 2>/dev/null || true)"
if [ -n "$STRANDED" ]; then
    echo -e "${RED}   ❌ Container(s) CREATED but never STARTED:${NC}" >&2
    echo "$STRANDED" >&2
    echo -e "${YELLOW}      compose aborted mid-swap. Start them, or re-run this script.${NC}" >&2
    echo -e "${YELLOW}      docker start $(echo "$STRANDED" | tr '\n' ' ')${NC}" >&2
    VERIFY_FAILED=1
else
    echo "   No stranded (Created) containers"
fi

# 7b. Containers report healthy.
WAIT_HEALTHY="$SCRIPT_DIR/wait-healthy.sh"
if [ -x "$WAIT_HEALTHY" ]; then
    if "$WAIT_HEALTHY" "$ENV" 420; then
        echo "   Containers healthy"
    else
        echo -e "${RED}   ❌ Containers did not become healthy${NC}" >&2
        VERIFY_FAILED=1
    fi
else
    echo -e "${YELLOW}   ⚠️ wait-healthy.sh not executable — skipping health wait${NC}" >&2
fi

# 7c. THE ONE THAT MATTERS: does the site answer?
# Deliberately explicit per environment rather than derived from an env var:
# .env.prod carries no SITE_URL, and a missing variable must not silently
# downgrade this into "no URL, nothing to check, success".
case "$ENV" in
    prod)    VERIFY_URL="https://scitex.ai/" ;;
    staging) VERIFY_URL="http://127.0.0.1:31294/" ;;
    dev)     VERIFY_URL="http://127.0.0.1:31295/" ;;
    *)       VERIFY_URL="" ;;
esac

if [ -n "$VERIFY_URL" ]; then
    # django rebuilds the TypeScript bundle and runs collectstatic AT CONTAINER
    # START (~5 min), so the deadline must exceed that or this check fails a
    # deploy that was merely still booting.
    echo "   Polling $VERIFY_URL (deadline 8 min; django compiles assets on boot)"
    SITE_OK=0
    for _ in $(seq 1 48); do
        CODE="$(curl -s -o /dev/null -w '%{http_code}' -m 10 "$VERIFY_URL" 2>/dev/null || echo 000)"
        case "$CODE" in
            200 | 301 | 302) SITE_OK=1; break ;;
        esac
        sleep 10
    done
    if [ "$SITE_OK" = "1" ]; then
        echo -e "${GREEN}   Site answering ($VERIFY_URL -> $CODE)${NC}"
    else
        echo -e "${RED}   ❌ Site NOT answering after 8 min (last code: $CODE)${NC}" >&2
        echo -e "${YELLOW}      Check for Created containers and django logs:${NC}" >&2
        echo -e "${YELLOW}      docker ps -a --filter status=created${NC}" >&2
        echo -e "${YELLOW}      docker logs --tail 50 scitex-hub-${ENV}-django-1${NC}" >&2
        VERIFY_FAILED=1
    fi
else
    echo -e "${YELLOW}   ⚠️ No verify URL for env '${ENV}' — service check SKIPPED${NC}" >&2
fi

# 7d. THE POST-CONDITION NOTHING ELSE CHECKS: the visitor pool must have at
#     least one DISTRIBUTABLE slot before this deploy may call itself done.
#
# Every deploy quarantines all 16 slots. That is the boot fail-safe in
# deployment/docker/common/scripts/entrypoint-prod.sh
# (`reconcile_visitor_slots --async`), and it is CORRECT: after a restart no
# slot's on-disk state can be trusted. The slots come back ONLY if
# celery_worker_vis then verifies each one clean.
#
# The entrypoint only DISPATCHES that re-clean. Every message it prints says
# "dispatched"; nothing anywhere asked the follow-up question "did any slot
# actually come back?". So the deploy declared success on dispatch rather than
# on outcome — constitution §2, a declaration that cannot be honoured
# evaporating instead of failing.
#
# MEASURED 2026-08-16: image built 22:06:16 JST, django recreated 22:08:34 JST,
# pool quarantined 16/16 for ~1h35m. EVERY SIGNAL WAS GREEN — containers
# healthy, site 200, /api/server-health/ "healthy" — while every anonymous
# visitor was funnelled onto the single shared readonly-visitor account. A
# human noticed, not a signal. The repair was a command that lived only in a
# card comment addressed to whoever deployed next, i.e. in a dead process's
# intention (constitution §7).
#
# visitor_pool_ready is READ-ONLY (pure ORM counting). It must never be
# replaced by `reconcile_visitor_slots`: that command's Phase 1 quarantines
# EVERY slot including healthy ones, so using it as a probe takes the pool down.
echo "   Checking visitor pool readiness..."
if docker ps --format '{{.Names}}' | grep -q "^${DJANGO_CONTAINER}$"; then
    # --wait: the async wipe+verify is ~10s per slot, and celery_worker_vis'
    # own healthcheck start_period is 300s. 600s clears both, so a merely-slow
    # pool is never failed — only a pool that never recovers.
    if docker exec "$DJANGO_CONTAINER" \
        python manage.py visitor_pool_ready --min-ready 1 --wait 600; then
        echo -e "${GREEN}   Visitor pool has distributable slots${NC}"
    else
        echo -e "${RED}   ❌ Visitor pool has NO distributable slot — every anonymous visitor gets read-only${NC}" >&2
        echo -e "${YELLOW}      docker exec ${DJANGO_CONTAINER} python manage.py reconcile_visitor_slots --repair-only${NC}" >&2
        echo -e "${YELLOW}      docker logs --tail 100 scitex-hub-${ENV}-celery_worker_vis-1${NC}" >&2
        VERIFY_FAILED=1
    fi
else
    echo -e "${RED}   ❌ ${DJANGO_CONTAINER} not running — cannot verify visitor pool${NC}" >&2
    VERIFY_FAILED=1
fi

echo ""
if [ "$VERIFY_FAILED" != "0" ]; then
    echo -e "${RED}❌ ${ENV} rebuild FAILED verification — the site may be DOWN.${NC}" >&2
    echo -e "${RED}   Images were built; the swap did not fully land. See hints above.${NC}" >&2
    exit 1
fi

echo -e "${GREEN}✅ ${ENV} rebuild complete — verified serving${NC}"
echo ""
echo -e "${CYAN}Check status with:${NC} make ENV=${ENV} status"
