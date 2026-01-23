#!/bin/bash
# -*- coding: utf-8 -*-
# Quick script to list users without needing to rebuild containers
# Usage: ./scripts/maintenance/list_users.sh [prod|dev]

ORIG_DIR="$(pwd)"
SCRIPT_DIR="$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)"
GIT_ROOT="$(git rev-parse --show-toplevel 2> /dev/null)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

ENV="${1:-prod}"

if [ "$ENV" = "prod" ]; then
    CONTAINER="scitex-cloud-prod-django-1"
elif [ "$ENV" = "dev" ]; then
    CONTAINER="scitex-cloud-dev-django-1"
else
    echo -e "${RED}Error: Invalid environment. Use 'prod' or 'dev'${NC}"
    exit 1
fi

# Check if container is running
if ! docker ps | grep -q "$CONTAINER"; then
    echo -e "${RED}Error: Container $CONTAINER is not running${NC}"
    exit 1
fi

echo -e "${GREEN}Listing users in $ENV environment...${NC}"
echo ""

# Execute Python script in container using -c flag (more reliable)
docker exec "$CONTAINER" python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
count = User.objects.count()

print('=' * 80)
print(f'Total users: {count}')
print('=' * 80)
print()

if count > 0:
    # Header
    header = f\"{'Username':<20} {'Email':<35} {'Active':<8} {'Staff':<8} {'Super':<8} {'Joined':<12}\"
    print(header)
    print('-' * len(header))

    # List users
    for user in User.objects.all().order_by('date_joined'):
        is_active = 'Yes' if user.is_active else 'No'
        is_staff = 'Yes' if user.is_staff else 'No'
        is_super = 'Yes' if user.is_superuser else 'No'
        joined = user.date_joined.strftime('%Y-%m-%d')

        print(f\"{user.username:<20} {user.email:<35} {is_active:<8} {is_staff:<8} {is_super:<8} {joined:<12}\")
else:
    print('No users found.')
"

echo ""
echo -e "${GREEN}Done.${NC}"
