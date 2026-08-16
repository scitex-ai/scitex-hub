#!/bin/bash
# Check Visitor Pool Health
#
# Reports whether visitors can actually get a WRITABLE workspace.
#
# The number that matters is ALLOCATABLE, not "not in use". A slot is only
# handed to a visitor when ALL THREE hold (pool_manager.py _available_slots):
#
#     quarantined = False   AND   is_active = False   AND   workspace_ready = True
#
# `workspace_ready` is the security gate: it is set only after the slot's
# apptainer instance is torn down, its SLURM job cancelled, and both VERIFIED
# gone (container_teardown.py). Until then the slot is not distributable, and
# every visitor silently falls back to the shared read-only `readonly-visitor`.
#
# INCIDENT 2026-07-13 — why this file was rewritten:
#   slurmctld died on the NAS and stayed dead for >24h. Every slot re-clean
#   failed at the SLURM teardown, so 0/16 slots were allocatable and EVERY
#   visitor to scitex.ai got a read-only workspace. This check reported:
#
#       [OK] Pool healthy: 16/16 slots free
#
#   ...because it computed `pool_size - active` — "slots not currently in
#   use" — and never looked at workspace_ready or quarantined. 0-in-use and
#   0-ALLOCATABLE are indistinguishable in that metric. It sat directly
#   beside check-slurm.sh's `[FAIL] slurmctld not running` and contradicted
#   it, which is worse than silence: it gives you a reason to dismiss the FAIL.
#
#   (It was also dead code — it imported `apps.project_app.models`, a path
#   that has not existed since the apps/infra/ refactor, and used `os` without
#   importing it, so it actually printed "[FAIL] Could not check visitor pool".)
#
#   Report the gate, not a proxy for it.

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

CONTAINER=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -E 'scitex-hub-(dev|prod)-django' | head -1 || echo "")

if [ -z "$CONTAINER" ]; then
    echo -e "  ${YELLOW}[WARN] No Django container running${NC}"
    exit 0
fi

RESULT=$(docker exec "$CONTAINER" python manage.py shell -c "
from django.contrib.auth.models import User
from django.utils import timezone

from apps.infra.project_app.models import Project, VisitorAllocation
from apps.infra.project_app.services.visitor_pool import VisitorPool

pool_size = VisitorPool.POOL_SIZE

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

qs = VisitorAllocation.objects.all()
# THE gate a visitor is actually measured against.
allocatable = qs.filter(
    quarantined=False, is_active=False, workspace_ready=True
).count()
in_use = qs.filter(is_active=True, expires_at__gt=timezone.now()).count()
quarantined = qs.filter(quarantined=True).count()
not_ready = qs.filter(workspace_ready=False).count()

if missing_users:
    print(f'MISSING_USERS:{len(missing_users)}')
elif missing_projects:
    print(f'MISSING_PROJECTS:{len(missing_projects)}')
else:
    print('OK')
print(f'ALLOCATABLE:{allocatable}')
print(f'POOL_SIZE:{pool_size}')
print(f'IN_USE:{in_use}')
print(f'QUARANTINED:{quarantined}')
print(f'NOT_READY:{not_ready}')
" 2>&1 | grep -E "^(OK$|MISSING_USERS:|MISSING_PROJECTS:|ALLOCATABLE:|POOL_SIZE:|IN_USE:|QUARANTINED:|NOT_READY:)" || echo "ERROR")

field() { echo "$RESULT" | grep "^$1:" | cut -d: -f2 | head -1; }

if echo "$RESULT" | grep -q "^MISSING_USERS:"; then
    echo -e "  ${RED}[FAIL] Missing $(field MISSING_USERS) visitor users${NC}"
    echo -e "    Fix: docker exec $CONTAINER python manage.py create_visitor_pool"
    exit 0
fi

if echo "$RESULT" | grep -q "^MISSING_PROJECTS:"; then
    echo -e "  ${RED}[FAIL] Missing $(field MISSING_PROJECTS) visitor projects${NC}"
    echo -e "    Fix: docker exec $CONTAINER python manage.py create_visitor_pool"
    exit 0
fi

if ! echo "$RESULT" | grep -q "^OK"; then
    echo -e "  ${RED}[FAIL] Could not check visitor pool${NC}"
    echo -e "    Run by hand to see the error:"
    echo -e "    docker exec $CONTAINER python manage.py shell -c 'from apps.infra.project_app.models import VisitorAllocation; print(VisitorAllocation.objects.count())'"
    exit 0
fi

ALLOCATABLE=$(field ALLOCATABLE)
POOL_SIZE=$(field POOL_SIZE)
IN_USE=$(field IN_USE)
QUARANTINED=$(field QUARANTINED)
NOT_READY=$(field NOT_READY)

if [ "${ALLOCATABLE:-0}" -eq 0 ]; then
    echo -e "  ${RED}[FAIL] 0/${POOL_SIZE} slots allocatable — EVERY visitor is getting a READ-ONLY workspace${NC}"
    echo -e "    quarantined=${QUARANTINED}  not-yet-verified=${NOT_READY}  in-use=${IN_USE}"
    # Name the usual suspect instead of making someone go find it. The slot
    # re-clean cannot verify a teardown without a reachable SLURM controller,
    # so it quarantines every slot it touches.
    if ! timeout 10 squeue -h > /dev/null 2>&1; then
        echo -e "    ${RED}CAUSE: SLURM controller unreachable — the slot teardown cannot verify,${NC}"
        echo -e "    ${RED}       so every re-clean fails and quarantines its slot.${NC}"
        echo -e "    Fix: sudo systemctl start slurmctld slurmd && sinfo"
    else
        echo -e "    SLURM is up, so the re-clean should be able to run."
        echo -e "    Fix: docker exec $CONTAINER python manage.py reconcile_visitor_slots --async"
        echo -e "    Then check the worker is actually consuming (a wedged worker looks idle):"
        echo -e "      docker exec $CONTAINER-celery celery -A config inspect active"
    fi
elif [ "${ALLOCATABLE:-0}" -le 2 ]; then
    echo -e "  ${YELLOW}[WARN] only ${ALLOCATABLE}/${POOL_SIZE} slots allocatable${NC}"
    echo -e "    quarantined=${QUARANTINED}  not-yet-verified=${NOT_READY}  in-use=${IN_USE}"
else
    echo "  [OK] ${ALLOCATABLE}/${POOL_SIZE} slots allocatable (in-use=${IN_USE})"
    if [ "${QUARANTINED:-0}" -ne 0 ]; then
        echo -e "  ${YELLOW}[WARN] ${QUARANTINED} slot(s) quarantined — a re-clean failed on them${NC}"
        echo -e "    Re-clean: docker exec $CONTAINER python manage.py reconcile_visitor_slots --async"
    fi
fi
