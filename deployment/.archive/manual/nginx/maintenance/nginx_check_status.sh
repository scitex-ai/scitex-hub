#!/bin/bash
# -*- coding: utf-8 -*-
# Check Nginx server status
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
    if [ -f /etc/nginx/sites-enabled/scitex_cloud_prod.conf ]; then
        echo "production"
    elif [ -f /etc/nginx/sites-enabled/scitex_cloud_dev.conf ]; then
        echo "development"
    elif systemctl is-active --quiet nginx 2> /dev/null; then
        echo "running"
    else
        echo "unknown"
    fi
}

# Check general Nginx status
check_general_status() {
    echo_header "=== Nginx Status ==="
    echo

    # Service status
    echo_info "Service Status:"
    if systemctl is-active --quiet nginx; then
        echo_success "  ✓ Service active"

        # Service details
        UPTIME=$(systemctl show nginx --property=ActiveEnterTimestamp --value)
        echo_info "  Active since: $UPTIME"

        # Nginx version
        NGINX_VERSION=$(nginx -v 2>&1 | grep -o "[0-9]\+\.[0-9]\+\.[0-9]\+")
        echo_info "  Version: $NGINX_VERSION"
    else
        echo_error "  ✗ Service not active"

        if systemctl is-enabled --quiet nginx 2> /dev/null; then
            echo_warning "  ⚠ Service enabled but not running"
            echo_info "  Start with: sudo systemctl start nginx"
        else
            echo_error "  ✗ Service not enabled"
            echo_info "  Enable with: sudo systemctl enable nginx"
        fi
        return 1
    fi
    echo

    # Configuration test
    echo_info "Configuration Test:"
    if sudo nginx -t 2>&1 | grep -q "test is successful"; then
        echo_success "  ✓ Configuration valid"
    else
        echo_error "  ✗ Configuration has errors"
        sudo nginx -t 2>&1 | sed 's/^/    /'
    fi
    echo

    # Process info
    echo_info "Process Info:"
    ps aux | grep "[n]ginx" | sed 's/^/  /'
    echo
}

# Check development configuration
check_development() {
    echo_header "=== Development Configuration ==="
    echo

    # Configuration file
    echo_info "Configuration File:"
    if [ -f /etc/nginx/sites-available/scitex_cloud_dev.conf ]; then
        echo_success "  ✓ Config exists: /etc/nginx/sites-available/scitex_cloud_dev.conf"

        # Check if enabled
        if [ -L /etc/nginx/sites-enabled/scitex_cloud_dev.conf ]; then
            echo_success "  ✓ Config enabled"
        else
            echo_warning "  ⚠ Config not enabled"
            echo_info "  Enable with: sudo ln -s /etc/nginx/sites-available/scitex_cloud_dev.conf /etc/nginx/sites-enabled/"
        fi
    else
        echo_error "  ✗ Config not found"
    fi
    echo

    # Server block details
    if [ -f /etc/nginx/sites-available/scitex_cloud_dev.conf ]; then
        echo_info "Server Block Details:"

        # Extract server name
        SERVER_NAME=$(grep "server_name" /etc/nginx/sites-available/scitex_cloud_dev.conf | head -1 | awk '{print $2}' | tr -d ';')
        echo_info "  Server name: $SERVER_NAME"

        # Extract listen port
        LISTEN_PORT=$(grep "listen" /etc/nginx/sites-available/scitex_cloud_dev.conf | grep -v "443" | head -1 | awk '{print $2}' | tr -d ';')
        echo_info "  Listen port: $LISTEN_PORT"

        # Extract upstream
        UPSTREAM=$(grep "proxy_pass" /etc/nginx/sites-available/scitex_cloud_dev.conf | head -1 | awk '{print $2}' | tr -d ';')
        echo_info "  Upstream: $UPSTREAM"
    fi
    echo

    # Test HTTP connectivity
    echo_info "HTTP Connectivity:"
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ 2> /dev/null | grep -q "200\|301\|302"; then
        echo_success "  ✓ HTTP accessible at http://localhost:8000"
    else
        echo_error "  ✗ HTTP not accessible"
    fi
    echo
}

