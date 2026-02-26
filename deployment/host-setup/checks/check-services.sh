#!/bin/bash
# Service Health Checker
# Tests actual connectivity to core services (Database, Redis, Gitea, CrossRef Local, OpenAlex Local)
# Called by: make status

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
# shellcheck disable=SC2034
source "${SCRIPT_DIR}/../scripts/lib/colors.sh" 2>/dev/null || {
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;36m'
    NC='\033[0m'
}

# Determine environment from argument or running containers
ENV="${1:-}"
if [ -z "$ENV" ]; then
    RUNNING=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -oE 'scitex-cloud-(dev|staging|prod)-django' | head -1 || echo "")
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

echo "🔌 Service Health:"

# Database check
DB_OK=$(docker exec "$CONTAINER" python manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('ok')" 2>/dev/null | tail -1 || echo "")
if [ "$DB_OK" = "ok" ]; then
    echo -e "  [OK] Database: connected"
else
    echo -e "  ${RED}[FAIL] Database: connection failed${NC}"
fi

# Redis check
REDIS_OK=$(docker exec "$CONTAINER" python manage.py shell -c "from django.core.cache import cache; cache.set('_health', 1, 10); print('ok' if cache.get('_health') else '')" 2>/dev/null | tail -1 || echo "")
if [ "$REDIS_OK" = "ok" ]; then
    echo -e "  [OK] Redis: connected"
else
    echo -e "  ${RED}[FAIL] Redis: connection failed${NC}"
fi

# Gitea check
GITEA_OK=$(docker exec "$CONTAINER" curl -sf http://gitea:3000/api/v1/version 2>/dev/null | grep -q version && echo "ok" || echo "")
if [ "$GITEA_OK" = "ok" ]; then
    echo -e "  [OK] Gitea: responding"
else
    echo -e "  ${YELLOW}[WARN] Gitea: not responding (may still be starting)${NC}"
fi

# CrossRef Local check (direct module detection)
CROSSREF_OK=$(docker exec "$CONTAINER" python -c "
from scitex.scholar.local_dbs import crossref_scitex
assert hasattr(crossref_scitex, 'search')
print('ok')
" 2>/dev/null | tail -1 || echo "")
if [ "$CROSSREF_OK" = "ok" ]; then
    echo -e "  [OK] CrossRef Local: ready"
else
    echo -e "  ${YELLOW}[WARN] CrossRef Local: not available${NC}"
fi

# OpenAlex Local check (direct module detection - sibling of CrossRef)
OPENALEX_OK=$(docker exec "$CONTAINER" python -c "
from scitex.scholar.local_dbs import openalex_scitex
assert hasattr(openalex_scitex, 'search')
print('ok')
" 2>/dev/null | tail -1 || echo "")
if [ "$OPENALEX_OK" = "ok" ]; then
    echo -e "  [OK] OpenAlex Local: ready"
else
    echo -e "  ${YELLOW}[WARN] OpenAlex Local: not available${NC}"
fi

# scitex-container module check (host-mounted, required for terminal)
CONTAINER_MOD_OK=$(docker exec "$CONTAINER" python -c "
import scitex_container
print('ok')
" 2>/dev/null | tail -1 || echo "")
if [ "$CONTAINER_MOD_OK" = "ok" ]; then
    echo -e "  [OK] scitex-container: mounted"
else
    echo -e "  ${RED}[FAIL] scitex-container: not mounted (terminals will fail)${NC}"
    echo -e "    Fix: restart Django container to pick up volume mount"
fi

# Vite manifest check (static files built correctly)
VITE_OK=$(docker exec "$CONTAINER" python -c "
import json, os
manifest = '/app/staticfiles/vite/.vite/manifest.json'
if os.path.exists(manifest):
    with open(manifest) as f:
        data = json.load(f)
    print('ok' if len(data) > 0 else '')
else:
    print('')
" 2>/dev/null | tail -1 || echo "")
if [ "$VITE_OK" = "ok" ]; then
    echo -e "  [OK] Vite: static files built"
else
    echo -e "  ${RED}[FAIL] Vite: manifest missing (styles/JS may be broken)${NC}"
    echo -e "    Fix: restart Django container (entrypoint runs vite build)"
fi

# Pending migrations check
MIGRATIONS_OK=$(docker exec "$CONTAINER" python manage.py showmigrations --plan 2>/dev/null | grep -c '^\[ \]' 2>/dev/null) || MIGRATIONS_OK=0
if [ "$MIGRATIONS_OK" = "0" ]; then
    echo -e "  [OK] Migrations: all applied"
else
    echo -e "  ${YELLOW}[WARN] Migrations: ${MIGRATIONS_OK} pending${NC}"
    echo -e "    Fix: restart Django container (entrypoint runs migrate)"
fi
