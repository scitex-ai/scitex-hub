#!/bin/bash
# ---
# Timestamp: 2026-03-21
# Author: ywatanabe + Claude
# File: deployment/host-setup/scripts/regenerate-gitea-token.sh
# ---
# Regenerates Gitea admin API token and updates .env file.
# Creates admin user if it doesn't exist.
# Usage: bash deployment/host-setup/scripts/regenerate-gitea-token.sh [ENV]
#   ENV: dev, staging, or prod (default: dev)

set -eu

# Colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

ENV="${1:-dev}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
ENV_FILE="$PROJECT_ROOT/deployment/docker/envs/.env.${ENV}"

# Resolve docker compose file
case "$ENV" in
    dev)     COMPOSE_FILE="$PROJECT_ROOT/deployment/docker/docker_dev/docker-compose.yml" ;;
    staging) COMPOSE_FILE="$PROJECT_ROOT/deployment/docker/docker_staging/docker-compose.yml" ;;
    prod)    COMPOSE_FILE="$PROJECT_ROOT/deployment/docker/docker_prod/docker-compose.yml" ;;
    *)
        echo -e "${RED}ERROR: Unknown environment '$ENV'. Use dev, staging, or prod.${NC}" >&2
        exit 1
        ;;
esac

if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}ERROR: Compose file not found: $COMPOSE_FILE${NC}" >&2
    exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}ERROR: Env file not found: $ENV_FILE${NC}" >&2
    exit 1
fi

COMPOSE_CMD="docker compose -f $COMPOSE_FILE"
GITEA_EXEC="$COMPOSE_CMD exec -T -u git gitea"

# Check Gitea container is running
if ! $COMPOSE_CMD ps gitea 2>/dev/null | grep -q "running\|Up"; then
    echo -e "${RED}ERROR: Gitea container is not running. Start it first.${NC}" >&2
    exit 1
fi

# Read admin credentials from env file
ADMIN_USER=$(grep "SCITEX_CLOUD_GITEA_ADMIN_USERNAME" "$ENV_FILE" | tail -1 | cut -d= -f2)
ADMIN_PASSWORD=$(grep "SCITEX_CLOUD_GITEA_ADMIN_PASSWORD" "$ENV_FILE" | tail -1 | cut -d= -f2)
ADMIN_EMAIL=$(grep "SCITEX_CLOUD_GITEA_ADMIN_EMAIL" "$ENV_FILE" | tail -1 | cut -d= -f2)

if [ -z "$ADMIN_USER" ]; then
    echo -e "${RED}ERROR: SCITEX_CLOUD_GITEA_ADMIN_USERNAME not found in $ENV_FILE${NC}" >&2
    exit 1
fi

if [ -z "$ADMIN_PASSWORD" ]; then
    echo -e "${RED}ERROR: SCITEX_CLOUD_GITEA_ADMIN_PASSWORD not found in $ENV_FILE${NC}" >&2
    exit 1
fi

if [ -z "$ADMIN_EMAIL" ]; then
    echo -e "${RED}ERROR: SCITEX_CLOUD_GITEA_ADMIN_EMAIL not found in $ENV_FILE${NC}" >&2
    exit 1
fi

echo ""
echo -e "${CYAN}🔑 Regenerating Gitea API token${NC}"
echo -e "${CYAN}   Environment: ${ENV}${NC}"
echo -e "${CYAN}   Admin user:  ${ADMIN_USER}${NC}"
echo ""

# Step 1: Ensure admin user exists
echo -e "${CYAN}  1. Checking admin user...${NC}"
USER_LIST=$($GITEA_EXEC gitea admin user list 2>&1)

if echo "$USER_LIST" | grep -q "$ADMIN_USER"; then
    echo -e "${GREEN}     ✅ Admin user '${ADMIN_USER}' exists${NC}"
