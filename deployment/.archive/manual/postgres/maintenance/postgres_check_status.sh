#!/bin/bash
# -*- coding: utf-8 -*-
# Check PostgreSQL server status
# Works for both development and production

set -euo pipefail

ORIG_DIR="$(pwd)"
THIS_DIR="$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)"
LOG_PATH="$THIS_DIR/.$(basename $0).log"
ERR_PATH="$THIS_DIR/.$(basename $0).err"
echo > "$LOG_PATH"
echo > "$ERR_PATH"

# Color codes
BLACK='\033[0;30m'
LIGHT_GRAY='\033[0;37m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() { echo -e "${LIGHT_GRAY}$1${NC}"; }
echo_success() { echo -e "${GREEN}$1${NC}"; }
echo_warning() { echo -e "${YELLOW}$1${NC}"; }
echo_error() { echo -e "${RED}$1${NC}"; }
echo_header() { echo -e "${BLUE}$1${NC}"; }

# Detect environment
detect_environment() {
    # Check for production databases
    if sudo -u postgres psql -lqt 2> /dev/null | cut -d \| -f 1 | grep -qw gitea_prod; then
        echo "production"
    # Check for development databases
    elif sudo -u postgres psql -lqt 2> /dev/null | cut -d \| -f 1 | grep -qw scitex_dev; then
        echo "development"
    # Check if PostgreSQL service is running at all
    elif systemctl is-active --quiet postgresql 2> /dev/null; then
        echo "running"
    else
        echo "unknown"
    fi
}

# Check PostgreSQL general status
check_general_status() {
    echo_header "=== PostgreSQL Status ==="
    echo

    # Service status
    echo_info "Service Status:"
    if systemctl is-active --quiet postgresql; then
        echo_success "  ✓ Service active"

        # Service details
        UPTIME=$(systemctl show postgresql --property=ActiveEnterTimestamp --value)
        echo_info "  Active since: $UPTIME"

        # PostgreSQL version
        PG_VERSION=$(sudo -u postgres psql --version 2> /dev/null | awk '{print $3}')
        echo_info "  Version: $PG_VERSION"
    else
        echo_error "  ✗ Service not active"

        if systemctl is-enabled --quiet postgresql 2> /dev/null; then
            echo_warning "  ⚠ Service enabled but not running"
            echo_info "  Start with: sudo systemctl start postgresql"
        else
            echo_error "  ✗ Service not enabled"
            echo_info "  Enable with: sudo systemctl enable postgresql"
        fi
        return 1
    fi
    echo

    # Process info
    echo_info "Process Info:"
    ps aux | grep "[p]ostgres" | head -5 | sed 's/^/  /'
    echo

    # Connection test
    echo_info "Connection Test:"
    if sudo -u postgres psql -c "SELECT 1;" > /dev/null 2>&1; then
        echo_success "  ✓ Can connect to PostgreSQL"
    else
        echo_error "  ✗ Cannot connect to PostgreSQL"
    fi
    echo
}

