#!/bin/bash
# Cloudflare Cache Purge Script
# Usage: ./cloudflare_cache_purge.sh [all|static|urls "url1 url2 ..."]
#
# Exit status (callers branch on it, so keep it stable):
#   0  purge accepted by Cloudflare
#   1  purge attempted and FAILED (API error, bad zone id, network) -- details on stderr
#   2  not configured for this environment (no zone id / token) -- nothing attempted
#
# Credentials come from the environment, or from the deploy env file:
#   CLOUDFLARE_ENV_FILE  (default: deployment/docker/envs/.env.${SCITEX_ENV:-prod})
# That is the same file compose_env.sh passes to `docker compose --env-file`.
# Until 2026-11-27 this script read deployment/docker/docker_prod/.env, a file
# that does not exist on prod, and rebuild.sh discarded its stderr: every
# "Purging Cloudflare cache" step reported "skipped" and nothing was purged.
#
# The API token is sent through a curl config on stdin, never in argv, so it
# does not show up in `ps` or audit logs.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${CLOUDFLARE_ENV_FILE:-$DOCKER_ROOT/envs/.env.${SCITEX_ENV:-prod}}"
API_BASE="${CLOUDFLARE_API_BASE:-https://api.cloudflare.com/client/v4}"

# Read KEY from the env file without sourcing it; strip CR and one pair of quotes.
read_env_value() {
    local key="$1" line
    line="$(grep -E "^${key}=" "$ENV_FILE" 2>/dev/null | tail -n 1 || true)"
    line="${line#*=}"
    line="${line%$'\r'}"
    if [[ "$line" =~ ^\"(.*)\"$ ]] || [[ "$line" =~ ^\'(.*)\'$ ]]; then
        line="${BASH_REMATCH[1]}"
    fi
    printf '%s' "$line"
}

if [ -f "$ENV_FILE" ]; then
    CLOUDFLARE_ZONE_ID="${CLOUDFLARE_ZONE_ID:-$(read_env_value CLOUDFLARE_ZONE_ID)}"
    CLOUDFLARE_API_TOKEN="${CLOUDFLARE_API_TOKEN:-$(read_env_value CLOUDFLARE_API_TOKEN)}"
    CLOUDFLARE_DOMAIN="${CLOUDFLARE_DOMAIN:-$(read_env_value CLOUDFLARE_DOMAIN)}"
fi

ZONE_ID="${CLOUDFLARE_ZONE_ID:-}"
API_TOKEN="${CLOUDFLARE_API_TOKEN:-}"
DOMAIN="${CLOUDFLARE_DOMAIN:-scitex.ai}"

validate_credentials() {
    if [ -z "$ZONE_ID" ] || [ -z "$API_TOKEN" ]; then
        echo -e "${YELLOW}Cloudflare purge not configured: CLOUDFLARE_ZONE_ID and CLOUDFLARE_API_TOKEN" \
            "must be set in the environment or in ${ENV_FILE}${NC}" >&2
        exit 2
    fi
    # A zone id is 32 lowercase hex characters. Anything else makes the API
    # answer 7003 ("could not route"), which reads like an outage, so refuse it
    # here with a message that names the variable (never its value).
    if [[ ! "$ZONE_ID" =~ ^[0-9a-f]{32}$ ]]; then
        echo -e "${RED}Error: CLOUDFLARE_ZONE_ID is malformed (length ${#ZONE_ID}; want 32 lowercase hex)." \
            "Source: ${ENV_FILE}${NC}" >&2
        exit 1
    fi
}

# POST a purge body; print Cloudflare's error codes/messages on failure.
cf_purge() {
    local body="$1" label="$2" response
    if ! response="$(printf 'header = "Authorization: Bearer %s"\n' "$API_TOKEN" |
        curl -sS --max-time 30 -K - -X POST "${API_BASE}/zones/${ZONE_ID}/purge_cache" \
            -H "Content-Type: application/json" --data "$body" 2>&1)"; then
        echo -e "${RED}❌ Cache purge (${label}) FAILED: request error: ${response}${NC}" >&2
        return 1
    fi
    if printf '%s' "$response" | grep -Eq '"success"[[:space:]]*:[[:space:]]*true'; then
        echo -e "${GREEN}✅ Cache purged (${label})${NC}"
        return 0
    fi
    local errors
    errors="$(printf '%s' "$response" | jq -ce '.errors' 2>/dev/null)" || errors="$response"
    echo -e "${RED}❌ Cache purge (${label}) FAILED; Cloudflare said:${NC}" >&2
    printf '%s\n' "$errors" >&2
    return 1
}

json_files() {
    printf '%s\n' "$@" | jq -R . | jq -cs '{files: .}'
}

purge_all() {
    echo -e "${CYAN}🗑️  Purging ALL Cloudflare cache for ${DOMAIN}...${NC}"
    cf_purge '{"purge_everything":true}' "everything"
}

# Common static files after a deployment.
purge_static() {
    echo -e "${CYAN}🗑️  Purging static file cache...${NC}"
    local urls=(
        "https://${DOMAIN}/static/shared/css/components/cookie-consent.css"
        "https://${DOMAIN}/static/shared/css/base.css"
        "https://${DOMAIN}/static/shared/css/components/navbar.css"
        "https://${DOMAIN}/static/shared/css/components/footer.css"
        "https://${DOMAIN}/static/public_app/css/home.css"
        "https://${DOMAIN}/static/vite/main.js"
    )
    cf_purge "$(json_files "${urls[@]}")" "${#urls[@]} static files"
}

purge_urls() {
    local urls_str="${1:-}"
    if [ -z "$urls_str" ]; then
        echo -e "${RED}Error: No URLs provided${NC}" >&2
        echo "Usage: $0 urls \"https://scitex.ai/file1 https://scitex.ai/file2\"" >&2
        exit 1
    fi
    echo -e "${CYAN}🗑️  Purging specific URLs...${NC}"
    # shellcheck disable=SC2086  # word-split the space-separated URL list on purpose
    cf_purge "$(json_files $urls_str)" "urls"
}

main() {
    local mode="${1:-static}"
    case "$mode" in
        all | static | urls) ;;
        *)
            echo "Usage: $0 [all|static|urls \"url1 url2 ...\"]" >&2
            exit 1
            ;;
    esac
    validate_credentials
    case "$mode" in
        all) purge_all ;;
        static) purge_static ;;
        urls) purge_urls "${2:-}" ;;
    esac
}

main "$@"
