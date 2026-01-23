#!/bin/bash
# -*- coding: utf-8 -*-
# Check uWSGI server status
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
    if systemctl is-active --quiet scitex_cloud_prod 2> /dev/null; then
        echo "production"
    elif systemctl is-active --quiet scitex_cloud_dev 2> /dev/null; then
        echo "development"
    elif [ -S /tmp/scitex_cloud_dev.sock ] || [ -S /tmp/scitex_cloud_prod.sock ]; then
        echo "socket"
    else
        echo "unknown"
    fi
}

# Check development
check_development() {
    echo_header "=== uWSGI Development Status ==="
    echo

    # Service status
    echo_info "Service Status:"
    if systemctl is-active --quiet scitex_cloud_dev 2> /dev/null; then
        echo_success "  ✓ Service active"

        # Service details
        UPTIME=$(systemctl show scitex_cloud_dev --property=ActiveEnterTimestamp --value)
        echo_info "  Active since: $UPTIME"
    else
        echo_error "  ✗ Service not active"

        if systemctl is-enabled --quiet scitex_cloud_dev 2> /dev/null; then
            echo_warning "  ⚠ Service enabled but not running"
            echo_info "  Start with: sudo systemctl start scitex_cloud_dev"
        else
            echo_error "  ✗ Service not enabled"
            echo_info "  Enable with: sudo systemctl enable scitex_cloud_dev"
        fi
        return 1
    fi
    echo

    # Process info
    echo_info "Process Info:"
    systemctl show scitex_cloud_dev --property=MainPID --value | xargs -I {} ps -p {} -o pid,user,%cpu,%mem,vsz,rss,tty,stat,start,time,comm 2> /dev/null | sed 's/^/  /'
    echo

    # Socket check
    echo_info "Socket Status:"
    if [ -S /tmp/scitex_cloud_dev.sock ]; then
        echo_success "  ✓ Socket exists: /tmp/scitex_cloud_dev.sock"

        # Socket permissions
        ls -la /tmp/scitex_cloud_dev.sock | sed 's/^/  /'
    else
        echo_error "  ✗ Socket not found"
    fi
    echo

    # Configuration file
    echo_info "Configuration:"
    if [ -f /home/ywatanabe/proj/scitex-cloud/deployment/uwsgi/scitex_cloud_dev.ini ]; then
        echo_success "  ✓ Config file exists"
        echo_info "  Path: deployment/uwsgi/scitex_cloud_dev.ini"
    else
        echo_error "  ✗ Config file not found"
    fi
    echo

    # Recent logs
    echo_info "Recent Logs (last 10 lines):"
    sudo journalctl -u scitex_cloud_dev -n 10 --no-pager 2> /dev/null | sed 's/^/  /'
}

# Check production
check_production() {
    echo_header "=== uWSGI Production Status ==="
    echo

    # Service status
    echo_info "Service Status:"
    if systemctl is-active --quiet scitex_cloud_prod; then
        echo_success "  ✓ Service active"

        # Service details
        UPTIME=$(systemctl show scitex_cloud_prod --property=ActiveEnterTimestamp --value)
        echo_info "  Active since: $UPTIME"
    else
        echo_error "  ✗ Service not active"

        if systemctl is-enabled --quiet scitex_cloud_prod 2> /dev/null; then
            echo_warning "  ⚠ Service enabled but not running"
            echo_info "  Start with: sudo systemctl start scitex_cloud_prod"
        else
            echo_error "  ✗ Service not enabled"
            echo_info "  Enable with: sudo systemctl enable scitex_cloud_prod"
        fi
        return 1
    fi
    echo

    # Process info
    echo_info "Process Info:"
    systemctl show scitex_cloud_prod --property=MainPID --value | xargs -I {} ps -p {} -o pid,user,%cpu,%mem,vsz,rss,tty,stat,start,time,comm 2> /dev/null | sed 's/^/  /'

    # Show all uWSGI workers
    echo_info "  Workers:"
    ps aux | grep "[u]wsgi.*scitex_cloud_prod" | sed 's/^/    /'
    echo

    # Socket check
    echo_info "Socket Status:"
    if [ -S /tmp/scitex_cloud_prod.sock ]; then
        echo_success "  ✓ Socket exists: /tmp/scitex_cloud_prod.sock"

        # Socket permissions
        ls -la /tmp/scitex_cloud_prod.sock | sed 's/^/  /'
    else
        echo_error "  ✗ Socket not found"
    fi
    echo

    # Configuration file
    echo_info "Configuration:"
    if [ -f /home/ywatanabe/proj/scitex-cloud/deployment/uwsgi/scitex_cloud_prod.ini ]; then
        echo_success "  ✓ Config file exists"
        echo_info "  Path: deployment/uwsgi/scitex_cloud_prod.ini"

        # Show key configuration
        echo_info "  Workers: $(grep "^processes" /home/ywatanabe/proj/scitex-cloud/deployment/uwsgi/scitex_cloud_prod.ini 2> /dev/null | cut -d'=' -f2 | tr -d ' ')"
        echo_info "  Threads: $(grep "^threads" /home/ywatanabe/proj/scitex-cloud/deployment/uwsgi/scitex_cloud_prod.ini 2> /dev/null | cut -d'=' -f2 | tr -d ' ')"
    else
        echo_error "  ✗ Config file not found"
    fi
    echo

    # Recent logs
    echo_info "Recent Logs (last 10 lines):"
    sudo journalctl -u scitex_cloud_prod -n 10 --no-pager 2> /dev/null | sed 's/^/  /'
}

# Main
main() {
    ENV=$(detect_environment)

    case $ENV in
        development)
            check_development
            ;;
        production)
            check_production
            ;;
        socket)
            echo_warning "=== uWSGI Status ==="
            echo_info "Socket found but service not detected via systemctl"
            echo_info "Check manually: ps aux | grep uwsgi"
            ;;
        unknown)
            echo_warning "=== uWSGI Status ==="
            echo_error "✗ uWSGI not detected"
            echo
            echo_info "Development:"
            echo_info "  Check: sudo systemctl status scitex_cloud_dev"
            echo_info "  Start: sudo systemctl start scitex_cloud_dev"
            echo
            echo_info "Production:"
            echo_info "  Check: sudo systemctl status scitex_cloud_prod"
            echo_info "  Start: sudo systemctl start scitex_cloud_prod"
            echo
            echo -e "Logs: $LOG_PATH (stdout) | $ERR_PATH (stderr)"
            exit 1
            ;;
    esac

    echo -e "\nLogs: $LOG_PATH (stdout) | $ERR_PATH (stderr)"
}

main "$@" > >(tee -a "$LOG_PATH") 2> >(tee -a "$ERR_PATH" >&2)

# EOF
