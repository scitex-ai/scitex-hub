#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2026-01-22 05:03:18 (ywatanabe)"
# File: ./scripts/maintenance/check_number_of_users.sh

ORIG_DIR="$(pwd)"
THIS_DIR="$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)"
LOG_PATH="$THIS_DIR/.$(basename $0).log"
echo > "$LOG_PATH"

GIT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"

GRAY='\033[0;90m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo_info() { echo -e "${GRAY}INFO: $1${NC}"; }
echo_success() { echo -e "${GREEN}SUCC: $1${NC}"; }
echo_warning() { echo -e "${YELLOW}WARN: $1${NC}"; }
echo_error() { echo -e "${RED}ERRO: $1${NC}"; }
echo_header() { echo_info "=== $1 ==="; }
# ---------------------------------------

main() {
    echo_header "Checking User Count"

    local container="scitex-cloud-nas-django-1"

    # Check if container is running
    if ! docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
        echo_error "Container ${container} is not running"
        exit 1
    fi

    # Query user count from Django
    local result=$(docker exec "$container" python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
total = User.objects.count()
active = User.objects.filter(is_active=True).count()
staff = User.objects.filter(is_staff=True).count()
superuser = User.objects.filter(is_superuser=True).count()
print(f'TOTAL:{total}')
print(f'ACTIVE:{active}')
print(f'STAFF:{staff}')
print(f'SUPERUSER:{superuser}')
" 2>/dev/null | grep -E "^(TOTAL|ACTIVE|STAFF|SUPERUSER):")

    if [ -z "$result" ]; then
        echo_error "Failed to query user count"
        exit 1
    fi

    local total=$(echo "$result" | grep "^TOTAL:" | cut -d: -f2)
    local active=$(echo "$result" | grep "^ACTIVE:" | cut -d: -f2)
    local staff=$(echo "$result" | grep "^STAFF:" | cut -d: -f2)
    local superuser=$(echo "$result" | grep "^SUPERUSER:" | cut -d: -f2)

    echo_success "User Statistics:"
    echo "  Total users:      $total"
    echo "  Active users:     $active"
    echo "  Staff users:      $staff"
    echo "  Superusers:       $superuser"
}

main "$@"

# EOF