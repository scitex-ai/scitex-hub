#!/bin/bash
# ==============================================================================
# rebuild.sh - Full rebuild of SciTeX Cloud environment
# ==============================================================================
# Usage: ./scripts/deploy/rebuild.sh <env>
#   env: dev, staging, or prod
#
# REBUILD_STEPS (single source of truth - used by 'make help-commands'):
#   1. slurm-clean   - Cancel ALL SLURM jobs and reset node state
#   2. down          - Stop services (docker compose down)
#   3. build         - Build Docker images (code COPIED into image)
#   4. clear-vite    - Clear vite timestamp (forces TypeScript rebuild)
#   5. up            - Start services (docker compose up -d)
#   6. apptainer     - Fix Apptainer sandbox permissions
#   7. cache-purge   - Purge Cloudflare cache
#
# No manual steps needed after running this script.
# ==============================================================================

# Print steps and exit (used by Makefile help-commands)
if [ "$1" = "--steps" ]; then
    grep -A5 "^# REBUILD_STEPS" "$0" | grep "^#   [0-9]" | sed 's/^#   //'
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
else
    DOCKER_DIR="$PROJECT_ROOT/deployment/docker/docker_${ENV}"
    COMPOSE_CMD="docker compose"
fi

# Check docker directory exists
if [ ! -d "$DOCKER_DIR" ]; then
    echo -e "${RED}Error: Docker directory not found: $DOCKER_DIR${NC}"
    exit 1
fi

# Preflight: Apptainer + fakeroot (needed by Step 6 to chmod sandbox files
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
    echo -e "${YELLOW}   This will cause downtime.${NC}"
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

# Step 1: Clean SLURM state (before stopping containers)
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

# Step 2: Stop and remove services
echo -e "${CYAN}  2. Stopping ${ENV}...${NC}"
$COMPOSE_CMD down --remove-orphans --volumes=false 2>/dev/null || true

# Remove any leftover containers (handles edge cases like "Created" state)
echo -e "${CYAN}  2b. Cleaning up leftover containers...${NC}"
docker ps -a --format '{{.Names}}' | grep "^scitex-hub-${ENV}-" | xargs -r docker rm -f 2>/dev/null || true

# Step 3: Build images (with resource limits to keep SSH responsive)
echo -e "${CYAN}  3. Building Docker images (CPU-limited to keep SSH alive)...${NC}"
export DOCKER_BUILDKIT=1
# nice -n 10: lower priority so SSH/system processes win CPU contention
# shellcheck disable=SC2086  # COMPOSE_CMD intentionally word-splits (e.g. "docker compose")
nice -n 10 $COMPOSE_CMD build

# Step 4: Clear vite timestamp (forces TypeScript rebuild)
echo -e "${CYAN}  4. Clearing vite timestamp (forces TypeScript rebuild)...${NC}"
docker run --rm -v "scitex-hub-${ENV}_static_volume:/staticfiles" alpine \
    rm -f /staticfiles/vite/.build-timestamp 2>/dev/null || true

# Step 5: Start services
echo -e "${CYAN}  5. Starting services...${NC}"
$COMPOSE_CMD up -d

# Step 6: Fix Apptainer sandbox permissions (must be readable by scitex user)
echo -e "${CYAN}  6. Fixing Apptainer sandbox permissions...${NC}"
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
        if ! apptainer exec \
            --fakeroot --writable \
            --contain --no-home --no-mount home,tmp,cwd \
            "$CURRENT_SANDBOX" \
            find / -xdev \
            -not -path '/proc*' -not -path '/sys*' -not -path '/dev*' \
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

# Step 7: Purge Cloudflare cache
echo -e "${CYAN}  7. Purging Cloudflare cache...${NC}"
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