else
    echo -e "${YELLOW}     ⚠️  Admin user '${ADMIN_USER}' not found. Creating...${NC}"

    CREATE_OUTPUT=$($GITEA_EXEC gitea admin user create \
        --username "$ADMIN_USER" \
        --password "$ADMIN_PASSWORD" \
        --email "$ADMIN_EMAIL" \
        --admin 2>&1)

    # Verify creation
    USER_LIST=$($GITEA_EXEC gitea admin user list 2>&1)
    if ! echo "$USER_LIST" | grep -q "$ADMIN_USER"; then
        echo -e "${RED}     ❌ Failed to create admin user${NC}" >&2
        echo -e "${RED}        $CREATE_OUTPUT${NC}" >&2
        exit 1
    fi
    echo -e "${GREEN}     ✅ Admin user '${ADMIN_USER}' created${NC}"
fi

echo ""

# Step 2: Delete old token if it exists
echo -e "${CYAN}  2. Cleaning old token...${NC}"
# Use same short flags as generate: -u for username, -t for token-name
$GITEA_EXEC gitea admin user delete-access-token \
    -u "$ADMIN_USER" \
    -t "django-api" 2>/dev/null && \
    echo -e "${GREEN}     ✅ Old token deleted${NC}" || \
    echo -e "${YELLOW}     ⚠️  No existing 'django-api' token (OK)${NC}"

echo ""

# Step 3: Generate new token
echo -e "${CYAN}  3. Generating new token...${NC}"
TOKEN_OUTPUT=""
if ! TOKEN_OUTPUT=$($GITEA_EXEC gitea admin user generate-access-token \
    -u "$ADMIN_USER" \
    -t "django-api" \
    --scopes "all" \
    --raw 2>&1); then
    echo -e "${RED}     ❌ Failed to generate token:${NC}" >&2
    echo -e "${RED}        $TOKEN_OUTPUT${NC}" >&2
    exit 1
fi

# With --raw, output is just the token
NEW_TOKEN=$(echo "$TOKEN_OUTPUT" | tr -d '[:space:]')

if [ -z "$NEW_TOKEN" ]; then
    echo -e "${RED}     ❌ Empty token returned${NC}" >&2
    echo -e "${RED}        Raw output: '$TOKEN_OUTPUT'${NC}" >&2
    exit 1
fi

echo -e "${GREEN}     ✅ Token generated: ${NEW_TOKEN:0:8}...${NEW_TOKEN: -4}${NC}"

echo ""

# Step 4: Update env files
# Docker compose loads .env from its own directory, AND there's a shared envs/.env.{env}
DOCKER_ENV_FILE="$PROJECT_ROOT/deployment/docker/docker_${ENV}/.env"
ENV_FILES=("$ENV_FILE")
if [ -f "$DOCKER_ENV_FILE" ] && [ "$DOCKER_ENV_FILE" != "$ENV_FILE" ]; then
    ENV_FILES+=("$DOCKER_ENV_FILE")
fi

UPDATED=0
for TARGET_FILE in "${ENV_FILES[@]}"; do
    echo -e "${CYAN}  4. Updating $TARGET_FILE...${NC}"
    OLD_TOKENS=$(grep "SCITEX_CLOUD_GITEA_TOKEN" "$TARGET_FILE" | sed 's/.*=//' | sort -u)
    for OLD_TOKEN in $OLD_TOKENS; do
        if [ -n "$OLD_TOKEN" ] && [ "$OLD_TOKEN" != "$NEW_TOKEN" ]; then
            sed -i "s|${OLD_TOKEN}|${NEW_TOKEN}|g" "$TARGET_FILE"
            UPDATED=$((UPDATED + 1))
        fi
    done
done

echo -e "${GREEN}     ✅ Updated ${UPDATED} token entries across ${#ENV_FILES[@]} file(s)${NC}"

echo ""
echo -e "${GREEN}✅ Gitea token regeneration complete${NC}"
echo ""
echo -e "${CYAN}Next: restart to apply:${NC}"
echo -e "  make env=$ENV restart"
echo ""
