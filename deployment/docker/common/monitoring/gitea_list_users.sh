#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-27 07:05:00 (ywatanabe)"
# File: ./containers/docker/scripts/maintenance/gitea_list_users.sh
#
# Docker-specific Gitea user listing script

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
    print(f"{'ID':<6} {'Username':<20} {'Full Name':<25} {'Email':<30} {'Admin':<6} {'Active':<7}")
    print("-" * 100)

    for user in sorted(users, key=lambda x: x.get('id', 0)):
        user_id = user.get('id', 'N/A')
        username = user.get('login', user.get('username', 'N/A'))[:18]
        full_name = user.get('full_name', '')[:23]
        email = user.get('email', 'N/A')[:28]
        is_admin = "✓" if user.get('is_admin', False) else ""
        is_active = "✓" if user.get('active', True) else "✗"

        print(f"{user_id:<6} {username:<20} {full_name:<25} {email:<30} {is_admin:<6} {is_active:<7}")

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

# Show user details
show_user_details() {
    local username="$1"

    echo_header "User Details: $username"
    echo

    response=$(curl -s -H "Authorization: token $GITEA_TOKEN" \
        "$GITEA_URL/api/v1/users/$username" 2> /dev/null)

    echo -e "$response" | python3 << 'EOF'
import sys
import json
from datetime import datetime

try:
    user = json.load(sys.stdin)

    if 'message' in user:
        print(f"Error: {user['message']}")
        sys.exit(1)

    print(f"ID:              {user.get('id', 'N/A')}")
    print(f"Username:        {user.get('login', user.get('username', 'N/A'))}")
    print(f"Full Name:       {user.get('full_name', 'N/A')}")
    print(f"Email:           {user.get('email', 'N/A')}")
    print(f"Is Admin:        {'Yes' if user.get('is_admin', False) else 'No'}")
    print(f"Active:          {'Yes' if user.get('active', True) else 'No'}")

    # Counts
    print(f"\nStatistics:")
    print(f"  Followers:     {user.get('followers_count', 0)}")
    print(f"  Following:     {user.get('following_count', 0)}")

    # Timestamps
    created = user.get('created', '')
    if created:
        created_time = datetime.fromisoformat(created.replace('Z', '+00:00'))
        print(f"  Created:       {created_time.strftime('%Y-%m-%d %H:%M:%S')}")

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
    echo -e "List users in Gitea (Docker deployment)"
    echo
    echo -e "Options:"
    echo -e "  -s, --search QUERY     Search users by username"
    echo -e "  -d, --detail USERNAME  Show detailed info for a user"
    echo -e "  -a, --admins           Show only administrators"
    echo -e "  -h, --help             Show this help message"
    echo
    echo -e "Examples:"
    echo -e "  $0                    # List all users"
    echo -e "  $0 -s john            # Search for users matching 'john'"
    echo -e "  $0 -d scitex          # Show details for user 'scitex'"
    echo -e "  $0 -a                 # List only administrators"
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

    # Configuration
    GITEA_URL="${SCITEX_CLOUD_GITEA_URL_DEV:-http://127.0.0.1:3000}"
    GITEA_TOKEN="${SCITEX_CLOUD_GITEA_TOKEN_DEV}"

    if [ -z "$GITEA_TOKEN" ]; then
        echo_error "GITEA_TOKEN not set"
        echo_info "Set SCITEX_CLOUD_GITEA_TOKEN_DEV in .env"
        exit 1
    fi

    # Validate token
    test_response=$(curl -s -H "Authorization: token $GITEA_TOKEN" \
        "$GITEA_URL/api/v1/user" 2> /dev/null)

    if ! echo -e "$test_response" | grep -q '"login"'; then
        echo_error "Invalid or expired token"
        echo_info "Check SCITEX_CLOUD_GITEA_TOKEN_DEV in .env"
        exit 1
    fi

    echo_header "Gitea Users (Docker Development)"
    echo

    # Show detail for specific user
    if [ -n "$detail_user" ]; then
        show_user_details "$detail_user"
        exit 0
    fi

    # Fetch users
    if [ -n "$search_query" ]; then
        echo_info "Searching for: $search_query"
        response=$(curl -s -H "Authorization: token $GITEA_TOKEN" \
            "$GITEA_URL/api/v1/users/search?q=$search_query" 2> /dev/null \
            | python3 -c "import sys, json; data = json.load(sys.stdin); print(json.dumps(data.get('data', [])))")
    else
        # Try admin API first
        response=$(curl -s -H "Authorization: token $GITEA_TOKEN" \
            "$GITEA_URL/api/v1/admin/users" 2> /dev/null)

        # Fallback to search if not admin
        if echo -e "$response" | grep -q "error\|message" || [ -z "$response" ]; then
            echo_info "Using search API (admin access not available)"
            response=$(curl -s -H "Authorization: token $GITEA_TOKEN" \
                "$GITEA_URL/api/v1/users/search" 2> /dev/null \
                | python3 -c "import sys, json; data = json.load(sys.stdin); print(json.dumps(data.get('data', [])))")
        fi
    fi

    # Filter admins if requested
    if [ "$admins_only" = true ]; then
        response=$(echo -e "$response" | python3 -c "
import sys, json
users = json.load(sys.stdin)
admins = [u for u in users if u.get('is_admin', False)]
print(json.dumps(admins))
")
    fi

    echo -e "$response" | format_user_list
}

main "$@" 2>&1 | tee -a "$LOG_PATH"

echo
echo -e "${GRAY}Log saved to: $LOG_PATH${NC}"

# EOF
