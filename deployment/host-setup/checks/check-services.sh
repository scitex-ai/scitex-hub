#!/bin/bash
# Service Health Checker
# Tests actual connectivity to core services (Database, Redis, Gitea, CrossRef)
# Called by: make status

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../scripts/lib/colors.sh" 2>/dev/null || {
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;36m'; NC='\033[0m'
}

# Determine environment from argument or running containers
ENV="${1:-}"
if [ -z "$ENV" ]; then
    RUNNING=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -oE 'scitex-cloud-(dev|nas)-django' | head -1 || echo "")
    if [ -z "$RUNNING" ]; then
        # No containers running, skip checks
        exit 0
    fi
    ENV=$(echo "$RUNNING" | sed 's/scitex-cloud-//' | sed 's/-django.*//')
fi

CONTAINER="scitex-cloud-${ENV}-django-1"

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$" 2>/dev/null; then
    exit 0
fi

echo -e "${BLUE}🔌 Service Health:${NC}"

# Database check
DB_OK=$(docker exec "$CONTAINER" python manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('ok')" 2>/dev/null | tail -1 || echo "")
if [ "$DB_OK" = "ok" ]; then
    echo -e "  ${GREEN}✓ Database: connected${NC}"
else
    echo -e "  ${RED}✗ Database: connection failed${NC}"
fi

# Redis check
REDIS_OK=$(docker exec "$CONTAINER" python manage.py shell -c "from django.core.cache import cache; cache.set('_health', 1, 10); print('ok' if cache.get('_health') else '')" 2>/dev/null | tail -1 || echo "")
if [ "$REDIS_OK" = "ok" ]; then
    echo -e "  ${GREEN}✓ Redis: connected${NC}"
else
    echo -e "  ${RED}✗ Redis: connection failed${NC}"
fi

# Gitea check
GITEA_OK=$(docker exec "$CONTAINER" curl -sf http://gitea:3000/api/v1/version 2>/dev/null | grep -q version && echo "ok" || echo "")
if [ "$GITEA_OK" = "ok" ]; then
    echo -e "  ${GREEN}✓ Gitea: responding${NC}"
else
    echo -e "  ${YELLOW}⚠ Gitea: not responding (may still be starting)${NC}"
fi

# CrossRef check (NAS only - has local container)
if [ "$ENV" = "nas" ]; then
    CROSSREF_OK=$(docker exec "$CONTAINER" curl -sf http://crossref:3333/health 2>/dev/null && echo "ok" || echo "")
    if [ "$CROSSREF_OK" = "ok" ]; then
        echo -e "  ${GREEN}✓ CrossRef API: responding${NC}"
    else
        echo -e "  ${YELLOW}⚠ CrossRef API: not responding${NC}"
    fi
fi

echo ""
