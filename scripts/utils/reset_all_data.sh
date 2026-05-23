#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-10 15:53:17 (ywatanabe)"
# File: ./scripts/utils/reset_all_data.sh

ORIG_DIR="$(pwd)"
THIS_DIR="$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)"
LOG_PATH="$THIS_DIR/.$(basename $0).log"
echo > "$LOG_PATH"

GIT_ROOT="$(git rev-parse --show-toplevel 2> /dev/null)"

GRAY='\033[0;90m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo_info() { echo -e "${GRAY}INFO: $1${NC}"; }
echo_success() { echo -e "${GREEN}SUCC: $1${NC}"; }
echo_warning() { echo -e "${YELLOW}WARN: $1${NC}"; }
echo_error() { echo -e "${RED}ERRO: $1${NC}"; }
echo_header() { echo_info "=== $1 ==="; }
# ---------------------------------------

# Reset all users and projects for fresh start, with preparing visitor pool

# Colors
BLUE='\033[0;34m'
BOLD='\033[1m'

# Functions

# Display usage information
# Example: usage
usage() {
    cat << EOF
${BOLD}Reset All Data - SciTeX Hub${NC}

Delete all users and projects for a fresh start with v2.0.0-beta.

${BOLD}⚠️  RECOMMENDATION:${NC}
    For complete fresh start including database and Gitea volumes, use:
    ${BLUE}make ENV=dev fresh-start${NC}

    This script only resets Django data. For full reset, use the Makefile command above.

${BOLD}Usage:${NC}
    $0 [OPTIONS]

${BOLD}Options:${NC}
    --dry-run               Show what would be deleted without deleting
    --confirm           withoutually delete (required for real deletion)
    --keep-users            Only delete projects, keep users
    --delete-directories    Also delete project directories from filesystem
    --env <env>             Environment: dev or prod (default: dev)
    -h, --help              Show this help message

${BOLD}Examples:${NC}
    # Preview what would be deleted
    $0 --dry-run

    # Delete all projects and users
    $0 --confirm

    # Delete only projects, keep users
    $0 --confirm --keep-users

    # Delete everything including directories
    $0 --confirm --delete-directories

    # Run in production environment
    $0 --confirm --env prod

${BOLD}Safety Features:${NC}
    - Requires --confirm flag (or --dry-run) to run
    - Preserves superuser accounts
    - Shows detailed summary
    - Runs in Docker for proper database/Gitea access

${BOLD}Note:${NC}
    This script will restart the Docker containers to ensure
    a clean state before performing the reset.
EOF
    exit 1
}

# Restart Docker containers for the given environment
# Example: restart_containers "dev"
restart_containers() {
    local env="$1"

    echo_header "Step 1/3: Restarting Docker containers"
    echo_info "Running: make ENV=$env restart"

    cd "$GIT_ROOT" || {
        echo_error "Failed to change to git root directory"
        return 1
    }

    if ! make ENV="$env" restart; then
        echo_error "Failed to restart Docker containers"
        return 1
    fi

    echo_success "Docker containers restarted"
    echo ""
    return 0
}

# Run reset command in Docker container
# Example: run_reset_command "dev" "--dry-run"
run_reset_command() {
    local env="$1"
    local cmd_args="$2"
    local container_name="scitex-hub-$env-web-1"

    echo_header "Step 2/3: Running reset command in Docker"
    echo_info "Container: $container_name"
    echo_info "Command: python manage.py reset_all_data $cmd_args"
    echo ""

    if ! docker exec "$container_name" python manage.py reset_all_data $cmd_args; then
        echo_error "Reset command failed"
        return 1
    fi

    return 0
}

# Recreate visitor pool after reset
# Example: recreate_visitor_pool "dev"
recreate_visitor_pool() {
    local env="$1"
    local container_name="scitex-hub-$env-web-1"

    echo_header "Step 3/3: Recreating visitor pool"
    echo_info "Container: $container_name"
    echo_info "Command: python manage.py create_visitor_pool"
    echo ""

    if docker exec "$container_name" python manage.py create_visitor_pool; then
        echo_success "✓ Visitor pool recreated (4 visitor accounts with workspaces)"
        return 0
    else
        echo_error "Failed to recreate visitor pool"
        echo_warning "You may need to run manually:"
        echo_warning "  docker exec $container_name python manage.py create_visitor_pool"
        return 1
    fi
}

# Main function
# Example: main --dry-run
main() {
    # Default values
    local env="dev"
    local dry_run=""
    local confirm=""
    local keep_users=""
    local delete_dirs=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                dry_run="--dry-run"
                shift
                ;;
            --confirm)
                confirm="--confirm"
                shift
                ;;
            --keep-users)
                keep_users="--keep-users"
                shift
                ;;
            --delete-directories)
                delete_dirs="--delete-directories"
                shift
                ;;
            --env)
                env="$2"
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

    # Validate arguments
    if [[ -z "$dry_run" && -z "$confirm" ]]; then
        echo_error "⚠️  DANGER: This will delete all users and projects!"
        echo ""
        echo "Use one of the following options:"
        echo "  --dry-run   : Preview what would be deleted"
        echo "  --confirm   : Actually perform the deletion"
        echo ""
        echo "Run with --help for more information"
        exit 1
    fi

    # Build command arguments
    local cmd_args="$dry_run $confirm $keep_users $delete_dirs"

    # Header
    echo ""
    echo_header "SciTeX Hub - Reset All Data"
    echo_info "Environment: $env"
    echo_info "Command args: $cmd_args"
    echo ""

    # Restart Docker containers
    if ! restart_containers "$env"; then
        exit 1
    fi

    # Run reset command in Docker
    if ! run_reset_command "$env" "$cmd_args"; then
        exit 1
    fi

    # Recreate visitor pool (only if actual deletion was performed)
    if [[ -n "$confirm" ]]; then
        echo ""
        if ! recreate_visitor_pool "$env"; then
            echo_warning "Continuing despite visitor pool recreation failure..."
        fi
    fi

    # Success message
    echo ""
    echo_success "✨ Reset command completed successfully!"

    if [[ -n "$dry_run" ]]; then
        echo ""
        echo_warning "This was a DRY RUN - no actual deletions were performed"
        echo_info "Run with --confirm to actually delete data"
    else
        echo ""
        echo_success "🎉 Fresh start ready!"
        echo_info "You can now create new projects with the latest features"
    fi

    echo ""
}

main "$@" 2>&1 | tee -a "$LOG_PATH"

# EOF
