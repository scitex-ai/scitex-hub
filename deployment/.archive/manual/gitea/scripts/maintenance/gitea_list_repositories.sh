#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-20 12:08:14 (ywatanabe)"
# File: ./scripts/deployment/maintenance/gitea_list_repositories.sh

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

# List all repositories in Gitea
# Works for both development and production

ERR_PATH="$THIS_DIR/.$(basename $0).err"
echo > "$ERR_PATH"

# Color codes
BLUE='\033[0;34m'

echo_header() { echo -e "${BLUE}$1${NC}"; }

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

# Load environment variables (before set -u to avoid unbound variable errors during sourcing)
if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
fi

# Enable strict mode after sourcing environment
set -euo pipefail

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

# Get API configuration
get_api_config() {
    local env=$1

    if [ "$env" = "development" ]; then
        GITEA_URL="${SCITEX_CLOUD_GITEA_URL_DEV:-http://localhost:3000}"
        GITEA_TOKEN="${SCITEX_CLOUD_GITEA_TOKEN_DEV:-}"
        ENV_DISPLAY="DEVELOPMENT"
    elif [ "$env" = "production" ]; then
        GITEA_URL="${SCITEX_CLOUD_GITEA_URL_PROD:-https://git.scitex.ai}"
        GITEA_TOKEN="${SCITEX_CLOUD_GITEA_TOKEN_PROD:-}"
        ENV_DISPLAY="PRODUCTION"
    else
        echo_error "Unknown environment"
        exit 1
    fi

    if [ -z "$GITEA_TOKEN" ]; then
        local env_file="dev"
        [ "$env" = "production" ] && env_file="prod"

        echo_error "GITEA_TOKEN not set. Please configure SCITEX_CLOUD_GITEA_TOKEN_${env^^} in your environment"
        echo_info "Run: source deployment/dotenvs/dotenv.${env_file}"
        echo_info "Or set: export SCITEX_CLOUD_GITEA_TOKEN_${env^^}=<your-token>"
        exit 1
    fi

    # Validate token by testing API access
    local test_response=$(curl -s -H "Authorization: token $GITEA_TOKEN" "$GITEA_URL/api/v1/user" 2> /dev/null)

    if echo "$test_response" | grep -q '"message":"token is required"'; then
        echo_error "Invalid or expired token!"
        echo
        echo_info "The token is set but Gitea rejects it as invalid."
        echo_info "Please generate a new token:"
        echo_info "  1. Go to $GITEA_URL"
        echo_info "  2. Login → Settings → Applications → Generate New Token"
        echo_info "  3. Update deployment/dotenvs/dotenv.${env_file}:"
        echo_info "     export SCITEX_CLOUD_GITEA_TOKEN_${env^^}=<new-token>"
        echo
        echo_error "Current token: ${GITEA_TOKEN:0:8}...${GITEA_TOKEN: -8}"
        exit 1
    elif echo "$test_response" | grep -q '"message"'; then
        echo_error "API Error: $(echo "$test_response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('message','Unknown error'))" 2> /dev/null || echo "Unknown error")"
        exit 1
    fi
}

# List all users (admin only)
list_all_users() {
    local url="$1"
    local token="$2"

    curl -s -H "Authorization: token $token" \
        "$url/api/v1/admin/users" 2> /dev/null \
        | python3 -c "
import sys, json
try:
    users = json.load(sys.stdin)
    print([u['login'] for u in users])
except:
    print('[]')
"
}

# List repositories for a user
list_user_repos() {
    local url="$1"
    local token="$2"
    local username="$3"

    curl -s -H "Authorization: token $token" \
        "$url/api/v1/users/$username/repos" 2> /dev/null
}

