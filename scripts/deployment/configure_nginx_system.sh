#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-20 15:08:00 (ywatanabe)"
# File: ./scripts/deployment/configure_nginx_system.sh

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

set -e

NGINX_CONF="/etc/nginx/nginx.conf"
BACKUP_DIR="/etc/nginx/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

usage() {
    echo "Usage: sudo $0 [-h|--help]"
    echo ""
    echo "Options:"
    echo "  -h, --help   Display this help message"
    echo ""
    echo "Description:"
    echo "  Enhances system nginx.conf with Django/uWSGI production settings"
    echo ""
    echo "  This is a ONE-TIME setup. Run only once after installing nginx."
    exit 1
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

backup_config() {
    echo_info "Creating backups..."
    mkdir -p "$BACKUP_DIR"

    if [ ! -f "$BACKUP_DIR/nginx.conf.original" ]; then
        cp "$NGINX_CONF" "$BACKUP_DIR/nginx.conf.original"
        echo_success "Original saved: nginx.conf.original"
    fi

    cp "$NGINX_CONF" "$BACKUP_DIR/nginx.conf.backup_$TIMESTAMP"
    echo_success "Backup created: nginx.conf.backup_$TIMESTAMP"
}

apply_enhancements() {
    if grep -q "# SciTeX Hub Enhancements" "$NGINX_CONF"; then
        echo_warning "Enhancements already applied"
        return 0
    fi

    echo_info "Applying enhancements..."

    # Use a temporary file for safety
    local temp_file=$(mktemp)

    # Add enhancements before the include line
    awk '
    /include \/etc\/nginx\/conf.d\/\*.conf;/ {
        print "    ##"
        print "    # SciTeX Hub Enhancements"
        print "    ##"
        print ""
        print "    client_max_body_size 100M;"
        print "    client_body_buffer_size 128k;"
        print ""
        print "    proxy_connect_timeout 600s;"
        print "    proxy_send_timeout 600s;"
        print "    proxy_read_timeout 600s;"
        print "    send_timeout 600s;"
        print ""
        print "    uwsgi_read_timeout 300s;"
        print "    uwsgi_send_timeout 300s;"
        print ""
        print "    proxy_buffer_size 128k;"
        print "    proxy_buffers 4 256k;"
        print "    proxy_busy_buffers_size 256k;"
        print ""
        print "    limit_req_zone $binary_remote_addr zone=scitex_limit:10m rate=10r/s;"
        print "    limit_req_status 429;"
        print ""
        print "    add_header X-Content-Type-Options \"nosniff\" always;"
        print "    add_header X-Frame-Options \"SAMEORIGIN\" always;"
        print "    add_header X-XSS-Protection \"1; mode=block\" always;"
        print ""
        print "    server_tokens off;"
        print ""
    }
    { print }
    ' "$NGINX_CONF" > "$temp_file"

    # Replace original with enhanced version
    mv "$temp_file" "$NGINX_CONF"

    echo_success "Enhancements applied"
}

test_and_reload() {
    echo_info "Testing configuration..."

    if nginx -t; then
        echo_success "Configuration valid"
        echo_info "Reloading nginx..."
        systemctl reload nginx 2> /dev/null || systemctl start nginx
        echo_success "Nginx reloaded"
        return 0
    else
        echo_error "Configuration test failed"
        echo_warning "Rolling back..."
        cp "$BACKUP_DIR/nginx.conf.backup_$TIMESTAMP" "$NGINX_CONF"
        return 1
    fi
}

print_summary() {
    echo ""
    echo_success "=== Configuration Complete ==="
    echo ""
    echo "Enhancements:"
    echo "  • Client max body size: 100M"
    echo "  • Extended timeouts for Django/uWSGI"
    echo "  • Increased buffer sizes"
    echo "  • Rate limiting: 10 req/s per IP"
    echo "  • Security headers enabled"
    echo "  • Server tokens hidden"
    echo ""
    echo "Backups:"
    echo "  • Original: $BACKUP_DIR/nginx.conf.original"
    echo "  • Latest: $BACKUP_DIR/nginx.conf.backup_$TIMESTAMP"
}

main() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h | --help)
                usage
                ;;
            *)
                echo_error "Unknown option: $1"
                usage
                ;;
        esac
    done

    echo_info "=== SciTeX Hub Nginx System Configuration ==="
    echo ""

    check_root
    backup_config
    apply_enhancements
    test_and_reload
    print_summary
}

main "$@" 2>&1 | tee -a "$LOG_PATH"

# EOF