# Check development databases
check_development() {
    echo_header "=== Development Databases ==="
    echo

    # List development databases
    echo_info "Development Databases:"
    sudo -u postgres psql -lqt 2> /dev/null | cut -d \| -f 1 | grep -E "scitex_dev|gitea_dev" | sed 's/^/  /' || echo_warning "  No development databases found"
    echo

    # Check scitex_dev database
    if sudo -u postgres psql -lqt 2> /dev/null | cut -d \| -f 1 | grep -qw scitex_dev; then
        echo_info "SciTeX Development Database:"
        echo_success "  ✓ Database exists: scitex_dev"

        # Database size
        DB_SIZE=$(sudo -u postgres psql -d scitex_dev -t -c "SELECT pg_size_pretty(pg_database_size('scitex_dev'));" 2> /dev/null | tr -d ' ')
        echo_info "  Size: $DB_SIZE"

        # Connection count
        CONN_COUNT=$(sudo -u postgres psql -d scitex_dev -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname='scitex_dev';" 2> /dev/null | tr -d ' ')
        echo_info "  Active connections: $CONN_COUNT"

        # Table count
        TABLE_COUNT=$(sudo -u postgres psql -d scitex_dev -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" 2> /dev/null | tr -d ' ')
        echo_info "  Tables: $TABLE_COUNT"
    else
        echo_warning "  ⚠ Database scitex_dev not found"
    fi
    echo

    # Check gitea_dev database
    if sudo -u postgres psql -lqt 2> /dev/null | cut -d \| -f 1 | grep -qw gitea_dev; then
        echo_info "Gitea Development Database:"
        echo_success "  ✓ Database exists: gitea_dev"

        DB_SIZE=$(sudo -u postgres psql -d gitea_dev -t -c "SELECT pg_size_pretty(pg_database_size('gitea_dev'));" 2> /dev/null | tr -d ' ')
        echo_info "  Size: $DB_SIZE"
    else
        echo_warning "  ⚠ Database gitea_dev not found"
    fi
    echo
}

# Check production databases
check_production() {
    echo_header "=== Production Databases ==="
    echo

    # List production databases
    echo_info "Production Databases:"
    sudo -u postgres psql -lqt 2> /dev/null | cut -d \| -f 1 | grep -E "scitex_prod|gitea_prod" | sed 's/^/  /' || echo_warning "  No production databases found"
    echo

    # Check scitex_prod database
    if sudo -u postgres psql -lqt 2> /dev/null | cut -d \| -f 1 | grep -qw scitex_prod; then
        echo_info "SciTeX Production Database:"
        echo_success "  ✓ Database exists: scitex_prod"

        # Database size
        DB_SIZE=$(sudo -u postgres psql -d scitex_prod -t -c "SELECT pg_size_pretty(pg_database_size('scitex_prod'));" 2> /dev/null | tr -d ' ')
        echo_info "  Size: $DB_SIZE"

        # Connection count
        CONN_COUNT=$(sudo -u postgres psql -d scitex_prod -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname='scitex_prod';" 2> /dev/null | tr -d ' ')
        echo_info "  Active connections: $CONN_COUNT"

        # Table count
        TABLE_COUNT=$(sudo -u postgres psql -d scitex_prod -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" 2> /dev/null | tr -d ' ')
        echo_info "  Tables: $TABLE_COUNT"
    else
        echo_warning "  ⚠ Database scitex_prod not found"
    fi
    echo

    # Check gitea_prod database
    if sudo -u postgres psql -lqt 2> /dev/null | cut -d \| -f 1 | grep -qw gitea_prod; then
        echo_info "Gitea Production Database:"
        echo_success "  ✓ Database exists: gitea_prod"

        DB_SIZE=$(sudo -u postgres psql -d gitea_prod -t -c "SELECT pg_size_pretty(pg_database_size('gitea_prod'));" 2> /dev/null | tr -d ' ')
        echo_info "  Size: $DB_SIZE"

        # Connection count
        CONN_COUNT=$(sudo -u postgres psql -d gitea_prod -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname='gitea_prod';" 2> /dev/null | tr -d ' ')
        echo_info "  Active connections: $CONN_COUNT"
    else
        echo_warning "  ⚠ Database gitea_prod not found"
    fi
    echo
}

# Show all databases
show_all_databases() {
    echo_info "All Databases:"
    sudo -u postgres psql -lqt 2> /dev/null | cut -d \| -f 1 | grep -v "^$" | grep -v "template" | sed 's/^/  /'
    echo
}

# Main
main() {
    # Always show general status first
    check_general_status || exit 1

    ENV=$(detect_environment)

    case $ENV in
        production)
            check_production
            check_development
            ;;
        development)
            check_development
            check_production
            ;;
        running)
            show_all_databases
            ;;
        unknown)
            echo_warning "=== PostgreSQL Status ==="
            echo_error "✗ PostgreSQL not running"
            echo
            echo_info "Check service status:"
            echo_info "  sudo systemctl status postgresql"
            echo
            echo_info "Start service:"
            echo_info "  sudo systemctl start postgresql"
            exit 1
            ;;
    esac

    # Recent logs
    echo_info "Recent Logs (last 10 lines):"
    sudo journalctl -u postgresql -n 10 --no-pager 2> /dev/null | sed 's/^/  /'

    echo -e "\nLogs: $LOG_PATH (stdout) | $ERR_PATH (stderr)"
}

main "$@" > >(tee -a "$LOG_PATH") 2> >(tee -a "$ERR_PATH" >&2)

# EOF
