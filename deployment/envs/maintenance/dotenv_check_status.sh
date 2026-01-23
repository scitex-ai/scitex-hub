#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-20 11:30:24 (ywatanabe)"
# File: ./scripts/deployment/maintenance/dotenv_check_status.sh

ORIG_DIR="$(pwd)"
THIS_DIR="$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)"
LOG_PATH="$THIS_DIR/.$(basename $0).log"
ERR_PATH="$THIS_DIR/.$(basename $0).err"
echo -e > "$LOG_PATH"
echo -e > "$ERR_PATH"

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

# Check environment configuration files status
# Validates dotenv files for development and production

set -euo pipefail

# Color codes
BLUE='\033[0;34m'

echo_header() { echo -e "${BLUE}$1${NC}"; }

# Project root
PROJECT_ROOT="/home/ywatanabe/proj/scitex-cloud"

# Critical environment variables that should exist
CRITICAL_VARS=(
    "SCITEX_CLOUD_DJANGO_SECRET_KEY"
    "SCITEX_CLOUD_SCITEX_CLOUD_DJANGO_SETTINGS_MODULE"
    "SCITEX_CLOUD_DB_NAME"
    "SCITEX_CLOUD_DB_USER"
    "SCITEX_CLOUD_DB_PASSWORD"
)

# Check if a dotenv file exists and is readable
check_file_exists() {
    local file=$1
    local name=$2

    if [ -f "$file" ]; then
        echo_success "  ✓ File exists: $file"

        # Check permissions
        if [ -r "$file" ]; then
            echo_success "  ✓ File is readable"
        else
            echo_error "  ✗ File is not readable"
            return 1
        fi

        # File size
        SIZE=$(du -h "$file" | cut -f1)
        echo_info "  Size: $SIZE"

        # Line count
        LINES=$(wc -l < "$file")
        echo_info "  Lines: $LINES"

        return 0
    else
        echo_error "  ✗ File not found: $file"
        return 1
    fi
}

