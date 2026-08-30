#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-20 15:07:00 (ywatanabe)"
# File: ./scripts/deployment/backup_database.sh

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
BACKUP_DIR="$PROJECT_ROOT/data/db/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

usage() {
    echo "Usage: $0 [-e|--env ENV] [-h|--help]"
    echo ""
    echo "Options:"
    echo "  -e, --env    Environment: dev or prod (default: both)"
    echo "  -h, --help   Display this help message"
    echo ""
    echo "Example:"
    echo "  $0 -e dev"
    echo "  $0 --env prod"
    exit 1
}

backup_postgres() {
    local db_name="$1"
    local db_user="$2"
    local backup_file="$BACKUP_DIR/${db_name}_${TIMESTAMP}.sql"

    echo_info "Backing up PostgreSQL: $db_name"

    if ! command -v pg_dump &> /dev/null; then
        echo_warning "pg_dump not found, skipping..."
        return 1
    fi

    if ! pg_isready -q 2> /dev/null; then
        echo_warning "PostgreSQL is not running, skipping..."
        return 1
    fi

    if pg_dump -U "$db_user" "$db_name" > "$backup_file" 2> /dev/null; then
        gzip "$backup_file"
        echo_success "Backup created: ${backup_file}.gz"
        return 0
    else
        echo_error "Failed to backup $db_name"
        return 1
    fi
}

cleanup_old_backups() {
    echo_info "Cleaning up backups older than 7 days..."
    find "$BACKUP_DIR" -name "*.gz" -mtime +7 -delete
    echo_success "Cleanup completed"
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

    echo_info "=== SciTeX Hub Database Backup ==="
    echo_info "Timestamp: $TIMESTAMP"
    echo ""

    mkdir -p "$BACKUP_DIR"

    if [ -z "$ENV" ] || [ "$ENV" = "dev" ]; then
        backup_postgres "scitex_hub_dev" "scitex_dev"
    fi

    if [ -z "$ENV" ] || [ "$ENV" = "prod" ]; then
        backup_postgres "scitex_hub_prod" "scitex_prod"
    fi

    echo ""
    cleanup_old_backups
    echo ""
    echo_success "Backup completed"
    echo_info "Location: $BACKUP_DIR"
    du -sh "$BACKUP_DIR"
}

main "$@" 2>&1 | tee -a "$LOG_PATH"

# EOF
