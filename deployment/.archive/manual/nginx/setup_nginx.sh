#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-20 15:37:24 (ywatanabe)"
# File: ./deployment/nginx/setup_nginx.sh

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

usage() {
    echo "Usage: sudo $0 [-e|--environment <dev|prod>] [-h|--help]"
    echo ""
    echo "Options:"
    echo "  -e, --environment  Deployment environment (dev or prod) (default: prod)"
    echo "  -h, --help         Display this help message"
    echo ""
    echo "Example:"
    echo "  sudo $0 -e prod"
    echo "  sudo $0 --environment dev"
    exit 1
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

setup_nginx() {
    local env="$1"

    echo_info "Setting up Nginx configuration for environment: $env"

    echo_info "Removing existing scitex configurations..."
    rm -f /etc/nginx/sites-available/scitex* /etc/nginx/sites-enabled/scitex*

    local system_src="$THIS_DIR/nginx.conf"
    local system_tgt="/etc/nginx/nginx.conf"
    local site_src="$THIS_DIR/scitex_cloud_${env}.conf"
    local site_available="/etc/nginx/sites-available/scitex_cloud.conf"
    local site_enabled="/etc/nginx/sites-enabled/scitex_cloud.conf"

    if [ ! -f "$site_src" ]; then
        echo_error "Config file not found: $site_src"
        exit 1
    fi

    echo_info "Symlinking Nginx system configuration..."
    ln -sf "$system_src" "$system_tgt"

    echo_info "Symlinking Nginx site configuration..."
    ln -sf "$site_src" "$site_available"

    echo_info "Enabling the site..."
    ln -sf "$site_available" "$site_enabled"

    echo_info "Checking files..."
    ls -al "$system_tgt"
    ls -al "$site_available"
    ls -al "$site_enabled"

    echo_info "Showing configurations..."
    echo "=== System nginx.conf ==="
    cat "$system_tgt"
    echo ""
    echo "=== Site configuration ==="
    cat "$site_available"

    echo_info "Testing Nginx configuration..."
    if nginx -t; then
        echo_success "Nginx configuration test passed"
    else
        echo_error "Nginx configuration test failed"
        return 1
    fi

    echo_info "Enabling Nginx to start on boot..."
    systemctl enable nginx

    if systemctl is-active --quiet nginx; then
        echo_info "Reloading Nginx..."
        systemctl reload nginx
    else
        echo_info "Starting Nginx..."
        systemctl start nginx
    fi

    echo_success "Nginx setup completed successfully for environment: $env"
    return 0
}

main() {
    ENVIRONMENT="prod"

    while [[ $# -gt 0 ]]; do
        case $1 in
            -e | --environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -h | --help)
                usage
                ;;
            *)
                echo_error "Unknown option: $1"
                usage
                ;;
        esac
    done

    if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "prod" ]]; then
        echo_error "Environment must be either 'dev' or 'prod', got: $ENVIRONMENT"
        exit 1
    fi

    echo_info "=== SciTeX Cloud Nginx Setup ==="
    echo ""

    check_root
    setup_nginx "$ENVIRONMENT"
}

main "$@" 2>&1 | tee -a "$LOG_PATH"

# EOF
