#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-27 07:10:00 (ywatanabe)"
# File: ./containers/docker/scripts/maintenance/gitea_list_repositories.sh
#
# Docker-specific Gitea repository listing script

ORIG_DIR="$(pwd)"
THIS_DIR="$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)"
LOG_PATH="$THIS_DIR/.$(basename $0).log"
echo -e > "$LOG_PATH"

GIT_ROOT="$(git rev-parse --show-toplevel 2> /dev/null)"

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

# Format repository list
format_repo_list() {
    python3 << 'EOF'
import sys
import json
from datetime import datetime

try:
    repos = json.load(sys.stdin)

    if not repos:
        print("No repositories found")
        sys.exit(0)

    print(f"Total repositories: {len(repos)}\n")
    print(f"{'Owner':<15} {'Name':<30} {'Private':<8} {'Stars':<6} {'Forks':<6} {'Size':<10}")
    print("-" * 85)

    for repo in sorted(repos, key=lambda x: x.get('updated_at', ''), reverse=True):
        owner = repo.get('owner', {}).get('login', 'N/A')[:13]
        name = repo.get('name', 'N/A')[:28]
        is_private = "✓" if repo.get('private', False) else ""
        stars = repo.get('stars_count', 0)
        forks = repo.get('forks_count', 0)
        size = f"{repo.get('size', 0)} KB"

        print(f"{owner:<15} {name:<30} {is_private:<8} {stars:<6} {forks:<6} {size:<10}")

    # Summary
    private_count = sum(1 for r in repos if r.get('private', False))
    total_size = sum(r.get('size', 0) for r in repos)

    print()
    print(f"Summary:")
    print(f"  Private repositories: {private_count}/{len(repos)}")
    print(f"  Total size: {total_size} KB ({total_size/1024:.2f} MB)")

except json.JSONDecodeError:
    print("Error: Invalid JSON response from API", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
EOF
}

# Show repository details
show_repo_details() {
    local owner="$1"
    local repo="$2"

    echo_header "Repository Details: $owner/$repo"
    echo

    response=$(curl -s -H "Authorization: token $GITEA_TOKEN" \
        "$GITEA_URL/api/v1/repos/$owner/$repo" 2> /dev/null)

    echo -e "$response" | python3 << 'EOF'
import sys
import json
from datetime import datetime

try:
    repo = json.load(sys.stdin)

    if 'message' in repo:
        print(f"Error: {repo['message']}")
        sys.exit(1)

    print(f"Full Name:       {repo.get('full_name', 'N/A')}")
    print(f"Description:     {repo.get('description', 'N/A')}")
    print(f"Owner:           {repo.get('owner', {}).get('login', 'N/A')}")
    print(f"Private:         {'Yes' if repo.get('private', False) else 'No'}")
    print(f"Fork:            {'Yes' if repo.get('fork', False) else 'No'}")
    print(f"Default Branch:  {repo.get('default_branch', 'N/A')}")
    print(f"Size:            {repo.get('size', 0)} KB")

    print(f"\nStatistics:")
    print(f"  Stars:         {repo.get('stars_count', 0)}")
    print(f"  Watchers:      {repo.get('watchers_count', 0)}")
    print(f"  Forks:         {repo.get('forks_count', 0)}")
    print(f"  Open Issues:   {repo.get('open_issues_count', 0)}")

    print(f"\nURLs:")
    print(f"  Clone (HTTPS): {repo.get('clone_url', 'N/A')}")
    print(f"  Clone (SSH):   {repo.get('ssh_url', 'N/A')}")
    print(f"  Web:           {repo.get('html_url', 'N/A')}")

    # Timestamps
    created = repo.get('created_at', '')
    if created:
        created_time = datetime.fromisoformat(created.replace('Z', '+00:00'))
        print(f"\nCreated:         {created_time.strftime('%Y-%m-%d %H:%M:%S')}")

    updated = repo.get('updated_at', '')
    if updated:
        updated_time = datetime.fromisoformat(updated.replace('Z', '+00:00'))
        print(f"Last Updated:    {updated_time.strftime('%Y-%m-%d %H:%M:%S')}")

except json.JSONDecodeError:
    print("Error: Invalid JSON response", file=sys.stderr)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
EOF
}

# Usage
usage() {
    echo -e "Usage: $0 [OPTIONS]"
    echo
    echo -e "List repositories in Gitea (Docker deployment)"
    echo
    echo -e "Options:"
    echo -e "  -u, --user USERNAME    List repositories for a specific user"
    echo -e "  -d, --detail OWNER/REPO Show detailed info for a repository"
    echo -e "  -p, --private          Show only private repositories"
    echo -e "  -h, --help             Show this help message"
    echo
    echo -e "Examples:"
    echo -e "  $0                     # List all accessible repositories"
    echo -e "  $0 -u scitex           # List repositories for user 'scitex'"
    echo -e "  $0 -d scitex/test-repo # Show details for repository"
    echo -e "  $0 -p                  # List only private repositories"
}

# Main
main() {
    local username=""
    local detail_repo=""
    local private_only=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -u | --user)
                username="$2"
                shift 2
                ;;
            -d | --detail)
                detail_repo="$2"
                shift 2
                ;;
            -p | --private)
                private_only=true
                shift
                ;;
            -h | --help)
                usage
                exit 0
                ;;
            *)
                echo_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    # Configuration
    GITEA_URL="${SCITEX_HUB_GITEA_URL_DEV:-http://127.0.0.1:3000}"
    GITEA_TOKEN="${SCITEX_HUB_GITEA_TOKEN_DEV}"

    if [ -z "$GITEA_TOKEN" ]; then
        echo_error "GITEA_TOKEN not set"
        echo_info "Set SCITEX_HUB_GITEA_TOKEN_DEV in .env"
        exit 1
    fi

    # Validate token
    test_response=$(curl -s -H "Authorization: token $GITEA_TOKEN" \
        "$GITEA_URL/api/v1/user" 2> /dev/null)

    if ! echo -e "$test_response" | grep -q '"login"'; then
        echo_error "Invalid or expired token"
        echo_info "Check SCITEX_HUB_GITEA_TOKEN_DEV in .env"
        exit 1
    fi

    echo_header "Gitea Repositories (Docker Development)"
    echo

    # Show detail for specific repository
    if [ -n "$detail_repo" ]; then
        owner=$(echo -e "$detail_repo" | cut -d'/' -f1)
        repo=$(echo -e "$detail_repo" | cut -d'/' -f2)
        show_repo_details "$owner" "$repo"
        exit 0
    fi

    # Fetch repositories
    if [ -n "$username" ]; then
        echo_info "Fetching repositories for user: $username"
        response=$(curl -s -H "Authorization: token $GITEA_TOKEN" \
            "$GITEA_URL/api/v1/users/$username/repos" 2> /dev/null)
    else
        echo_info "Fetching your repositories..."
        response=$(curl -s -H "Authorization: token $GITEA_TOKEN" \
            "$GITEA_URL/api/v1/user/repos" 2> /dev/null)
    fi

    # Filter private repos if requested
    if [ "$private_only" = true ]; then
        response=$(echo -e "$response" | python3 -c "
import sys, json
repos = json.load(sys.stdin)
private = [r for r in repos if r.get('private', False)]
print(json.dumps(private))
")
    fi

    echo -e "$response" | format_repo_list
}

main "$@" 2>&1 | tee -a "$LOG_PATH"

echo
echo -e "${GRAY}Log saved to: $LOG_PATH${NC}"

# EOF
