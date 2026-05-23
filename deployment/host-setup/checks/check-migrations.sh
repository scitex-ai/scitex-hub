#!/bin/bash
# Migration Status Checker
# Detects unapplied Django migrations
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
    RUNNING=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -oE 'scitex-hub-(dev|prod)-django' | head -1 || echo "")
    if [ -z "$RUNNING" ]; then
        exit 0
    fi
    ENV=$(echo "$RUNNING" | sed 's/scitex-hub-//' | sed 's/-django.*//')
fi

CONTAINER="scitex-hub-${ENV}-django-1"

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$" 2>/dev/null; then
    exit 0
fi

echo "📦 Migrations:"

# Get unapplied migrations
UNAPPLIED=$(docker exec "$CONTAINER" python manage.py showmigrations --plan 2>/dev/null | grep '\[ \]' || echo "")

if [ -z "$UNAPPLIED" ]; then
    echo "  [OK] All migrations applied"
else
    COUNT=$(echo "$UNAPPLIED" | wc -l)
    echo -e "  ${RED}[FAIL] $COUNT unapplied migration(s)${NC}"
    echo "$UNAPPLIED" | head -5 | while read -r line; do
        echo -e "    ${YELLOW}$line${NC}"
    done
    if [ "$COUNT" -gt 5 ]; then
        echo -e "    ${YELLOW}... and $((COUNT - 5)) more${NC}"
    fi
    echo -e "    Fix: make env=$ENV migrate"
fi
