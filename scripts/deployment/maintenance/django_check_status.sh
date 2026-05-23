#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-20 11:37:45 (ywatanabe)"
# File: ./scripts/deployment/maintenance/django_check_status.sh

ORIG_DIR="$(pwd)"
THIS_DIR="$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)"
LOG_PATH="$THIS_DIR/.$(basename $0).log"
echo > "$LOG_PATH"

BLACK='\033[0;30m'
LIGHT_GRAY='\033[0;37m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo_info() { echo -e "${LIGHT_GRAY}$1${NC}"; }
echo_success() { echo -e "${GREEN}$1${NC}"; }
echo_warning() { echo -e "${YELLOW}$1${NC}"; }
echo_error() { echo -e "${RED}$1${NC}"; }
# ---------------------------------------

ERR_PATH="$THIS_DIR/.$(basename $0).err"
echo > "$ERR_PATH"

# Check Django application status
# Works for both development and production

set -euo pipefail

# Color codes
BLUE='\033[0;34m'

echo_header() { echo -e "${BLUE}$1${NC}"; }

# Project root
PROJECT_ROOT="/home/ywatanabe/proj/scitex-cloud"

# Detect environment based on DEBUG setting or running process
detect_environment() {
    # Check if .env exists and what DEBUG is set to
    if [ -f "$PROJECT_ROOT/.env" ]; then
        DEBUG_VALUE=$(grep "^DEBUG=" "$PROJECT_ROOT/.env" 2> /dev/null | cut -d'=' -f2)
        if [ "$DEBUG_VALUE" = "True" ] || [ "$DEBUG_VALUE" = "true" ] || [ "$DEBUG_VALUE" = "1" ]; then
            echo "development"
        else
            echo "production"
        fi
    else
        # Fallback: check if dev or prod service is running
        if systemctl is-active --quiet scitex_hub_prod 2> /dev/null; then
            echo "production"
        elif systemctl is-active --quiet scitex_hub_dev 2> /dev/null; then
            echo "development"
        else
            echo "unknown"
        fi
    fi
}

# Check Django installation
check_django_installation() {
    echo_header "=== Django Installation ==="
    echo

    # Check if Python virtual environment exists
    echo_info "Python Environment:"
    if [ -d "$PROJECT_ROOT/.env" ] || [ -d "$PROJECT_ROOT/venv" ] || [ -d "$PROJECT_ROOT/.venv" ]; then
        echo_success "  ✓ Virtual environment directory found"
    else
        echo_warning "  ⚠ No virtual environment directory found"
    fi

    # Check Django version
    if command -v python3 > /dev/null 2>&1; then
        DJANGO_VERSION=$(python3 -c "import django; print(django.get_version())" 2> /dev/null || echo "Not installed")
        if [ "$DJANGO_VERSION" != "Not installed" ]; then
            echo_success "  ✓ Django installed: version $DJANGO_VERSION"
        else
            echo_error "  ✗ Django not installed"
        fi
    fi
    echo

    # Check Python version
    if command -v python3 > /dev/null 2>&1; then
        PYTHON_VERSION=$(python3 --version | awk '{print $2}')
        echo_info "Python Version: $PYTHON_VERSION"
    fi
    echo
}

# Check Django settings files
check_settings_files() {
    echo_header "=== Django Settings Files ==="
    echo

    # Check settings directory
    if [ -d "$PROJECT_ROOT/config/settings" ]; then
        echo_success "✓ Settings directory exists"
        echo

        # List settings files
        echo_info "Settings Files:"
        for file in settings_shared.py settings_dev.py settings_prod.py; do
            if [ -f "$PROJECT_ROOT/config/settings/$file" ]; then
                echo_success "  ✓ $file exists"
                SIZE=$(du -h "$PROJECT_ROOT/config/settings/$file" | cut -f1)
                LINES=$(wc -l < "$PROJECT_ROOT/config/settings/$file")
                echo_info "    Size: $SIZE, Lines: $LINES"
            else
                echo_error "  ✗ $file not found"
            fi
        done
    else
        echo_error "✗ Settings directory not found"
    fi
    echo
}

