#!/bin/bash
# ==============================================================================
# rebuild.sh - Full rebuild of SciTeX Cloud environment
# ==============================================================================
# Usage: ./scripts/deploy/rebuild.sh <env>
#   env: dev, staging, or prod
#
# REBUILD_STEPS (single source of truth - used by 'make help-commands'):
#   1. down          - Stop services (docker compose down)
#   2. build         - Build Docker images (code COPIED into image)
#   3. clear-vite    - Clear vite timestamp (forces TypeScript rebuild)
#   4. up            - Start services (docker compose up -d)
#   5. cache-purge   - Purge Cloudflare cache
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

# Validate environment argument
ENV="${1:-}"
if [ -z "$ENV" ]; then
    echo -e "${RED}Error: Environment required${NC}"
    echo "Usage: $0 <env>"
    echo "  env: dev, staging, or prod"
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

# Production safety confirmation
if [ "$ENV" = "prod" ]; then
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

# Step 1: Stop and remove services
echo -e "${CYAN}  1. Stopping ${ENV}...${NC}"
cd "$DOCKER_DIR"
$COMPOSE_CMD down --remove-orphans --volumes=false 2>/dev/null || true

# Remove any leftover containers (handles edge cases like "Created" state)
echo -e "${CYAN}  1b. Cleaning up leftover containers...${NC}"
docker ps -a --format '{{.Names}}' | grep "^scitex-cloud-${ENV}-" | xargs -r docker rm -f 2>/dev/null || true

# Step 2: Build images
echo -e "${CYAN}  2. Building Docker images...${NC}"
$COMPOSE_CMD build

# Step 3: Clear vite timestamp (forces TypeScript rebuild)
echo -e "${CYAN}  3. Clearing vite timestamp (forces TypeScript rebuild)...${NC}"
docker run --rm -v "scitex-cloud-${ENV}_static_volume:/staticfiles" alpine \
    rm -f /staticfiles/vite/.build-timestamp 2>/dev/null || true

# Step 4: Start services
echo -e "${CYAN}  4. Starting services...${NC}"
$COMPOSE_CMD up -d

# Step 5: Purge Cloudflare cache
echo -e "${CYAN}  5. Purging Cloudflare cache...${NC}"
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
