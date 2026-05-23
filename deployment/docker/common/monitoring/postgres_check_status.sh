#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-27 07:15:00 (ywatanabe)"
# File: ./containers/docker/scripts/maintenance/postgres_check_status.sh
#
# Docker-specific PostgreSQL status checker

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
if [ -f "$GIT_ROOT/.env" ]; then
    set -a
    source "$GIT_ROOT/.env"
    set +a
fi

check_postgres_status() {
    echo_header "PostgreSQL Status (Docker Compose)"
    echo

    cd "$DOCKER_DIR" || exit 1

    # Container status
    echo_info "Container Status:"
    if docker-compose -f docker-compose.dev.yml ps | grep -q "docker_db_1"; then
        STATUS=$(docker-compose -f docker-compose.dev.yml ps docker_db_1 2> /dev/null | grep docker_db_1 | awk '{print $4}')

        if echo -e "$STATUS" | grep -q "Up"; then
            echo_success "  ✓ Container running"

            # Check health status
            if echo -e "$STATUS" | grep -q "healthy"; then
                echo_success "  ✓ Health check passed"
            else
                echo_warning "  ⚠ Health check pending or failing"
            fi

            # Uptime
            UPTIME=$(docker ps --filter name=docker_db_1 --format "{{.Status}}")
            echo_info "  Uptime: $UPTIME"
        else
            echo_error "  ✗ Container not running"
            echo_info "  Status: $STATUS"
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
    docker port docker_db_1 2> /dev/null | while read line; do
        echo_info "  $line"
    done
    echo

    # Database connection test
    echo_info "Database Connection:"
    SCITEX_CLOUD_POSTGRES_USER="${SCITEX_CLOUD_POSTGRES_USER:-scitex_dev}"
    SCITEX_CLOUD_POSTGRES_DB="${SCITEX_CLOUD_POSTGRES_DB:-scitex_hub_dev}"

    if docker-compose -f docker-compose.dev.yml exec -T db \
        psql -U "$SCITEX_CLOUD_POSTGRES_USER" -d "$SCITEX_CLOUD_POSTGRES_DB" -c "SELECT 1;" > /dev/null 2>&1; then
        echo_success "  ✓ Connection successful"
        echo_info "  User: $SCITEX_CLOUD_POSTGRES_USER"
        echo_info "  Database: $SCITEX_CLOUD_POSTGRES_DB"
    else
        echo_error "  ✗ Connection failed"
        echo_info "  Check credentials in .env"
        return 1
    fi
    echo

    # Database version
    echo_info "PostgreSQL Version:"
    VERSION=$(docker-compose -f docker-compose.dev.yml exec -T db \
        psql -U "$SCITEX_CLOUD_POSTGRES_USER" -t -c "SELECT version();" 2> /dev/null | head -1 | xargs)
    echo_info "  $VERSION"
    echo

    # Database size
    echo_info "Database Size:"
    DB_SIZE=$(docker-compose -f docker-compose.dev.yml exec -T db \
        psql -U "$SCITEX_CLOUD_POSTGRES_USER" -d "$SCITEX_CLOUD_POSTGRES_DB" -t \
        -c "SELECT pg_size_pretty(pg_database_size('$SCITEX_CLOUD_POSTGRES_DB'));" 2> /dev/null | xargs)
    echo_info "  $SCITEX_CLOUD_POSTGRES_DB: $DB_SIZE"
    echo

    # Active connections
    echo_info "Active Connections:"
    docker-compose -f docker-compose.dev.yml exec -T db \
        psql -U "$SCITEX_CLOUD_POSTGRES_USER" -d "$SCITEX_CLOUD_POSTGRES_DB" -c \
        "SELECT datname, count(*) as connections
         FROM pg_stat_activity
         WHERE datname IS NOT NULL
         GROUP BY datname;" 2> /dev/null | sed 's/^/  /'
    echo

    # Tables
    echo_info "Tables in $SCITEX_CLOUD_POSTGRES_DB:"
    TABLE_COUNT=$(docker-compose -f docker-compose.dev.yml exec -T db \
        psql -U "$SCITEX_CLOUD_POSTGRES_USER" -d "$SCITEX_CLOUD_POSTGRES_DB" -t \
        -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2> /dev/null | xargs)
    echo_info "  Total tables: $TABLE_COUNT"

    if [ "$TABLE_COUNT" -gt 0 ]; then
        echo_info "  Recent tables (top 5 by size):"
        docker-compose -f docker-compose.dev.yml exec -T db \
            psql -U "$SCITEX_CLOUD_POSTGRES_USER" -d "$SCITEX_CLOUD_POSTGRES_DB" -c \
            "SELECT tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
             FROM pg_tables
             WHERE schemaname = 'public'
             ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
             LIMIT 5;" 2> /dev/null | sed 's/^/    /'
    fi
    echo

    # Resource usage
    echo_info "Resource Usage:"
    docker stats docker_db_1 --no-stream --format \
        "  CPU: {{.CPUPerc}}  |  Memory: {{.MemUsage}}  |  Net I/O: {{.NetIO}}  |  Block I/O: {{.BlockIO}}" \
        2> /dev/null
    echo

    # Volume
    echo_info "Data Volume:"
    if docker volume inspect docker_postgres_data > /dev/null 2>&1; then
        echo_success "  ✓ Volume exists: docker_postgres_data"

        VOLUME_MOUNTPOINT=$(docker volume inspect docker_postgres_data --format '{{.Mountpoint}}' 2> /dev/null)
        if [ -n "$VOLUME_MOUNTPOINT" ] && [ -d "$VOLUME_MOUNTPOINT" ]; then
            VOLUME_SIZE=$(sudo du -sh "$VOLUME_MOUNTPOINT" 2> /dev/null | cut -f1 || echo -e "N/A")
            echo_info "  Size: $VOLUME_SIZE"
        fi
        echo_info "  Mountpoint: $VOLUME_MOUNTPOINT"
    else
        echo_warning "  ⚠ Volume not found"
    fi
    echo

    # Recent logs
    echo_info "Recent Logs (last 5 lines):"
    docker logs docker_db_1 --tail 5 2>&1 | sed 's/^/  /'
    echo

    # Summary
    echo_header "Quick Actions"
    echo_info "View logs:     docker logs docker_db_1 -f"
    echo_info "psql shell:    docker-compose -f docker-compose.dev.yml exec db psql -U $SCITEX_CLOUD_POSTGRES_USER -d $SCITEX_CLOUD_POSTGRES_DB"
    echo_info "Backup DB:     docker-compose -f docker-compose.dev.yml exec db pg_dump -U $SCITEX_CLOUD_POSTGRES_USER $SCITEX_CLOUD_POSTGRES_DB > backup.sql"
    echo_info "Restart:       cd $DOCKER_DIR && docker-compose -f docker-compose.dev.yml restart db"
}

main() {
    check_postgres_status
}

main "$@" 2>&1 | tee -a "$LOG_PATH"

echo
echo -e "${GRAY}Log saved to: $LOG_PATH${NC}"

# EOF
