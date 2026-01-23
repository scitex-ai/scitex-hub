#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-20 18:30:00 (ywatanabe)"
# File: ./deployment/gitea/maintenance/gitea_check_status.sh

ORIG_DIR="$(pwd)"
THIS_DIR="$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)"
LOG_PATH="$THIS_DIR/.$(basename $0).log"
echo > "$LOG_PATH"

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
echo_blue() { echo -e "${BLUE}$1${NC}"; }

usage() {
    echo "Usage: $0 [-e|--env ENV] [-h|--help]"
    echo ""
    echo "Options:"
    echo "  -e, --env    Environment: dev or prod (required)"
    echo "  -h, --help   Display this help message"
    echo ""
    echo "Example:"
    echo "  $0 -e dev"
    echo "  $0 --env prod"
    exit 1
}

parse_args() {
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
        usage
    fi
}

set_environment_variables() {
    if [ "$ENV" = "dev" ]; then
        GITEA_DB_NAME="gitea_dev"
        GITEA_DB_USER="gitea_dev"
        DOMAIN="localhost"
        HTTP_PORT="3001"
        SSH_PORT="2223"
        ROOT_URL="http://localhost:${HTTP_PORT}/"
        SERVICE_NAME="gitea_dev"
        CONFIG_FILE="/etc/gitea/app_dev.ini"
    else
        GITEA_DB_NAME="gitea_prod"
        GITEA_DB_USER="gitea_prod"
        DOMAIN="git.scitex.ai"
        HTTP_PORT="3000"
        SSH_PORT="2222"
        ROOT_URL="https://${DOMAIN}/"
        SERVICE_NAME="gitea_prod"
        CONFIG_FILE="/etc/gitea/app_prod.ini"
    fi
}

