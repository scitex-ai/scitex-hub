#!/bin/bash
# Migration Status Checker
# Detects unapplied Django migrations
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
        exit 0
    fi
    ENV=$(echo "$RUNNING" | sed 's/scitex-cloud-//' | sed 's/-django.*//')
fi

CONTAINER="scitex-cloud-${ENV}-django-1"

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$" 2>/dev/null; then
    exit 0
fi

echo -e "${BLUE}📦 Migration Status:${NC}"

# Get unapplied migrations
UNAPPLIED=$(docker exec "$CONTAINER" python manage.py showmigrations --plan 2>/dev/null | grep '\[ \]' || echo "")

if [ -z "$UNAPPLIED" ]; then
    echo -e "  ${GREEN}✓ All migrations applied${NC}"
else
    COUNT=$(echo "$UNAPPLIED" | wc -l)
    echo -e "  ${RED}✗ $COUNT unapplied migration(s)${NC}"
    echo "$UNAPPLIED" | head -5 | while read line; do
        echo -e "    ${YELLOW}$line${NC}"
    done
    if [ "$COUNT" -gt 5 ]; then
        echo -e "    ${YELLOW}... and $((COUNT - 5)) more${NC}"
    fi
    echo -e "  ${BLUE}💡 Fix: make env=$ENV migrate${NC}"
fi

echo ""