# Check Django apps
check_django_apps() {
    echo_header "=== Django Applications ==="
    echo

    if [ -d "$PROJECT_ROOT/apps" ]; then
        echo_success "✓ Apps directory exists"
        echo

        # Count and list apps
        APP_COUNT=$(find "$PROJECT_ROOT/apps" -maxdepth 1 -type d -name "*_app" | wc -l)
        echo_info "Installed Apps: $APP_COUNT"
        echo

        # List each app with details
        for app_dir in "$PROJECT_ROOT/apps"/*_app; do
            if [ -d "$app_dir" ]; then
                echo
                APP_NAME=$(basename "$app_dir")
                echo_info "  $APP_NAME:"

                # Check for key files
                if [ -f "$app_dir/models.py" ]; then
                    MODEL_COUNT=$(grep -c "^class.*models\.Model" "$app_dir/models.py" 2> /dev/null || echo 0)
                    echo_info "    Models: $MODEL_COUNT"
                fi

                if [ -f "$app_dir/views.py" ]; then
                    VIEW_COUNT=$(grep -c "^def \|^class.*View" "$app_dir/views.py" 2> /dev/null || echo 0)
                    echo_info "    Views: $VIEW_COUNT"
                fi

                if [ -d "$app_dir/templates" ]; then
                    TEMPLATE_COUNT=$(find "$app_dir/templates" -name "*.html" | wc -l)
                    echo_info "    Templates: $TEMPLATE_COUNT"
                fi
            fi
        done
    else
        echo_error "✗ Apps directory not found"
    fi
    echo
}

# Run Django system checks
run_django_checks() {
    echo_header "=== Django System Checks ==="
    echo

    cd "$PROJECT_ROOT"

    # Try to run Django check command
    ENV=$(detect_environment)

    echo_info "Running Django checks for $ENV environment..."
    echo

    if [ "$ENV" = "development" ]; then
        export SCITEX_CLOUD_DJANGO_SETTINGS_MODULE="config.settings.settings_dev"
    else
        export SCITEX_CLOUD_DJANGO_SETTINGS_MODULE="config.settings.settings_prod"
    fi

    if python3 manage.py check --deploy 2>&1; then
        echo
        echo_success "✓ Django deployment checks passed"
    else
        echo
        echo_warning "⚠ Some Django checks failed (see above)"
    fi
    echo
}

# Check database migrations
check_migrations() {
    echo_header "=== Database Migrations ==="
    echo

    cd "$PROJECT_ROOT"

    ENV=$(detect_environment)

    if [ "$ENV" = "development" ]; then
        export SCITEX_CLOUD_DJANGO_SETTINGS_MODULE="config.settings.settings_dev"
    else
        export SCITEX_CLOUD_DJANGO_SETTINGS_MODULE="config.settings.settings_prod"
    fi

    # Check if there are unapplied migrations
    echo_info "Checking migration status..."
    echo

    if python3 manage.py showmigrations 2> /dev/null | grep -q "\[ \]"; then
        echo_warning "⚠ Unapplied migrations detected:"
        python3 manage.py showmigrations 2> /dev/null | grep "\[ \]" | sed 's/^/  /'
        echo
        echo_info "Run: python3 manage.py migrate"
    else
        echo_success "✓ All migrations applied"
    fi
    echo
}

# Check static files
check_static_files() {
    echo_header "=== Static Files ==="
    echo

    # Check static directory
    if [ -d "$PROJECT_ROOT/static" ]; then
        echo_success "✓ Static directory exists"

        STATIC_SIZE=$(du -sh "$PROJECT_ROOT/static" 2> /dev/null | cut -f1)
        STATIC_FILES=$(find "$PROJECT_ROOT/static" -type f | wc -l)

        echo_info "  Size: $STATIC_SIZE"
        echo_info "  Files: $STATIC_FILES"
    else
        echo_warning "⚠ Static directory not found"
        echo_info "  Run: python3 manage.py collectstatic"
    fi
    echo

    # Check staticfiles directory (collected static)
    if [ -d "$PROJECT_ROOT/staticfiles" ]; then
        echo_success "✓ Staticfiles directory exists (collected)"

        STATICFILES_SIZE=$(du -sh "$PROJECT_ROOT/staticfiles" 2> /dev/null | cut -f1)
        STATICFILES_COUNT=$(find "$PROJECT_ROOT/staticfiles" -type f | wc -l)

        echo_info "  Size: $STATICFILES_SIZE"
        echo_info "  Files: $STATICFILES_COUNT"
    else
        echo_warning "⚠ Staticfiles directory not found"
    fi
    echo
}

# Check media files
check_media_files() {
    echo_header "=== Media Files ==="
    echo

    if [ -d "$PROJECT_ROOT/media" ]; then
        echo_success "✓ Media directory exists"

        MEDIA_SIZE=$(du -sh "$PROJECT_ROOT/media" 2> /dev/null | cut -f1)
        MEDIA_FILES=$(find "$PROJECT_ROOT/media" -type f | wc -l)

        echo_info "  Size: $MEDIA_SIZE"
        echo_info "  Files: $MEDIA_FILES"
    else
        echo_warning "⚠ Media directory not found"
    fi
    echo
}

# Check log files
check_logs() {
    echo_header "=== Application Logs ==="
    echo

    if [ -d "$PROJECT_ROOT/logs" ]; then
        echo_success "✓ Logs directory exists"
        echo

        # List log files with sizes
        echo_info "Log Files:"
        find "$PROJECT_ROOT/logs" -type f -name "*.log" -exec du -h {} \; | sed 's/^/  /'
    else
        echo_warning "⚠ Logs directory not found"
    fi
    echo
}

# Main
main() {
    check_django_installation
    check_settings_files
    check_django_apps
    check_static_files
    check_media_files
    check_logs

    # Only run these if Django is installed
    if python3 -c "import django" 2> /dev/null; then
        run_django_checks
        check_migrations
    else
        echo_error "Django not installed - skipping Django-specific checks"
    fi

    echo -e "\nLogs: $LOG_PATH (stdout) | $ERR_PATH (stderr)"
}

main "$@" > >(tee -a "$LOG_PATH") 2> >(tee -a "$ERR_PATH" >&2)
