#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-27 07:00:00 (ywatanabe)"
# File: ./containers/docker/scripts/maintenance/gitea_check_status.sh
#
# Docker-specific Gitea status checker
# This script is designed specifically for Docker Compose deployments

ORIG_DIR="$(pwd)"
THIS_DIR="$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)"
LOG_PATH="$THIS_DIR/.$(basename $0).log"
echo -e > "$LOG_PATH"

GIT_ROOT="$(git rev-parse --show-toplevel 2> /dev/null)"
DOCKER_DIR="$GIT_ROOT/deployment/docker/docker_dev"

# Colors
GRAY='\033[0;90m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo_info() { echo -e "${GRAY}$1${NC}"; }
echo_success() { echo -e "${GREEN}$1${NC}"; }
echo_warning() { echo -e "${YELLOW}$1${NC}"; }
echo_error() { echo -e "${RED}$1${NC}"; }
echo_header() { echo -e "${BLUE}=== $1 ===${NC}"; }

# Load environment
load_environment() {
    if [ -f "$GIT_ROOT/.env" ]; then
        set -a
        source "$GIT_ROOT/.env"
        set +a
    fi
}

check_gitea_status() {
    echo_header "Gitea Status (Docker Compose)"
    echo

    cd "$DOCKER_DIR" || exit 1

    # Container status
    echo_info "Container Status:"
    if docker-compose -f docker-compose.dev.yml ps | grep -q "docker_gitea_1"; then
        STATUS=$(docker-compose -f docker-compose.dev.yml ps docker_gitea_1 2> /dev/null | grep docker_gitea_1 | awk '{print $4}')

        if echo -e "$STATUS" | grep -q "Up"; then
            echo_success "  ✓ Container running"

            # Check health status
            if echo -e "$STATUS" | grep -q "healthy"; then
                echo_success "  ✓ Health check passed"
            else
                echo_warning "  ⚠ Health check pending or failing"
            fi

            # Uptime
            UPTIME=$(docker ps --filter name=docker_gitea_1 --format "{{.Status}}")
            echo_info "  Uptime: $UPTIME"
        else
            echo_error "  ✗ Container not running"
            echo_info "  Status: $STATUS"
            echo_info "  Start: cd $DOCKER_DIR && ./start_dev.sh"
            return 1
        fi
    else
        echo_error "  ✗ Container not found"
        echo_info "  Create: cd $DOCKER_DIR && ./start_dev.sh -a start"
        return 1
    fi
    echo

    # Port bindings
    echo_info "Port Bindings:"
    docker port docker_gitea_1 2> /dev/null | while read line; do
        echo_info "  $line"
    done
    echo

    # API connectivity
    echo_info "API Connectivity:"
    GITEA_URL="${SCITEX_HUB_GITEA_URL_DEV:-http://127.0.0.1:3000}"

    if curl -f -s "${GITEA_URL}/api/v1/version" > /dev/null 2>&1; then
        VERSION=$(curl -s "${GITEA_URL}/api/v1/version" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
        echo_success "  ✓ API accessible at ${GITEA_URL}/api/v1"
        echo_info "  Gitea Version: $VERSION"
    else
        echo_error "  ✗ API not accessible at ${GITEA_URL}"
    fi
    echo

    # Authentication test
    echo_info "Authentication:"
    GITEA_TOKEN="${SCITEX_HUB_GITEA_TOKEN_DEV}"

    if [ -n "$GITEA_TOKEN" ]; then
        AUTH_RESPONSE=$(curl -s -H "Authorization: token ${GITEA_TOKEN}" \
            "${GITEA_URL}/api/v1/user" 2> /dev/null)

        if echo -e "$AUTH_RESPONSE" | grep -q '"login"'; then
            GITEA_USER=$(echo -e "$AUTH_RESPONSE" | grep -o '"login":"[^"]*"' | cut -d'"' -f4)
            echo_success "  ✓ Token valid for user: $GITEA_USER"
        else
            echo_error "  ✗ Token authentication failed"
            echo_info "  Check: SCITEX_HUB_GITEA_TOKEN_DEV in .env"
        fi
    else
        echo_warning "  ⚠ No token configured"
        echo_info "  Set: SCITEX_HUB_GITEA_TOKEN_DEV in .env"
    fi
    echo

    # Web UI
    echo_info "Web Interface:"
    if curl -s -o /dev/null -w "%{http_code}" "${GITEA_URL}/" | grep -q "200"; then
        echo_success "  ✓ Web UI accessible at ${GITEA_URL}"
    else
        echo_error "  ✗ Web UI not accessible"
    fi
    echo

    # Resource usage
    echo_info "Resource Usage:"
    docker stats docker_gitea_1 --no-stream --format \
        "  CPU: {{.CPUPerc}}  |  Memory: {{.MemUsage}}  |  Net I/O: {{.NetIO}}  |  Block I/O: {{.BlockIO}}" \
        2> /dev/null
    echo

    # Volume
    echo_info "Data Volume:"
    if docker volume inspect docker_gitea_data > /dev/null 2>&1; then
        echo_success "  ✓ Volume exists: docker_gitea_data"

        # Get volume size (approximate)
        VOLUME_MOUNTPOINT=$(docker volume inspect docker_gitea_data --format '{{.Mountpoint}}' 2> /dev/null)
        if [ -n "$VOLUME_MOUNTPOINT" ] && [ -d "$VOLUME_MOUNTPOINT" ]; then
            VOLUME_SIZE=$(sudo du -sh "$VOLUME_MOUNTPOINT" 2> /dev/null | cut -f1 || echo -e "N/A")
            echo_info "  Size: $VOLUME_SIZE"
        fi
        echo_info "  Mountpoint: $VOLUME_MOUNTPOINT"
    else
        echo_warning "  ⚠ Volume not found"
        echo_info "  Volume will be created on first start"
    fi
    echo

    # Recent logs
    echo_info "Recent Logs (last 10 lines):"
    docker logs docker_gitea_1 --tail 10 2>&1 | sed 's/^/  /' | tail -10
    echo

    # Summary
    echo_header "Quick Actions"
    echo_info "View logs:     docker logs docker_gitea_1 -f"
    echo_info "Restart:       cd $DOCKER_DIR && ./start_dev.sh -a restart"
    echo_info "Full restart:  cd $DOCKER_DIR && ./start_dev.sh -a start"
    echo_info "Shell access:  docker exec -it docker_gitea_1 /bin/sh"
    echo_info "API check:     python $GIT_ROOT/scripts/check_gitea_api.py"
}

main() {
    load_environment
    check_gitea_status
}

main "$@" 2>&1 | tee -a "$LOG_PATH"

echo
echo -e "${GRAY}Log saved to: $LOG_PATH${NC}"

# EOF