check_service_status() {
    echo_blue "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo_blue "  Gitea Service Status Check (${ENV})"
    echo_blue "  Domain: ${DOMAIN}"
    echo_blue "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # 1. Check systemd service
    echo_info "1. Systemd Service Status:"
    if systemctl is-active --quiet ${SERVICE_NAME} 2> /dev/null; then
        echo_success "   ✓ ${SERVICE_NAME} is running"
        systemctl status ${SERVICE_NAME} --no-pager -l 2> /dev/null | head -10 | sed 's/^/   /'
    else
        echo_error "   ✗ ${SERVICE_NAME} is NOT running"
        echo_warning "   Run: sudo systemctl start ${SERVICE_NAME}"
        return 1
    fi
    echo ""

    # 2. Check process
    echo_info "2. Process Information:"
    if pgrep -f "gitea web.*${ENV}" > /dev/null 2>&1; then
        ps aux | grep "[g]itea web.*${CONFIG_FILE}" | sed 's/^/   /'
        echo_success "   ✓ Gitea process is running"
    else
        echo_warning "   ⚠ Gitea process not found with config filter"
        ps aux | grep "[g]itea web" | sed 's/^/   /'
    fi
    echo ""

    # 3. Check ports
    echo_info "3. Network Ports:"

    # HTTP port
    if ss -tlnp 2> /dev/null | grep -q ":${HTTP_PORT}" || netstat -tlnp 2> /dev/null | grep -q ":${HTTP_PORT}"; then
        echo_success "   ✓ HTTP port ${HTTP_PORT} is listening"
        (ss -tlnp 2> /dev/null || netstat -tlnp 2> /dev/null) | grep ":${HTTP_PORT}" | sed 's/^/   /'
    else
        echo_error "   ✗ HTTP port ${HTTP_PORT} is NOT listening"
    fi

    # SSH port
    if ss -tlnp 2> /dev/null | grep -q ":${SSH_PORT}" || netstat -tlnp 2> /dev/null | grep -q ":${SSH_PORT}"; then
        echo_success "   ✓ SSH port ${SSH_PORT} is listening"
        (ss -tlnp 2> /dev/null || netstat -tlnp 2> /dev/null) | grep ":${SSH_PORT}" | sed 's/^/   /'
    else
        echo_error "   ✗ SSH port ${SSH_PORT} is NOT listening"
    fi
    echo ""

    # 4. Test HTTP endpoint
    echo_info "4. HTTP Endpoint Test:"
    HTTP_CODE=$(curl -f -s -o /dev/null -w "%{http_code}" http://${DOMAIN}:${HTTP_PORT} 2> /dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        echo_success "   ✓ HTTP endpoint is responding (http://${DOMAIN}:${HTTP_PORT})"
        echo_info "     HTTP Status: $HTTP_CODE"
    else
        echo_warning "   ⚠ HTTP endpoint returned code: $HTTP_CODE"
    fi
    echo ""

    # 5. Test SSH endpoint
    echo_info "5. SSH Endpoint Test:"
    if timeout 2 bash -c "echo > /dev/tcp/${DOMAIN}/${SSH_PORT}" 2> /dev/null; then
        echo_success "   ✓ SSH port is accessible (${DOMAIN}:${SSH_PORT})"
    else
        echo_warning "   ⚠ SSH port connection test failed"
    fi
    echo ""

    # 6. Configuration file
    echo_info "6. Configuration:"
    if [ -f "$CONFIG_FILE" ]; then
        echo_success "   ✓ Config file exists: $CONFIG_FILE"
        echo_info "   Key settings:"
        sudo grep -E "^(APP_NAME|HTTP_PORT|HTTP_ADDR|SSH_PORT|ROOT_URL|DOMAIN)" "$CONFIG_FILE" 2> /dev/null | sed 's/^/     /' || echo "     (Could not read config)"
    else
        echo_error "   ✗ Config file not found: $CONFIG_FILE"
    fi
    echo ""

    # 7. Database connection
    echo_info "7. Database Connection:"
    if sudo -u postgres psql -lqt 2> /dev/null | cut -d \| -f 1 | grep -qw "$GITEA_DB_NAME"; then
        echo_success "   ✓ Database exists: $GITEA_DB_NAME"

        # Count repositories and users
        REPO_COUNT=$(sudo -u postgres psql -d "$GITEA_DB_NAME" -tAc "SELECT COUNT(*) FROM repository;" 2> /dev/null || echo "0")
        USER_COUNT=$(sudo -u postgres psql -d "$GITEA_DB_NAME" -tAc "SELECT COUNT(*) FROM \"user\";" 2> /dev/null || echo "0")

        echo_info "   Statistics:"
        echo_info "     Users: $USER_COUNT"
        echo_info "     Repositories: $REPO_COUNT"
    else
        echo_error "   ✗ Database not found: $GITEA_DB_NAME"
    fi
    echo ""

    # 8. Disk usage
    echo_info "8. Disk Usage:"
    if [ -d "/var/lib/gitea/data" ]; then
        DISK_USAGE=$(sudo du -sh /var/lib/gitea/data 2> /dev/null | awk '{print $1}' || echo "N/A")
        echo_info "   Data directory: $DISK_USAGE"

        if [ -d "/var/lib/gitea/data/gitea-repositories" ]; then
            REPO_USAGE=$(sudo du -sh /var/lib/gitea/data/gitea-repositories 2> /dev/null | awk '{print $1}' || echo "N/A")
            echo_info "   Repositories: $REPO_USAGE"
        fi
    fi
    echo ""

    # 9. Recent logs
    echo_info "9. Recent Log Entries (last 5):"
    if sudo journalctl -u ${SERVICE_NAME} -n 5 --no-pager 2> /dev/null | grep -q .; then
        sudo journalctl -u ${SERVICE_NAME} -n 5 --no-pager 2> /dev/null | sed 's/^/   /'
    else
        echo_warning "   ⚠ Could not retrieve logs (may need sudo)"
    fi
    echo ""
}

print_summary() {
    echo_blue "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo_blue "  Access Information (${ENV})"
    echo_blue "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo_info "Web Interface:"
    if [ "$ENV" = "dev" ]; then
        echo "  http://localhost:${HTTP_PORT}"
        echo "  http://127.0.0.1:${HTTP_PORT}"
        WSL_IP=$(hostname -I 2> /dev/null | awk '{print $1}')
        if [ -n "$WSL_IP" ]; then
            echo "  http://${WSL_IP}:${HTTP_PORT} (from Windows)"
        fi
    else
        echo "  http://${DOMAIN}"
        echo "  https://${DOMAIN}"
    fi
    echo ""
    echo_info "Git Clone (SSH):"
    echo "  git clone ssh://git@${DOMAIN}:${SSH_PORT}/username/repo.git"
    echo ""
    echo_info "Git Clone (HTTP):"
    if [ "$ENV" = "dev" ]; then
        echo "  git clone http://localhost:${HTTP_PORT}/username/repo.git"
    else
        echo "  git clone http://${DOMAIN}/username/repo.git"
        echo "  git clone https://${DOMAIN}/username/repo.git"
    fi
    echo ""
    echo_info "Useful Commands:"
    echo "  sudo systemctl status ${SERVICE_NAME}"
    echo "  sudo systemctl restart ${SERVICE_NAME}"
    echo "  sudo journalctl -u ${SERVICE_NAME} -f"
    echo "  sudo -u postgres psql -d ${GITEA_DB_NAME}"
    echo ""
    echo_blue "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

main() {
    parse_args "$@"
    set_environment_variables

    echo_info "=== Gitea Status Check (${ENV}) ==="
    echo ""

    check_service_status
    print_summary
}

main "$@" 2>&1 | tee -a "$LOG_PATH"

# EOF