# Check for critical variables in dotenv file
check_critical_vars() {
    local file=$1
    local env_suffix=$2 # Either "_DEV" or "_PROD"
    local missing_vars=()

    echo_info "  Critical Variables:"

    # Check Django settings
    if grep -q "^export SCITEX_CLOUD_DJANGO_SECRET_KEY=" "$file" 2> /dev/null; then
        echo_success "    ✓ SCITEX_CLOUD_DJANGO_SECRET_KEY is set"
    else
        echo_error "    ✗ SCITEX_CLOUD_DJANGO_SECRET_KEY is missing"
        missing_vars+=("SCITEX_CLOUD_DJANGO_SECRET_KEY")
    fi

    if grep -q "^export SCITEX_CLOUD_SCITEX_CLOUD_DJANGO_SETTINGS_MODULE=" "$file" 2> /dev/null; then
        echo_success "    ✓ SCITEX_CLOUD_SCITEX_CLOUD_DJANGO_SETTINGS_MODULE is set"
    else
        echo_error "    ✗ SCITEX_CLOUD_SCITEX_CLOUD_DJANGO_SETTINGS_MODULE is missing"
        missing_vars+=("SCITEX_CLOUD_SCITEX_CLOUD_DJANGO_SETTINGS_MODULE")
    fi

    # Check database variables with environment suffix
    for var in "SCITEX_CLOUD_DB_NAME" "SCITEX_CLOUD_DB_USER" "SCITEX_CLOUD_DB_PASSWORD"; do
        if grep -q "^export ${var}${env_suffix}=" "$file" 2> /dev/null; then
            echo_success "    ✓ ${var}${env_suffix} is set"
        else
            echo_error "    ✗ ${var}${env_suffix} is missing"
            missing_vars+=("${var}${env_suffix}")
        fi
    done

    if [ ${#missing_vars[@]} -gt 0 ]; then
        return 1
    fi
    return 0
}

# Check development environment
check_development() {
    echo_header "=== Development Environment Configuration ==="
    echo

    # Check dotenv.dev
    echo_info "Development Dotenv File:"
    if check_file_exists "$PROJECT_ROOT/deployment/dotenvs/dotenv.dev" "Development"; then
        echo

        # Check critical variables
        check_critical_vars "$PROJECT_ROOT/deployment/dotenvs/dotenv.dev" "_DEV"
        echo

        # Check if this is development environment
        if grep -q "settings_dev" "$PROJECT_ROOT/deployment/dotenvs/dotenv.dev" 2> /dev/null; then
            echo_success "  ✓ Configured for development environment"
        else
            echo_warning "  ⚠ Environment configuration unclear"
        fi
    fi
    echo
}

# Check production environment
check_production() {
    echo_header "=== Production Environment Configuration ==="
    echo

    # Check dotenv.prod
    echo_info "Production Dotenv File:"
    if check_file_exists "$PROJECT_ROOT/deployment/dotenvs/dotenv.prod" "Production"; then
        echo

        # Check critical variables
        check_critical_vars "$PROJECT_ROOT/deployment/dotenvs/dotenv.prod" "_PROD"
        echo

        # Check if this is production environment
        if grep -q "settings_prod" "$PROJECT_ROOT/deployment/dotenvs/dotenv.prod" 2> /dev/null; then
            echo_success "  ✓ Configured for production environment"
        else
            echo_warning "  ⚠ Environment configuration unclear"
        fi

        # Check for production database
        if grep -q "SCITEX_CLOUD_DB_NAME_PROD" "$PROJECT_ROOT/deployment/dotenvs/dotenv.prod" 2> /dev/null; then
            echo_success "  ✓ Production database configured"
        else
            echo_warning "  ⚠ Production database configuration not found"
        fi
    fi
    echo
}

# Check example file
check_example() {
    echo_header "=== Example Environment File ==="
    echo

    echo_info "Example Dotenv File:"
    if check_file_exists "$PROJECT_ROOT/deployment/dotenvs/dotenv.example" "Example"; then
        echo_info "  This file serves as a template for new installations"
    fi
    echo
}

# Check root .env file
check_root_env() {
    echo_header "=== Root .env File ==="
    echo

    echo_info "Root .env File:"
    if check_file_exists "$PROJECT_ROOT/.env" "Root"; then
        echo

        # Determine which environment it's configured for
        DEBUG_VALUE=$(grep "^DEBUG=" "$PROJECT_ROOT/.env" 2> /dev/null | cut -d'=' -f2)
        if [ "$DEBUG_VALUE" = "True" ] || [ "$DEBUG_VALUE" = "true" ] || [ "$DEBUG_VALUE" = "1" ]; then
            echo_info "  Environment: Development (DEBUG=True)"
        else
            echo_info "  Environment: Production (DEBUG=False)"
        fi
    else
        echo_warning "  ⚠ Root .env file not found"
        echo_info "  You may need to create one by copying from deployment/dotenvs/"
    fi
    echo
}

# Check environment variable consistency
check_consistency() {
    echo_header "=== Environment Variable Consistency ==="
    echo

    # Check if critical variables differ between dev and prod
    echo_info "Checking variable differences between dev and prod:"
    echo

    for var in "SCITEX_CLOUD_DB_NAME" "SCITEX_CLOUD_DB_USER"; do
        if [ -f "$PROJECT_ROOT/deployment/dotenvs/dotenv.dev" ] && [ -f "$PROJECT_ROOT/deployment/dotenvs/dotenv.prod" ]; then
            DEV_VAL=$(grep "^export ${var}_DEV=" "$PROJECT_ROOT/deployment/dotenvs/dotenv.dev" 2> /dev/null | cut -d'=' -f2)
            PROD_VAL=$(grep "^export ${var}_PROD=" "$PROJECT_ROOT/deployment/dotenvs/dotenv.prod" 2> /dev/null | cut -d'=' -f2)

            if [ -n "$DEV_VAL" ] && [ -n "$PROD_VAL" ]; then
                if [ "$DEV_VAL" = "$PROD_VAL" ]; then
                    echo_warning "  ⚠ $var is identical in dev and prod"
                    echo_info "    Consider using different values to avoid confusion"
                else
                    echo_success "  ✓ $var differs between environments"
                fi
            else
                echo_info "  ○ $var not fully configured in both environments"
            fi
        fi
    done
    echo
}

# Security recommendations
show_security_recommendations() {
    echo_header "=== Security Recommendations ==="
    echo

    echo_info "File Permissions:"
    if [ -f "$PROJECT_ROOT/deployment/dotenvs/dotenv.prod" ]; then
        PERMS=$(stat -c "%a" "$PROJECT_ROOT/deployment/dotenvs/dotenv.prod")
        if [ "$PERMS" = "600" ] || [ "$PERMS" = "400" ]; then
            echo_success "  ✓ Production dotenv has restrictive permissions ($PERMS)"
        else
            echo_warning "  ⚠ Production dotenv permissions: $PERMS"
            echo_info "  Consider: chmod 600 $PROJECT_ROOT/deployment/dotenvs/dotenv.prod"
        fi
    fi
    echo

    echo_info "Best Practices:"
    echo_info "  • Never commit .env files with secrets to git"
    echo_info "  • Use different SCITEX_CLOUD_DJANGO_SECRET_KEY for dev and prod"
    echo_info "  • Use different database credentials for dev and prod"
    echo_info "  • Keep production DEBUG=False"
    echo_info "  • Set specific SCITEX_CLOUD_ALLOWED_HOSTS in production"
    echo
}

# Main
main() {
    echo_header "=== Environment Configuration Status ==="
    echo

    check_development
    check_production
    check_example
    check_root_env
    check_consistency
    show_security_recommendations

    echo -e "\nLogs: $LOG_PATH (stdout) | $ERR_PATH (stderr)"
}

main "$@" > >(tee -a "$LOG_PATH") 2> >(tee -a "$ERR_PATH" >&2)
