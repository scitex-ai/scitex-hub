#!/bin/bash
# DB Module Data Integrity Checker
# Verifies AppsModule DB records match the registry (seed/rename commands applied).
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

# Auto-detect running environment
ENV="${1:-}"
if [ -z "$ENV" ]; then
    RUNNING=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -oE 'scitex-cloud-(dev|prod)-django' | head -1 || echo "")
    if [ -z "$RUNNING" ]; then
        exit 0
    fi
    ENV=$(echo "$RUNNING" | sed 's/scitex-cloud-//' | sed 's/-django.*//')
fi

CONTAINER="scitex-cloud-${ENV}-django-1"

if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$" 2>/dev/null; then
    exit 0
fi

echo "🗄️  DB Modules:"

# Run a quick Python check against the DB
RESULT=$(docker exec "$CONTAINER" python manage.py shell -c "
from apps.workspace.apps_app.models import AppsModule
from apps.infra.workspace_app.registry import get_all_modules

# Registry module names
registry_names = {m.name for m in get_all_modules()}

# DB module names
db_names = set(AppsModule.objects.values_list('module_name', flat=True))

stale = db_names - registry_names - {'marketplace'}  # ignore pre-rename records
missing = registry_names - db_names

issues = []
if 'hub' in db_names:
    issues.append('RENAME:hub→home  (run: python manage.py rename_hub_to_home)')
if 'apps' in db_names and 'store' not in db_names:
    issues.append('RENAME:apps→store  (run: python manage.py rename_apps_to_store)')
if missing:
    issues.append(f'MISSING:{sorted(missing)}  (run: python manage.py seed_apps)')

if issues:
    for i in issues:
        print('ISSUE: ' + i)
else:
    print('OK')
" 2>/dev/null || echo "ERROR: could not query DB")

if echo "$RESULT" | grep -q "^OK$"; then
    echo "  [OK] All module records are up to date"
elif echo "$RESULT" | grep -q "^ERROR"; then
    echo -e "  ${YELLOW}[WARN] Could not check module records${NC}"
else
    while IFS= read -r line; do
        if echo "$line" | grep -q "^ISSUE:"; then
            MSG="${line#ISSUE: }"
            if echo "$MSG" | grep -q "^RENAME"; then
                echo -e "  ${YELLOW}[WARN] $MSG${NC}"
            else
                echo -e "  ${RED}[FAIL] $MSG${NC}"
            fi
        fi
    done <<<"$RESULT"
    echo -e "    Fix: make env=${ENV} seed"
fi
