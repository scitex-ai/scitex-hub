#!/bin/bash
# Cloudflare Cache Purge Script
# Usage: ./cloudflare_cache_purge.sh [all|static|urls "url1 url2 ..."]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Load environment variables (safely, without sourcing)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../../docker_nas/.env"

if [ -f "$ENV_FILE" ]; then
    # Read specific variables without sourcing (avoids issues with special chars)
    CLOUDFLARE_ZONE_ID="${CLOUDFLARE_ZONE_ID:-$(grep '^CLOUDFLARE_ZONE_ID=' "$ENV_FILE" 2>/dev/null | cut -d= -f2-)}"
    CLOUDFLARE_API_TOKEN="${CLOUDFLARE_API_TOKEN:-$(grep '^CLOUDFLARE_API_TOKEN=' "$ENV_FILE" 2>/dev/null | cut -d= -f2-)}"
    CLOUDFLARE_DOMAIN="${CLOUDFLARE_DOMAIN:-$(grep '^CLOUDFLARE_DOMAIN=' "$ENV_FILE" 2>/dev/null | cut -d= -f2-)}"
fi

# Required environment variables
ZONE_ID="${CLOUDFLARE_ZONE_ID:-}"
API_TOKEN="${CLOUDFLARE_API_TOKEN:-}"
DOMAIN="${CLOUDFLARE_DOMAIN:-scitex.ai}"

# Validate credentials
validate_credentials() {
    if [ -z "$ZONE_ID" ] || [ -z "$API_TOKEN" ]; then
        echo -e "${RED}Error: Cloudflare credentials not configured${NC}"
        echo -e "${YELLOW}Required environment variables:${NC}"
        echo "  CLOUDFLARE_ZONE_ID=<your-zone-id>"
        echo "  CLOUDFLARE_API_TOKEN=<your-api-token>"
        echo ""
        echo "Add these to: deployment/docker/docker_nas/.env"
        echo ""
        echo "To get these values:"
        echo "  1. Zone ID: Cloudflare Dashboard → scitex.ai → Overview (right sidebar)"
        echo "  2. API Token: Cloudflare Dashboard → My Profile → API Tokens → Create Token"
        echo "     - Use template: 'Edit zone DNS' or create custom with 'Cache Purge' permission"
        return 1
    fi
    return 0
}

# Purge all cache
purge_all() {
    echo -e "${CYAN}🗑️  Purging ALL Cloudflare cache for ${DOMAIN}...${NC}"

    response=$(curl -s -X POST "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/purge_cache" \
        -H "Authorization: Bearer ${API_TOKEN}" \
        -H "Content-Type: application/json" \
        --data '{"purge_everything":true}')

    if echo "$response" | grep -q '"success":\s*true'; then
        echo -e "${GREEN}✅ All cache purged successfully${NC}"
        return 0
    else
        echo -e "${RED}❌ Cache purge failed:${NC}"
        echo "$response" | jq . 2>/dev/null || echo "$response"
        return 1
    fi
}

# Purge static files (common patterns after deployment)
purge_static() {
    echo -e "${CYAN}🗑️  Purging static file cache...${NC}"

    # Common static file patterns to purge after deployment
    local urls=(
        "https://${DOMAIN}/static/shared/css/components/cookie-consent.css"
        "https://${DOMAIN}/static/shared/css/base.css"
        "https://${DOMAIN}/static/shared/css/components/navbar.css"
        "https://${DOMAIN}/static/shared/css/components/footer.css"
        "https://${DOMAIN}/static/public_app/css/home.css"
        "https://${DOMAIN}/static/vite/main.js"
    )

    # Build JSON array
    local json_files=$(printf '%s\n' "${urls[@]}" | jq -R . | jq -s .)

    response=$(curl -s -X POST "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/purge_cache" \
        -H "Authorization: Bearer ${API_TOKEN}" \
        -H "Content-Type: application/json" \
        --data "{\"files\":${json_files}}")

    if echo "$response" | grep -q '"success":\s*true'; then
        echo -e "${GREEN}✅ Static file cache purged (${#urls[@]} files)${NC}"
        return 0
    else
        echo -e "${RED}❌ Cache purge failed:${NC}"
        echo "$response" | jq . 2>/dev/null || echo "$response"
        return 1
    fi
}

# Purge specific URLs
purge_urls() {
    local urls_str="$1"

    if [ -z "$urls_str" ]; then
        echo -e "${RED}Error: No URLs provided${NC}"
        echo "Usage: $0 urls \"https://scitex.ai/file1 https://scitex.ai/file2\""
        return 1
    fi

    echo -e "${CYAN}🗑️  Purging specific URLs...${NC}"

    # Convert space-separated string to JSON array
    local json_files=$(echo "$urls_str" | tr ' ' '\n' | jq -R . | jq -s .)

    response=$(curl -s -X POST "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/purge_cache" \
        -H "Authorization: Bearer ${API_TOKEN}" \
        -H "Content-Type: application/json" \
        --data "{\"files\":${json_files}}")

    if echo "$response" | grep -q '"success":\s*true'; then
        echo -e "${GREEN}✅ URLs purged successfully${NC}"
        return 0
    else
        echo -e "${RED}❌ Cache purge failed:${NC}"
        echo "$response" | jq . 2>/dev/null || echo "$response"
        return 1
    fi
}

# Main
main() {
    local mode="${1:-static}"

    # Validate credentials first
    if ! validate_credentials; then
        exit 1
    fi

    case "$mode" in
        all)
            purge_all
            ;;
        static)
            purge_static
            ;;
        urls)
            purge_urls "$2"
            ;;
        *)
            echo "Usage: $0 [all|static|urls \"url1 url2 ...\"]"
            echo ""
            echo "Commands:"
            echo "  all     - Purge entire cache (use sparingly)"
            echo "  static  - Purge common static files (default)"
            echo "  urls    - Purge specific URLs"
            exit 1
            ;;
    esac
}

main "$@"
