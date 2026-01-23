#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-20 18:30:00 (ywatanabe)"
# File: ./deployment/gitea/maintenance/gitea_list_repositories.sh

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
    echo "Usage: $0 [-e|--env ENV] [-u|--user USERNAME] [-h|--help]"
    echo ""
    echo "Options:"
    echo "  -e, --env     Environment: dev or prod (required)"
    echo "  -u, --user    Filter by username (optional)"
    echo "  -h, --help    Display this help message"
    echo ""
    echo "Example:"
    echo "  $0 -e dev                    # List all repositories"
    echo "  $0 -e prod -u ywatanabe      # List repositories for user 'ywatanabe'"
    exit 1
}

parse_args() {
    ENV=""
    USERNAME=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            -e | --env)
                ENV="$2"
                shift 2
                ;;
            -u | --user)
                USERNAME="$2"
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
    else
        GITEA_DB_NAME="gitea_prod"
        GITEA_DB_USER="gitea_prod"
        DOMAIN="git.scitex.ai"
        HTTP_PORT="3000"
        SSH_PORT="2222"
        ROOT_URL="https://${DOMAIN}/"
        SERVICE_NAME="gitea_prod"
    fi
}

check_database() {
    if ! sudo -u postgres psql -lqt 2> /dev/null | cut -d \| -f 1 | grep -qw "$GITEA_DB_NAME"; then
        echo_error "Database not found: $GITEA_DB_NAME"
        echo_warning "Run: sudo ./deployment/gitea/setup_gitea.sh -e $ENV"
        exit 1
    fi
}

list_repositories() {
    echo_blue "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo_blue "  Gitea Repositories (${ENV})"
    echo_blue "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Build SQL query
    SQL_QUERY="
        SELECT
            u.name as owner,
            r.name as repo,
            r.is_private,
            r.num_stars,
            r.num_forks,
            r.size,
            to_char(r.created_unix, 'YYYY-MM-DD HH24:MI:SS') as created,
            to_char(r.updated_unix, 'YYYY-MM-DD HH24:MI:SS') as updated
        FROM repository r
        JOIN \"user\" u ON r.owner_id = u.id
    "

    if [ -n "$USERNAME" ]; then
        SQL_QUERY="$SQL_QUERY WHERE u.name = '$USERNAME'"
    fi

    SQL_QUERY="$SQL_QUERY ORDER BY r.updated_unix DESC;"

    # Get repository count
    TOTAL_REPOS=$(sudo -u postgres psql -d "$GITEA_DB_NAME" -tAc "SELECT COUNT(*) FROM repository;" 2> /dev/null || echo "0")
    echo_info "Total repositories: $TOTAL_REPOS"
    echo ""

    # Execute query and format output
    RESULT=$(sudo -u postgres psql -d "$GITEA_DB_NAME" -c "$SQL_QUERY" 2> /dev/null)

    if [ -z "$RESULT" ] || [ "$TOTAL_REPOS" = "0" ]; then
        echo_warning "No repositories found"
        if [ -n "$USERNAME" ]; then
            echo_info "  (filtered by user: $USERNAME)"
        fi
        echo ""
        echo_info "To create a repository:"
        echo "  1. Go to: $ROOT_URL"
        echo "  2. Click '+' → New Repository"
        echo ""
        return
    fi

    # Display results
    echo "$RESULT" | sed 's/^/  /'
    echo ""

    # Get detailed statistics
    echo_blue "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo_blue "  Statistics"
    echo_blue "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Count by type
    PUBLIC_REPOS=$(sudo -u postgres psql -d "$GITEA_DB_NAME" -tAc "SELECT COUNT(*) FROM repository WHERE is_private = false;" 2> /dev/null || echo "0")
    PRIVATE_REPOS=$(sudo -u postgres psql -d "$GITEA_DB_NAME" -tAc "SELECT COUNT(*) FROM repository WHERE is_private = true;" 2> /dev/null || echo "0")

    echo_info "Repository Types:"
    echo "  Public:  $PUBLIC_REPOS"
    echo "  Private: $PRIVATE_REPOS"
    echo ""

    # Total size
    TOTAL_SIZE=$(sudo -u postgres psql -d "$GITEA_DB_NAME" -tAc "SELECT SUM(size) FROM repository;" 2> /dev/null || echo "0")
    TOTAL_SIZE_MB=$((TOTAL_SIZE / 1024 / 1024))

    echo_info "Total Size: ${TOTAL_SIZE_MB} MB"
    echo ""

    # Active users
    ACTIVE_USERS=$(sudo -u postgres psql -d "$GITEA_DB_NAME" -tAc "SELECT COUNT(DISTINCT owner_id) FROM repository;" 2> /dev/null || echo "0")
    echo_info "Active Repository Owners: $ACTIVE_USERS"
    echo ""
}

list_clone_commands() {
    echo_blue "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo_blue "  Clone Commands"
    echo_blue "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Get repository list for clone commands
    REPO_LIST=$(sudo -u postgres psql -d "$GITEA_DB_NAME" -tAc "
        SELECT u.name || '/' || r.name
        FROM repository r
        JOIN \"user\" u ON r.owner_id = u.id
        ORDER BY r.updated_unix DESC
        LIMIT 10;" 2> /dev/null)

    if [ -z "$REPO_LIST" ]; then
        echo_warning "No repositories to clone"
        return
    fi

    echo_info "SSH Clone (recommended):"
    echo ""
    while IFS= read -r repo; do
        if [ -n "$repo" ]; then
            echo "  git clone ssh://git@${DOMAIN}:${SSH_PORT}/${repo}.git"
        fi
    done <<< "$REPO_LIST"
    echo ""

    echo_info "HTTP Clone:"
    echo ""
    while IFS= read -r repo; do
        if [ -n "$repo" ]; then
            if [ "$ENV" = "dev" ]; then
                echo "  git clone http://localhost:${HTTP_PORT}/${repo}.git"
            else
                echo "  git clone https://${DOMAIN}/${repo}.git"
            fi
        fi
    done <<< "$REPO_LIST"
    echo ""
}

print_access_info() {
    echo_blue "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo_blue "  Access Information"
    echo_blue "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo_info "Web Interface: $ROOT_URL"
    echo_info "SSH Port: $SSH_PORT"
    echo_info "HTTP Port: $HTTP_PORT"
    echo ""
    echo_blue "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

main() {
    parse_args "$@"
    set_environment_variables
    check_database

    echo_info "=== Gitea Repository List (${ENV}) ==="
    if [ -n "$USERNAME" ]; then
        echo_info "    Filter: user = $USERNAME"
    fi
    echo ""

    list_repositories
    list_clone_commands
    print_access_info
}

main "$@" 2>&1 | tee -a "$LOG_PATH"

# EOF