# Format repository info
format_repo_info() {
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
    print(f"{'ID':<6} {'Name':<30} {'Owner':<15} {'Stars':<6} {'Forks':<6} {'Size':<10} {'Updated':<20}")
    print("-" * 110)

    for repo in sorted(repos, key=lambda x: x['updated_at'], reverse=True):
        repo_id = repo['id']
        name = repo['name'][:28]
        owner = repo['owner']['login'][:13]
        stars = repo.get('stars_count', 0)
        forks = repo.get('forks_count', 0)
        size = f"{repo.get('size', 0) // 1024}MB" if repo.get('size', 0) > 1024 else f"{repo.get('size', 0)}KB"

        # Parse updated time
        try:
            updated = datetime.fromisoformat(repo['updated_at'].replace('Z', '+00:00'))
            updated_str = updated.strftime('%Y-%m-%d %H:%M')
        except:
            updated_str = repo['updated_at'][:16]

        # Visibility indicator
        private = "🔒" if repo.get('private', False) else "🌐"

        print(f"{repo_id:<6} {name:<30} {owner:<15} {stars:<6} {forks:<6} {size:<10} {updated_str:<20} {private}")

except json.JSONDecodeError:
    print("Error: Invalid JSON response from API", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
EOF
}

# Show detailed info for specific repository
show_repo_details() {
    local url="$1"
    local token="$2"
    local owner="$3"
    local repo="$4"

    echo_header "=== Repository Details: $owner/$repo ==="
    echo

    local response=$(curl -s -H "Authorization: token $token" \
        "$url/api/v1/repos/$owner/$repo" 2> /dev/null)

    echo "$response" | python3 << 'EOF'
import sys
import json
from datetime import datetime

try:
    repo = json.load(sys.stdin)

    print(f"Name:          {repo['name']}")
    print(f"Full Name:     {repo['full_name']}")
    print(f"Description:   {repo.get('description', 'N/A')}")
    print(f"Owner:         {repo['owner']['login']}")
    print(f"Private:       {'Yes' if repo.get('private', False) else 'No'}")
    print(f"Fork:          {'Yes' if repo.get('fork', False) else 'No'}")
    print(f"Stars:         {repo.get('stars_count', 0)}")
    print(f"Forks:         {repo.get('forks_count', 0)}")
    print(f"Watchers:      {repo.get('watchers_count', 0)}")
    print(f"Open Issues:   {repo.get('open_issues_count', 0)}")
    print(f"Size:          {repo.get('size', 0)} KB")
    print(f"Default Branch: {repo.get('default_branch', 'N/A')}")
    print(f"Clone URL:     {repo.get('clone_url', 'N/A')}")
    print(f"SSH URL:       {repo.get('ssh_url', 'N/A')}")

    # Timestamps
    created = datetime.fromisoformat(repo['created_at'].replace('Z', '+00:00'))
    updated = datetime.fromisoformat(repo['updated_at'].replace('Z', '+00:00'))
    print(f"Created:       {created.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Updated:       {updated.strftime('%Y-%m-%d %H:%M:%S')}")

except json.JSONDecodeError:
    print("Error: Invalid JSON response", file=sys.stderr)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
EOF
}

# Usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "List repositories in Gitea"
    echo
    echo "Options:"
    echo "  -u, --user USERNAME    List repositories for specific user"
    echo "  -a, --all              List all repositories (requires admin)"
    echo "  -d, --detail OWNER/REPO Show detailed info for a repository"
    echo "  -h, --help             Show this help message"
    echo
    echo "Examples:"
    echo "  $0                     # List current user's repositories"
    echo "  $0 -u scitex           # List scitex user's repositories"
    echo "  $0 -a                  # List all repositories"
    echo "  $0 -d scitex/test-repo # Show details for specific repo"
}

# Main
main() {
    local user=""
    local all_repos=false
    local detail_repo=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -u | --user)
                user="$2"
                shift 2
                ;;
            -a | --all)
                all_repos=true
                shift
                ;;
            -d | --detail)
                detail_repo="$2"
                shift 2
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

    # Detect environment
    ENV=$(detect_environment)

    if [ "$ENV" = "unknown" ]; then
        echo_error "Gitea not running"
        echo_info "Start with: ./deployment/gitea/scripts/start-dev.sh"
        exit 1
    fi

    # Get API config
    get_api_config "$ENV"

    echo_header "=== Gitea Repositories ($ENV_DISPLAY) ==="
    echo

    # Show detail for specific repo
    if [ -n "$detail_repo" ]; then
        IFS='/' read -r owner repo <<< "$detail_repo"
        show_repo_details "$GITEA_URL" "$GITEA_TOKEN" "$owner" "$repo"
        exit 0
    fi

    # List all repositories (admin only)
    if [ "$all_repos" = true ]; then
        echo_info "Fetching all repositories..."

        # Get all users first
        users=$(list_all_users "$GITEA_URL" "$GITEA_TOKEN")

        if [ "$users" = "[]" ]; then
            echo_warning "Cannot fetch all users (admin access required)"
            echo_info "Falling back to current user's repositories"
            user=""
        else
            # Collect repos from all users
            echo "$users" | python3 -c "
import sys, json
users = eval(sys.stdin.read())
for user in users:
    print(user)
" | while read -r username; do
                list_user_repos "$GITEA_URL" "$GITEA_TOKEN" "$username"
            done | python3 -c "
import sys, json
repos = []
for line in sys.stdin:
    try:
        user_repos = json.loads(line.strip())
        if isinstance(user_repos, list):
            repos.extend(user_repos)
    except:
        pass
print(json.dumps(repos))
" | format_repo_info
            exit 0
        fi
    fi

    # List for specific user or current user
    if [ -n "$user" ]; then
        echo_info "Fetching repositories for user: $user"
        local response=$(list_user_repos "$GITEA_URL" "$GITEA_TOKEN" "$user")
    else
        echo_info "Fetching your repositories..."
        local response=$(curl -s -H "Authorization: token $GITEA_TOKEN" "$GITEA_URL/api/v1/user/repos")
    fi

    # Check if response indicates token error
    if echo "$response" | grep -q '"message":"token is required"'; then
        echo_error "Invalid or expired token!"
        echo
        echo_info "The token is set but Gitea API rejects it."
        echo_info "Please generate a new token:"
        echo_info "  1. Go to $GITEA_URL"
        echo_info "  2. Login → Settings → Applications → Generate New Token"
        echo_info "  3. Select scopes: read:repository, read:user"
        echo_info "  4. Update in deployment/dotenvs/dotenv.dev:"
        echo_info "     export SCITEX_CLOUD_GITEA_TOKEN_DEV=<new-token>"
        echo
        echo_error "Current token: ${GITEA_TOKEN:0:8}...${GITEA_TOKEN: -8}"
        exit 1
    fi

    # Format and display
    echo "$response" | format_repo_info
}

main "$@" > >(tee -a "$LOG_PATH") 2> >(tee -a "$ERR_PATH" >&2)

echo -e "\nLogs: $LOG_PATH (stdout) | $ERR_PATH (stderr)"

# EOF
