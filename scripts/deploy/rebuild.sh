#!/bin/bash
# ==============================================================================
# rebuild.sh - Full rebuild of SciTeX Hub environment
# ==============================================================================
# Usage: ./scripts/deploy/rebuild.sh <env>
#   env: dev, staging, or prod
#
# REBUILD_STEPS (single source of truth - used by 'make help-commands'):
#   1. slurm-clean   - Cancel ALL SLURM jobs and reset node state
#   2. build         - Build new images while the OLD stack keeps serving
#   3. clear-vite    - Clear vite timestamp (forces TypeScript rebuild)
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

# Set docker directory and compose command based on environment
if [ "$ENV" = "staging" ]; then
    DOCKER_DIR="$PROJECT_ROOT/deployment/docker"
    export SCITEX_ENV=staging
    COMPOSE_CMD="docker compose --env-file ./envs/.env.staging -f docker-compose.yml -f docker-compose.staging.yml"
elif [ "$ENV" = "prod" ]; then
    # --env-file ../envs/.env.prod feeds SCITEX_HUB_*_PROD vars at compose-time
    # (cloudflared token, ports). Symmetric with staging COMPOSE_CMD above.
    # Closes RC-6's compose-time-substitution sibling gap surfaced in the
    # 2026-06-06 cutover (docs/incidents/2026-06-06-prod-cutover-cloud-to-hub.md).
    DOCKER_DIR="$PROJECT_ROOT/deployment/docker/docker_prod"
    COMPOSE_CMD="docker compose --env-file ../envs/.env.prod"
else
    DOCKER_DIR="$PROJECT_ROOT/deployment/docker/docker_${ENV}"
    COMPOSE_CMD="docker compose"
fi

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

# Step 1: Clean SLURM state (before swapping containers)
echo -e "${CYAN}  1. Cleaning SLURM state...${NC}"
cd "$DOCKER_DIR"
DJANGO_CONTAINER="scitex-hub-${ENV}-django-1"
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

# Step 2: Build images WHILE THE OLD STACK KEEPS SERVING.
# CRITICAL (constitution §2 "no surprises"): we deliberately do NOT
# 'docker compose down' before building. The previous containers — nginx,
# cloudflared, django, postgres, redis, gitea — stay UP and keep serving
# traffic for the entire ~10-min build. Only after the build succeeds does
# Step 4 ('up -d') swap the app containers, so the site stays reachable during
# a rebuild (prod: no more 530; staging: no connection-refused for the whole
# build). 'docker compose build' touches images only, never the running
# containers, so serving is unaffected here.
echo -e "${CYAN}  2. Building Docker images (old stack still serving; CPU-limited to keep SSH alive)...${NC}"
export DOCKER_BUILDKIT=1
# nice -n 10: lower priority so SSH/system processes win CPU contention
# shellcheck disable=SC2086  # COMPOSE_CMD intentionally word-splits (e.g. "docker compose")
nice -n 10 $COMPOSE_CMD build

# Step 3: Clear vite timestamp (forces TypeScript rebuild on the new container)
echo -e "${CYAN}  3. Clearing vite timestamp (forces TypeScript rebuild)...${NC}"
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
        if ! apptainer exec \
            --fakeroot --writable \
            --contain --no-home --no-mount home,tmp,cwd \
            "$CURRENT_SANDBOX" \
            find / -xdev \
            -not -path '/proc*' -not -path '/sys*' -not -path '/dev*' \
            -not -path '/.singularity.d*' \
            -not -type l \
            -exec chmod a+rX {} + 2>&1; then
            echo -e "${RED}   ❌ Sandbox permission fix failed (apptainer --fakeroot find/chmod).${NC}" >&2
            exit 1
        fi
        echo "   Sandbox permissions fixed"
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

echo ""
echo -e "${GREEN}✅ ${ENV} rebuild complete${NC}"
echo ""
echo -e "${CYAN}Check status with:${NC} make ENV=${ENV} status"
