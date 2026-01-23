#!/bin/bash
# -*- coding: utf-8 -*-
# List all users in Gitea
# Works for both development and production

ORIG_DIR="$(pwd)"
THIS_DIR="$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)"
LOG_PATH="$THIS_DIR/.$(basename $0).log"
ERR_PATH="$THIS_DIR/.$(basename $0).err"
echo > "$LOG_PATH"
echo > "$ERR_PATH"

# Color codes
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

# List all users (requires admin token)
list_all_users() {
    local url="$1"
    local token="$2"

    curl -s -H "Authorization: token $token" \
        "$url/api/v1/admin/users" 2> /dev/null
}

# Search users (public API)
search_users() {
    local url="$1"
    local token="$2"
    local query="${3:-}"

    local endpoint="$url/api/v1/users/search"
    if [ -n "$query" ]; then
        endpoint="$endpoint?q=$query"
    fi

    curl -s -H "Authorization: token $token" "$endpoint" 2> /dev/null \
        | python3 -c "import sys, json; data = json.load(sys.stdin); print(json.dumps(data.get('data', [])))"
}

# Get user details
get_user_details() {
    local url="$1"
    local token="$2"
    local username="$3"

    curl -s -H "Authorization: token $token" \
        "$url/api/v1/users/$username" 2> /dev/null
}

