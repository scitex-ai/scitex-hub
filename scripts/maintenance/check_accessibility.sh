#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2026-02-13 (ywatanabe)"
# File: scripts/maintenance/check_accessibility.sh
# ----------------------------------------
# Description: WCAG 2.2 AA accessibility check using pa11y-ci + axe-core
#
# Checks all key pages for:
#   - Color contrast ratios (4.5:1 normal, 3:1 large text)
#   - ARIA attributes, roles, labels
#   - Keyboard navigation
#   - All WCAG 2.2 Level AA criteria
#
# Usage:
#   ./scripts/maintenance/check_accessibility.sh           # default: 127.0.0.1:8000
#   ./scripts/maintenance/check_accessibility.sh --url URL  # custom base URL
#   ./scripts/maintenance/check_accessibility.sh --ci       # CI mode (exit code only)
#
# Prerequisites:
#   npx (comes with npm/node)
#   Running Django dev server at the target URL
#
# Exit codes:
#   0 = All pages pass WCAG 2.2 AA
#   1 = Violations found
#   2 = Setup/connectivity error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIG="$PROJECT_ROOT/.pa11yci.json"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

BASE_URL="http://127.0.0.1:8000"
CI_MODE=false

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
    --url)
        BASE_URL="$2"
        shift 2
        ;;
    --ci)
        CI_MODE=true
        shift
        ;;
    -h | --help)
        echo "Usage: $0 [--url BASE_URL] [--ci]"
        echo ""
        echo "Options:"
        echo "  --url URL  Base URL (default: http://127.0.0.1:8000)"
        echo "  --ci       CI mode: suppress colors, exit code only"
        echo ""
        echo "Requires: npx (npm/node), running Django server"
        exit 0
        ;;
    *)
        echo "Unknown option: $1" >&2
        exit 2
        ;;
    esac
done

# Check prerequisites
if ! command -v npx &>/dev/null; then
    echo -e "${RED}Error: npx not found. Install Node.js/npm.${NC}" >&2
    exit 2
fi

# Check server is reachable
if ! curl -s -o /dev/null -w '' --connect-timeout 3 "$BASE_URL" 2>/dev/null; then
    echo -e "${RED}Error: Server not reachable at $BASE_URL${NC}" >&2
    echo -e "${YELLOW}Start with: make ENV=dev start${NC}" >&2
    exit 2
fi

# Check config exists
if [[ ! -f "$CONFIG" ]]; then
    echo -e "${RED}Error: .pa11yci.json not found at $CONFIG${NC}" >&2
    exit 2
fi

# Rewrite URLs if custom base URL
TEMP_CONFIG=""
if [[ "$BASE_URL" != "http://127.0.0.1:8000" ]]; then
    TEMP_CONFIG="$(mktemp /tmp/pa11yci.XXXXXX.json)"
    sed "s|http://127.0.0.1:8000|${BASE_URL}|g" "$CONFIG" >"$TEMP_CONFIG"
    CONFIG="$TEMP_CONFIG"
fi

cleanup() {
    [[ -n "$TEMP_CONFIG" && -f "$TEMP_CONFIG" ]] && rm -f "$TEMP_CONFIG"
}
trap cleanup EXIT

# Run pa11y-ci
echo -e "${CYAN}Running WCAG 2.2 AA accessibility check...${NC}"
echo -e "${CYAN}Target: $BASE_URL${NC}"
echo ""

EXIT_CODE=0
if $CI_MODE; then
    npx --yes pa11y-ci --config "$CONFIG" 2>&1 || EXIT_CODE=$?
else
    npx --yes pa11y-ci --config "$CONFIG" 2>&1 || EXIT_CODE=$?
fi

echo ""
if [[ $EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}All pages pass WCAG 2.2 AA${NC}"
else
    echo -e "${RED}WCAG 2.2 AA violations found (exit code: $EXIT_CODE)${NC}"
    echo -e "${YELLOW}Fix contrast issues in static/shared/css/primitives/colors.css${NC}"
    echo -e "${YELLOW}Use semantic tokens (--text-primary, --text-muted) not legacy (--scitex-color-01)${NC}"
fi

exit $EXIT_CODE

# EOF
