#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-20 15:40:00 (ywatanabe)"
# File: ./deployment/uwsgi/setup_uwsgi.sh

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

PROJECT_ROOT="$(cd "$THIS_DIR/../.." && pwd)"
LOG_FILE=".$(basename $0).log"

usage() {
    echo "Usage: sudo $0 [-e|--env ENV] [-h|--help]"
    echo ""
    echo "Options:"
    echo "  -e, --env    Environment: dev or prod (required)"
    echo "  -h, --help   Display this help message"
    echo ""
    echo "Example:"
    echo "  sudo $0 -e dev"
    echo "  sudo $0 -e prod"
    exit 1
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

install_uwsgi() {
    local venv_path="$PROJECT_ROOT/.venv"

    echo_info "Installing uWSGI..."

    if [ ! -d "$venv_path" ]; then
        echo_error "Virtual environment not found at $venv_path"
        exit 1
    fi

    sudo -u ywatanabe "$venv_path/bin/pip" install uwsgi
    echo_success "uWSGI installed"
}

create_directories() {
    local env="$1"

    echo_info "Creating directories..."
    mkdir -p /var/log/uwsgi
    chown www-data:www-data /var/log/uwsgi

    if [ "$env" = "dev" ]; then
        mkdir -p /run
        chown www-data:www-data /run 2> /dev/null || true
    else
        mkdir -p /run/scitex_cloud
        chown www-data:www-data /run/scitex_cloud
    fi

    echo_success "Directories created"
}

setup_systemd_service() {
    local env="$1"

    echo_info "Creating systemd service..."

    if [ "$env" = "dev" ]; then
        local ini_file="$PROJECT_ROOT/deployment/uwsgi/uwsgi_dev.ini"
        local service_file="$PROJECT_ROOT/deployment/uwsgi/uwsgi_dev.service"
        local service_name="uwsgi_dev"
    else
        local ini_file="$PROJECT_ROOT/deployment/uwsgi/uwsgi_prod.ini"
        local service_file="$PROJECT_ROOT/deployment/uwsgi/uwsgi_prod.service"
        local service_name="uwsgi_prod"
    fi

    mkdir -p /etc/uwsgi
    cp "$ini_file" /etc/uwsgi/
    cp "$service_file" /etc/systemd/system/${service_name}.service

    systemctl daemon-reload
    echo_success "Service created: ${service_name}"
}

enable_and_start_service() {
    local env="$1"
    local service_name="uwsgi_prod"

    if [ "$env" = "dev" ]; then
        service_name="uwsgi_dev"
    fi

    echo_info "Enabling and starting service..."
    systemctl enable ${service_name}
    systemctl restart ${service_name}
    echo_success "Service enabled and started: ${service_name}"
}

verify_setup() {
    local env="$1"
    local service_name="uwsgi_prod"

    if [ "$env" = "dev" ]; then
        service_name="uwsgi_dev"
    fi

    echo ""
    echo_info "Verifying setup..."
    echo ""
    systemctl status ${service_name} --no-pager || true
}

print_summary() {
    local env="$1"
    local service_name="uwsgi_prod"
    local socket_path="/run/scitex_cloud.sock"
    local log_path="/var/log/uwsgi/scitex_cloud.log"

    if [ "$env" = "dev" ]; then
        service_name="uwsgi_dev"
        socket_path="/run/scitex_cloud_dev.sock"
        log_path="/var/log/uwsgi/scitex_cloud_dev.log"
    fi

    echo ""
    echo_success "=== uWSGI ${env} Setup Complete ==="
    echo ""
    echo "Service: ${service_name}"
    echo "Socket: ${socket_path}"
    echo "Logs: ${log_path}"

    if [ "$env" = "dev" ]; then
        echo ""
        echo "Auto-reload: Enabled (checks every 2 seconds)"
        echo "Touch to reload: touch /tmp/reload-scitex-dev"
    fi

    echo ""
    echo "Commands:"
    echo "  sudo systemctl status ${service_name}"
    echo "  sudo systemctl restart ${service_name}"
    echo "  sudo systemctl stop ${service_name}"
    echo "  sudo journalctl -u ${service_name} -f"
}

main() {
    ENV=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            -e | --env)
                ENV="$2"
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

    if [ -z "$ENV" ]; then
        echo_error "Environment (-e|--env) is required"
        usage
    fi

    if [ "$ENV" != "dev" ] && [ "$ENV" != "prod" ]; then
        echo_error "Environment must be 'dev' or 'prod'"
        exit 1
    fi

    echo_info "=== SciTeX Cloud uWSGI Setup (${ENV}) ==="
    echo ""

    check_root
    install_uwsgi
    create_directories "$ENV"
    setup_systemd_service "$ENV"
    enable_and_start_service "$ENV"
    verify_setup "$ENV"
    print_summary "$ENV"
}

main "$@" 2>&1 | tee -a "$LOG_FILE"

# EOF