# Format user list
format_user_list() {
    python3 << 'EOF'
import sys
import json
from datetime import datetime

try:
    users = json.load(sys.stdin)

    if not users:
        print("No users found")
        sys.exit(0)

    print(f"Total users: {len(users)}\n")
    print(f"{'ID':<6} {'Username':<20} {'Full Name':<25} {'Email':<30} {'Admin':<6} {'Active':<7} {'Last Login':<20}")
    print("-" * 120)

    for user in sorted(users, key=lambda x: x.get('id', 0)):
        user_id = user.get('id', 'N/A')
        username = user.get('login', user.get('username', 'N/A'))[:18]
        full_name = user.get('full_name', '')[:23]
        email = user.get('email', 'N/A')[:28]
        is_admin = "✓" if user.get('is_admin', False) else ""
        is_active = "✓" if user.get('active', True) else "✗"

        # Parse last login
        last_login = user.get('last_login', '')
        if last_login:
            try:
                login_time = datetime.fromisoformat(last_login.replace('Z', '+00:00'))
                last_login_str = login_time.strftime('%Y-%m-%d %H:%M')
            except:
                last_login_str = last_login[:16]
        else:
            last_login_str = 'Never'

        print(f"{user_id:<6} {username:<20} {full_name:<25} {email:<30} {is_admin:<6} {is_active:<7} {last_login_str:<20}")

    # Summary
    admin_count = sum(1 for u in users if u.get('is_admin', False))
    active_count = sum(1 for u in users if u.get('active', True))

    print()
    print(f"Summary:")
    print(f"  Active users: {active_count}/{len(users)}")
    print(f"  Administrators: {admin_count}")

except json.JSONDecodeError:
    print("Error: Invalid JSON response from API", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
EOF
}

# Show detailed user info
show_user_details() {
    local url="$1"
    local token="$2"
    local username="$3"

    echo_header "=== User Details: $username ==="
    echo

    local response=$(get_user_details "$url" "$token" "$username")

    echo "$response" | python3 << 'EOF'
import sys
import json
from datetime import datetime

try:
    user = json.load(sys.stdin)

    print(f"ID:              {user.get('id', 'N/A')}")
    print(f"Username:        {user.get('login', user.get('username', 'N/A'))}")
    print(f"Full Name:       {user.get('full_name', 'N/A')}")
    print(f"Email:           {user.get('email', 'N/A')}")
    print(f"Avatar URL:      {user.get('avatar_url', 'N/A')}")
    print(f"Language:        {user.get('language', 'N/A')}")
    print(f"Is Admin:        {'Yes' if user.get('is_admin', False) else 'No'}")
    print(f"Active:          {'Yes' if user.get('active', True) else 'No'}")
    print(f"Restricted:      {'Yes' if user.get('restricted', False) else 'No'}")
    print(f"Visibility:      {user.get('visibility', 'N/A')}")
    print(f"Location:        {user.get('location', 'N/A')}")
    print(f"Website:         {user.get('website', 'N/A')}")
    print(f"Description:     {user.get('description', 'N/A')}")

    # Counts
    print(f"\nStatistics:")
    print(f"  Followers:     {user.get('followers_count', 0)}")
    print(f"  Following:     {user.get('following_count', 0)}")
    print(f"  Starred Repos: {user.get('starred_repos_count', 0)}")

    # Timestamps
    created = user.get('created', '')
    if created:
        created_time = datetime.fromisoformat(created.replace('Z', '+00:00'))
        print(f"  Created:       {created_time.strftime('%Y-%m-%d %H:%M:%S')}")

    last_login = user.get('last_login', '')
    if last_login:
        login_time = datetime.fromisoformat(last_login.replace('Z', '+00:00'))
        print(f"  Last Login:    {login_time.strftime('%Y-%m-%d %H:%M:%S')}")

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
    echo "List users in Gitea"
    echo
    echo "Options:"
    echo "  -s, --search QUERY     Search users by username"
    echo "  -d, --detail USERNAME  Show detailed info for a user"
    echo "  -a, --admins           Show only administrators"
    echo "  -h, --help             Show this help message"
    echo
    echo "Examples:"
    echo "  $0                    # List all users"
    echo "  $0 -s john            # Search for users matching 'john'"
    echo "  $0 -d scitex          # Show details for user 'scitex'"
    echo "  $0 -a                 # List only administrators"
    echo
    echo "Note: Listing all users requires admin API token"
}

# Main
main() {
    local search_query=""
    local detail_user=""
    local admins_only=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -s | --search)
                search_query="$2"
                shift 2
                ;;
            -d | --detail)
                detail_user="$2"
                shift 2
                ;;
            -a | --admins)
                admins_only=true
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

    # Detect environment
    ENV=$(detect_environment)

    if [ "$ENV" = "unknown" ]; then
        echo_error "Gitea not running"
        echo_info "Start with: ./deployment/gitea/scripts/start-dev.sh"
        exit 1
    fi

    # Get API config
    get_api_config "$ENV"

    echo_header "=== Gitea Users ($ENV_DISPLAY) ==="
    echo

    # Show detail for specific user
    if [ -n "$detail_user" ]; then
        show_user_details "$GITEA_URL" "$GITEA_TOKEN" "$detail_user"
        exit 0
    fi

    # Search users
    if [ -n "$search_query" ]; then
        echo_info "Searching for: $search_query"
        search_users "$GITEA_URL" "$GITEA_TOKEN" "$search_query" | format_user_list
        exit 0
    fi

    # List all users (requires admin)
    echo_info "Fetching all users..."

    response=$(list_all_users "$GITEA_URL" "$GITEA_TOKEN")

    # Check if we got a valid response
    if echo "$response" | grep -q "error" || [ -z "$response" ] || [ "$response" = "null" ]; then
        echo_warning "Cannot fetch all users (admin access required)"
        echo_info "Using search API instead..."

        # Fallback to search API
        search_users "$GITEA_URL" "$GITEA_TOKEN" "" | format_user_list
    else
        # Filter admins if requested
        if [ "$admins_only" = true ]; then
            echo "$response" | python3 -c "
import sys, json
users = json.load(sys.stdin)
admins = [u for u in users if u.get('is_admin', False)]
print(json.dumps(admins))
" | format_user_list
        else
            echo "$response" | format_user_list
        fi
    fi
}

main "$@" > >(tee -a "$LOG_PATH") 2> >(tee -a "$ERR_PATH" >&2)

echo -e "\nLogs: $LOG_PATH (stdout) | $ERR_PATH (stderr)"

# EOF