# Check production configuration
check_production() {
    echo_header "=== Production Configuration ==="
    echo

    # Configuration file
    echo_info "Configuration File:"
    if [ -f /etc/nginx/sites-available/scitex_cloud_prod.conf ]; then
        echo_success "  ✓ Config exists: /etc/nginx/sites-available/scitex_cloud_prod.conf"

        # Check if enabled
        if [ -L /etc/nginx/sites-enabled/scitex_cloud_prod.conf ]; then
            echo_success "  ✓ Config enabled"
        else
            echo_warning "  ⚠ Config not enabled"
            echo_info "  Enable with: sudo ln -s /etc/nginx/sites-available/scitex_cloud_prod.conf /etc/nginx/sites-enabled/"
        fi
    else
        echo_error "  ✗ Config not found"
    fi
    echo

    # Server block details
    if [ -f /etc/nginx/sites-available/scitex_cloud_prod.conf ]; then
        echo_info "Server Block Details:"

        # Extract server names
        SERVER_NAMES=$(grep "server_name" /etc/nginx/sites-available/scitex_cloud_prod.conf | grep -v "#" | awk '{for(i=2;i<=NF;i++) printf "%s ", $i}')
        echo_info "  Server names: $SERVER_NAMES"

        # Extract listen ports
        echo_info "  Listen ports:"
        grep "listen" /etc/nginx/sites-available/scitex_cloud_prod.conf | grep -v "#" | sed 's/^/    /'

        # Extract upstream
        UPSTREAM=$(grep "proxy_pass" /etc/nginx/sites-available/scitex_cloud_prod.conf | head -1 | awk '{print $2}' | tr -d ';')
        echo_info "  Upstream: $UPSTREAM"
    fi
    echo

    # SSL certificate check
    echo_info "SSL Certificates:"
    if [ -f /etc/letsencrypt/live/scitex.ai/fullchain.pem ]; then
        EXPIRY=$(openssl x509 -enddate -noout -in /etc/letsencrypt/live/scitex.ai/fullchain.pem 2> /dev/null | cut -d= -f2)
        echo_success "  ✓ Certificate exists for scitex.ai"
        echo_info "  Expires: $EXPIRY"
    else
        echo_warning "  ⚠ Certificate not found for scitex.ai"
    fi

    if [ -f /etc/letsencrypt/live/git.scitex.ai/fullchain.pem ]; then
        EXPIRY=$(openssl x509 -enddate -noout -in /etc/letsencrypt/live/git.scitex.ai/fullchain.pem 2> /dev/null | cut -d= -f2)
        echo_success "  ✓ Certificate exists for git.scitex.ai"
        echo_info "  Expires: $EXPIRY"
    else
        echo_warning "  ⚠ Certificate not found for git.scitex.ai"
    fi
    echo

    # Test HTTPS connectivity
    echo_info "HTTPS Connectivity:"
    if curl -s -o /dev/null -w "%{http_code}" https://scitex.ai/ 2> /dev/null | grep -q "200\|301\|302"; then
        echo_success "  ✓ HTTPS accessible at https://scitex.ai"
    else
        echo_error "  ✗ HTTPS not accessible"
    fi
    echo
}

# Show enabled sites
show_enabled_sites() {
    echo_info "Enabled Sites:"
    if [ -d /etc/nginx/sites-enabled ]; then
        ls -la /etc/nginx/sites-enabled/ | grep -v "^total" | grep -v "^d" | sed 's/^/  /'
    else
        echo_warning "  No sites-enabled directory found"
    fi
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
            show_enabled_sites
            ;;
        unknown)
            echo_warning "=== Nginx Status ==="
            echo_error "✗ Nginx not running"
            echo
            echo_info "Check service status:"
            echo_info "  sudo systemctl status nginx"
            echo
            echo_info "Start service:"
            echo_info "  sudo systemctl start nginx"
            exit 1
            ;;
    esac

    # Recent logs
    echo_info "Recent Error Logs (last 10 lines):"
    sudo tail -n 10 /var/log/nginx/error.log 2> /dev/null | sed 's/^/  /' || echo_info "  No error log available"
    echo

    echo_info "Recent Access Logs (last 5 lines):"
    sudo tail -n 5 /var/log/nginx/access.log 2> /dev/null | sed 's/^/  /' || echo_info "  No access log available"

    echo -e "\nLogs: $LOG_PATH (stdout) | $ERR_PATH (stderr)"
}

main "$@" > >(tee -a "$LOG_PATH") 2> >(tee -a "$ERR_PATH" >&2)

# EOF
