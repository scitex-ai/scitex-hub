#!/bin/bash
# Check Visitor Pool Health
# Verifies visitor users exist and pool allocations are valid

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

echo "👥 Visitors:"

# Find running django container
CONTAINER=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -E 'scitex-hub-(dev|prod)-django' | head -1 || echo "")

if [ -z "$CONTAINER" ]; then
    echo -e "  ${YELLOW}[WARN] No Django container running${NC}"
    exit 0
fi

# Check visitor pool health via Django shell
RESULT=$(docker exec "$CONTAINER" python manage.py shell -c "
from django.contrib.auth.models import User
from django.conf import settings
from apps.project_app.models import Project, VisitorAllocation
from django.utils import timezone

# Get pool size from settings
pool_size = int(os.environ.get('SCITEX_CLOUD_VISITOR_POOL_SIZE', getattr(settings, 'SCITEX_CLOUD_VISITOR_POOL_SIZE', 4)))

# Check visitor users
missing_users = []
missing_projects = []
for i in range(1, pool_size + 1):
    username = f'visitor-{i:03d}'
    try:
        u = User.objects.get(username=username)
        if not Project.objects.filter(owner=u, slug='default-project').exists():
            missing_projects.append(username)
    except User.DoesNotExist:
        missing_users.append(username)

# Check allocations
total = VisitorAllocation.objects.count()
active = VisitorAllocation.objects.filter(is_active=True, expires_at__gt=timezone.now()).count()
expired = VisitorAllocation.objects.filter(is_active=True, expires_at__lte=timezone.now()).count()

# Output status
if missing_users:
    print(f'MISSING_USERS:{len(missing_users)}')
elif missing_projects:
    print(f'MISSING_PROJECTS:{len(missing_projects)}')
else:
    print('OK')
print(f'POOL:{pool_size-active}/{pool_size}')
print(f'EXPIRED:{expired}')
" 2>&1 | grep -E "^(OK$|MISSING_USERS:|MISSING_PROJECTS:|POOL:|EXPIRED:)" || echo "ERROR")

if echo "$RESULT" | grep -q "^OK"; then
    POOL_STATUS=$(echo "$RESULT" | grep "^POOL:" | cut -d: -f2)
    EXPIRED=$(echo "$RESULT" | grep "^EXPIRED:" | cut -d: -f2)
    echo "  [OK] Pool healthy: $POOL_STATUS slots free"
    if [ "$EXPIRED" != "0" ]; then
        echo -e "  ${YELLOW}[WARN] $EXPIRED expired allocations (run: reset_visitor_pool --free-expired)${NC}"
    fi
elif echo "$RESULT" | grep -q "^MISSING_USERS:"; then
    COUNT=$(echo "$RESULT" | grep "^MISSING_USERS:" | cut -d: -f2)
    echo -e "  ${RED}[FAIL] Missing $COUNT visitor users${NC}"
    echo -e "    Fix: docker exec $CONTAINER python manage.py create_visitor_pool"
    echo -e "    Alt: make ENV=dev fresh-start"
elif echo "$RESULT" | grep -q "^MISSING_PROJECTS:"; then
    COUNT=$(echo "$RESULT" | grep "^MISSING_PROJECTS:" | cut -d: -f2)
    echo -e "  ${RED}[FAIL] Missing $COUNT visitor projects${NC}"
    echo -e "    Fix: docker exec $CONTAINER python manage.py create_visitor_pool"
else
    echo -e "  ${RED}[FAIL] Could not check visitor pool${NC}"
    echo -e "    Fix: docker exec $CONTAINER python manage.py create_visitor_pool"
    echo -e "    Alt: docker exec $CONTAINER python manage.py reset_visitor_pool"
fi
