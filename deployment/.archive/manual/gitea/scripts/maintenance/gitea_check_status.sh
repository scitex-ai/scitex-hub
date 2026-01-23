#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-20 11:41:00 (ywatanabe)"
# File: ./scripts/deployment/maintenance/gitea_check_status.sh

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

# Check Gitea server status
# Works for both development (Docker) and production (systemd)

set -euo pipefail

BLUE='\033[0;34m'

echo_header() { echo -e "${BLUE}$1${NC}"; }

# Detect environment
detect_environment() {
    if docker ps 2> /dev/null | grep -q scitex-gitea-dev; then
        echo "development"
    elif systemctl is-active --quiet gitea 2> /dev/null; then
        echo "production"
    else
        echo "unknown"
    fi
}

# Check development (Docker)
check_development() {
    echo_header "=== Gitea Development Status (Docker) ==="
    echo

    # Container status
    echo_info "Container Status:"
    if docker ps | grep -q scitex-gitea-dev; then
        echo_success "  ✓ Container running"

        # Container details
        CONTAINER_ID=$(docker ps --filter name=scitex-gitea-dev --format "{{.ID}}")
        UPTIME=$(docker ps --filter name=scitex-gitea-dev --format "{{.Status}}")
        echo_info "  Container ID: $CONTAINER_ID"
        echo_info "  Uptime: $UPTIME"
    else
        echo_error "  ✗ Container not running"

        # Check if container exists but is stopped
        if docker ps -a | grep -q scitex-gitea-dev; then
            echo_warning "  ⚠ Container exists but is stopped"
            echo_info "  Start with: docker start scitex-gitea-dev"
        else
            echo_error "  ✗ Container does not exist"
            echo_info "  Create with: ./deployment/gitea/scripts/start-dev.sh"
        fi
        return 1
    fi
    echo

    # Port bindings
    echo_info "Port Bindings:"
    docker port scitex-gitea-dev 2> /dev/null | while read line; do
        echo_info "  $line"
    done
    echo

    # API connectivity
    echo_info "API Connectivity:"
    if curl -s http://localhost:3000/api/v1/version > /dev/null 2>&1; then
        VERSION=$(curl -s http://localhost:3000/api/v1/version | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
        echo_success "  ✓ API accessible"
        echo_info "  Version: $VERSION"
    else
        echo_error "  ✗ API not accessible"
    fi
    echo

    # Web UI
    echo_info "Web Interface:"
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/ | grep -q "200"; then
        echo_success "  ✓ Web UI accessible at http://localhost:3000"
    else
        echo_error "  ✗ Web UI not accessible"
    fi
    echo

    # Resource usage
    echo_info "Resource Usage:"
    docker stats scitex-gitea-dev --no-stream --format "table {{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}" 2> /dev/null
    echo

    # Volume
    echo_info "Data Volume:"
    if docker volume inspect gitea-data > /dev/null 2>&1; then
        VOLUME_SIZE=$(docker system df -v 2> /dev/null | grep gitea-data | awk '{print $3}')
        echo_success "  ✓ Volume exists"
        echo_info "  Size: $VOLUME_SIZE"
    else
        echo_warning "  ⚠ Volume not found"
    fi
    echo

    # Recent logs
    echo_info "Recent Logs (last 10 lines):"
    docker logs scitex-gitea-dev --tail 10 2>&1 | sed 's/^/  /'
}

# Check production (systemd)
check_production() {
    echo_header "=== Gitea Production Status (systemd) ==="
    echo

    # Service status
    echo_info "Service Status:"
    if systemctl is-active --quiet gitea; then
        echo_success "  ✓ Service active"

        # Service details
        UPTIME=$(systemctl show gitea --property=ActiveEnterTimestamp --value)
        echo_info "  Active since: $UPTIME"
    else
        echo_error "  ✗ Service not active"

        if systemctl is-enabled --quiet gitea 2> /dev/null; then
            echo_warning "  ⚠ Service enabled but not running"
            echo_info "  Start with: sudo systemctl start gitea"
        else
            echo_error "  ✗ Service not enabled"
            echo_info "  Enable with: sudo systemctl enable gitea"
        fi
        return 1
    fi
    echo

    # Process info
    echo_info "Process Info:"
    systemctl show gitea --property=MainPID --value | xargs -I {} ps -p {} -o pid,user,%cpu,%mem,vsz,rss,tty,stat,start,time,comm 2> /dev/null | sed 's/^/  /'
    echo

    # API connectivity
    echo_info "API Connectivity:"
    if curl -s https://git.scitex.ai/api/v1/version > /dev/null 2>&1; then
        VERSION=$(curl -s https://git.scitex.ai/api/v1/version | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
        echo_success "  ✓ API accessible"
        echo_info "  Version: $VERSION"
    else
        echo_error "  ✗ API not accessible"
    fi
    echo

    # Web UI
    echo_info "Web Interface:"
    if curl -s -o /dev/null -w "%{http_code}" https://git.scitex.ai/ | grep -q "200"; then
        echo_success "  ✓ Web UI accessible at https://git.scitex.ai"
    else
        echo_error "  ✗ Web UI not accessible"
    fi
    echo

    # SSL certificate
    echo_info "SSL Certificate:"
    if [ -f /etc/letsencrypt/live/git.scitex.ai/fullchain.pem ]; then
        EXPIRY=$(openssl x509 -enddate -noout -in /etc/letsencrypt/live/git.scitex.ai/fullchain.pem 2> /dev/null | cut -d= -f2)
        echo_success "  ✓ Certificate valid"
        echo_info "  Expires: $EXPIRY"
    else
        echo_warning "  ⚠ Certificate not found"
    fi
    echo

    # Database
    echo_info "Database Connection:"
    if sudo -u postgres psql -d gitea_prod -c "SELECT 1;" > /dev/null 2>&1; then
        echo_success "  ✓ PostgreSQL connected"

        # Database size
        DB_SIZE=$(sudo -u postgres psql -d gitea_prod -t -c "SELECT pg_size_pretty(pg_database_size('gitea_prod'));" 2> /dev/null | tr -d ' ')
        echo_info "  Size: $DB_SIZE"
    else
        echo_error "  ✗ Database connection failed"
    fi
    echo

    # Data directory
    echo_info "Data Directory:"
    if [ -d /var/lib/gitea ]; then
        DATA_SIZE=$(du -sh /var/lib/gitea 2> /dev/null | cut -f1)
        echo_success "  ✓ Directory exists"
        echo_info "  Size: $DATA_SIZE"
        echo_info "  Path: /var/lib/gitea"
    else
        echo_error "  ✗ Data directory not found"
    fi
    echo

    # Recent logs
    echo_info "Recent Logs (last 10 lines):"
    sudo journalctl -u gitea -n 10 --no-pager 2> /dev/null | sed 's/^/  /'
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
        unknown)
            echo_warning "=== Gitea Status ==="
            echo_error "✗ Gitea not detected"
            echo
            echo_info "Development (Docker):"
            echo_info "  Start: ./deployment/gitea/scripts/start-dev.sh"
            echo_info "  Check: docker ps | grep gitea"
            echo
            echo_info "Production (systemd):"
            echo_info "  Check: sudo systemctl status gitea"
            echo_info "  Deploy: sudo ./deployment/gitea/scripts/deploy-production.sh"
            exit 1
            ;;
    esac
}

main "$@" > >(tee -a "$LOG_PATH") 2> >(tee -a "$ERR_PATH" >&2)

echo -e "\nLogs: $LOG_PATH (stdout) | $ERR_PATH (stderr)"

# EOF
