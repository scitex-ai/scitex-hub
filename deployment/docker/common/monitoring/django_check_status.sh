#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-27 07:20:00 (ywatanabe)"
# File: ./containers/docker/scripts/maintenance/django_check_status.sh
#
# Docker-specific Django status checker

ORIG_DIR="$(pwd)"
THIS_DIR="$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)"
LOG_PATH="$THIS_DIR/.$(basename $0).log"
echo -e > "$LOG_PATH"

GIT_ROOT="$(git rev-parse --show-toplevel 2> /dev/null)"
DOCKER_DIR="$GIT_ROOT/deployment/docker/docker_dev"

# Colors
GRAY='\033[0;90m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo_info() { echo -e "${GRAY}$1${NC}"; }
echo_success() { echo -e "${GREEN}$1${NC}"; }
echo_warning() { echo -e "${YELLOW}$1${NC}"; }
echo_error() { echo -e "${RED}$1${NC}"; }
echo_header() { echo -e "${BLUE}=== $1 ===${NC}"; }

# Load environment
if [ -f "$GIT_ROOT/.env" ]; then
    set -a
    source "$GIT_ROOT/.env"
    set +a
fi

check_django_status() {
    echo_header "Django Status (Docker Compose)"
    echo

    cd "$DOCKER_DIR" || exit 1

    # Container status
    echo_info "Container Status:"
    if docker-compose -f docker-compose.dev.yml ps | grep -q "docker_web_1"; then
        STATUS=$(docker-compose -f docker-compose.dev.yml ps docker_web_1 2> /dev/null | grep docker_web_1 | awk '{print $4}')

        if echo -e "$STATUS" | grep -q "Up"; then
            echo_success "  ✓ Container running"

            # Check health status
            if echo -e "$STATUS" | grep -q "healthy"; then
                echo_success "  ✓ Health check passed"
            else
                echo_warning "  ⚠ Health check pending or failing"
            fi

            # Uptime
            UPTIME=$(docker ps --filter name=docker_web_1 --format "{{.Status}}")
            echo_info "  Uptime: $UPTIME"
        else
            echo_error "  ✗ Container not running"
            echo_info "  Status: $STATUS"
            return 1
        fi
    else
        echo_error "  ✗ Container not found"
        echo_info "  Create: cd $DOCKER_DIR && ./start_dev.sh -a start"
        return 1
    fi
    echo

    # Port bindings
    echo_info "Port Bindings:"
    docker port docker_web_1 2> /dev/null | while read line; do
        echo_info "  $line"
    done
    echo

    # Web server test
    echo_info "Web Server:"
    HTTP_PORT="${SCITEX_CLOUD_HTTP_PORT_DEV:-8000}"

    if curl -f -s "http://localhost:$HTTP_PORT" > /dev/null 2>&1; then
        echo_success "  ✓ Django accessible at http://localhost:$HTTP_PORT"

        # Check admin
        if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$HTTP_PORT/admin/" | grep -q "200\|302"; then
            echo_success "  ✓ Admin panel accessible at http://localhost:$HTTP_PORT/admin/"
        else
            echo_warning "  ⚠ Admin panel not accessible"
        fi
    else
        echo_error "  ✗ Django not accessible"
    fi
    echo

    # Django settings
    echo_info "Django Configuration:"
    SETTINGS_MODULE=$(docker-compose -f docker-compose.dev.yml exec -T web \
        python -c "import os; print(os.getenv('SCITEX_CLOUD_DJANGO_SETTINGS_MODULE', 'Not set'))" 2> /dev/null)
    echo_info "  Settings module: $SETTINGS_MODULE"

    DEBUG_MODE=$(docker-compose -f docker-compose.dev.yml exec -T web \
        python manage.py shell -c "from django.conf import settings; print(settings.DEBUG)" 2> /dev/null | tail -1)
    echo_info "  Debug mode: $DEBUG_MODE"
    echo

    # Database connection
    echo_info "Database Connection:"
    DB_CHECK=$(docker-compose -f docker-compose.dev.yml exec -T web \
        python manage.py shell -c "
from django.db import connection
try:
    cursor = connection.cursor()
    cursor.execute('SELECT 1')
    print('Connected')
except Exception as e:
    print(f'Failed: {e}')
" 2> /dev/null | tail -1)

    if echo -e "$DB_CHECK" | grep -q "Connected"; then
        echo_success "  ✓ Database connection successful"
    else
        echo_error "  ✗ Database connection failed"
        echo_info "  Error: $DB_CHECK"
    fi
    echo

    # Migrations status
    echo_info "Migrations:"
    UNAPPLIED=$(docker-compose -f docker-compose.dev.yml exec -T web \
        python manage.py showmigrations --plan 2> /dev/null | grep -c "\[ \]" || echo -e "0")

    if [ "$UNAPPLIED" -eq 0 ]; then
        echo_success "  ✓ All migrations applied"
    else
        echo_warning "  ⚠ Unapplied migrations: $UNAPPLIED"
        echo_info "  Run: docker-compose -f docker-compose.dev.yml exec web python manage.py migrate"
    fi
    echo

    # Installed apps
    echo_info "Installed Apps:"
    APP_COUNT=$(docker-compose -f docker-compose.dev.yml exec -T web \
        python manage.py shell -c "from django.conf import settings; print(len(settings.INSTALLED_APPS))" 2> /dev/null | tail -1)
    echo_info "  Total apps: $APP_COUNT"

    # Custom apps (apps under 'apps' directory)
    echo_info "  Custom apps:"
    docker-compose -f docker-compose.dev.yml exec -T web \
        python manage.py shell -c "
from django.conf import settings
custom_apps = [app for app in settings.INSTALLED_APPS if app.startswith('apps.')]
for app in custom_apps:
    print(f'    - {app}')
" 2> /dev/null | grep "apps\."
    echo

    # Static files
    echo_info "Static Files:"
    STATIC_ROOT=$(docker-compose -f docker-compose.dev.yml exec -T web \
        python manage.py shell -c "from django.conf import settings; print(settings.STATIC_ROOT)" 2> /dev/null | tail -1)
    echo_info "  Static root: $STATIC_ROOT"

    STATIC_URL=$(docker-compose -f docker-compose.dev.yml exec -T web \
        python manage.py shell -c "from django.conf import settings; print(settings.STATIC_URL)" 2> /dev/null | tail -1)
    echo_info "  Static URL: $STATIC_URL"
    echo

    # Registered users
    echo_info "Users:"
    USER_COUNT=$(docker-compose -f docker-compose.dev.yml exec -T web \
        python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
print(User.objects.count())
" 2> /dev/null | tail -1)
    echo_info "  Total users: $USER_COUNT"

    ADMIN_COUNT=$(docker-compose -f docker-compose.dev.yml exec -T web \
        python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
print(User.objects.filter(is_superuser=True).count())
" 2> /dev/null | tail -1)
    echo_info "  Superusers: $ADMIN_COUNT"
    echo

    # Resource usage
    echo_info "Resource Usage:"
    docker stats docker_web_1 --no-stream --format \
        "  CPU: {{.CPUPerc}}  |  Memory: {{.MemUsage}}  |  Net I/O: {{.NetIO}}  |  Block I/O: {{.BlockIO}}" \
        2> /dev/null
    echo

    # Recent logs
    echo_info "Recent Logs (last 5 lines):"
    docker logs docker_web_1 --tail 5 2>&1 | sed 's/^/  /'
    echo

    # Django check
    echo_info "Django System Check:"
    docker-compose -f docker-compose.dev.yml exec -T web \
        python manage.py check --deploy 2>&1 | sed 's/^/  /' | head -10
    echo

    # Summary
    echo_header "Quick Actions"
    echo_info "View logs:       docker logs docker_web_1 -f"
    echo_info "Django shell:    docker-compose -f docker-compose.dev.yml exec web python manage.py shell"
    echo_info "Run migrations:  docker-compose -f docker-compose.dev.yml exec web python manage.py migrate"
    echo_info "Collectstatic:   docker-compose -f docker-compose.dev.yml exec web python manage.py collectstatic --no-input"
    echo_info "Restart:         cd $DOCKER_DIR && ./start_dev.sh -a restart"
}

main() {
    check_django_status
}

main "$@" 2>&1 | tee -a "$LOG_PATH"

echo
echo -e "${GRAY}Log saved to: $LOG_PATH${NC}"

# EOF
