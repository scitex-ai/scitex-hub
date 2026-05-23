#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: 2026-02-13
# Author: ywatanabe (with Claude Code)
# File: /home/ywatanabe/proj/scitex-hub/scripts/maintenance/check_contrast.sh
#
# WCAG AA Contrast Ratio Checker for SciTeX Cloud
#
# Checks text contrast ratios on key pages using Playwright (primary)
# or static CSS analysis (fallback).
#
# Usage:
#   ./scripts/maintenance/check_contrast.sh                # Auto-detect method
#   ./scripts/maintenance/check_contrast.sh --playwright   # Force Playwright
#   ./scripts/maintenance/check_contrast.sh --static       # Force static CSS analysis
#   ./scripts/maintenance/check_contrast.sh --url URL      # Custom base URL
#   ./scripts/maintenance/check_contrast.sh --quiet        # Exit code only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m'

echo_info() { echo -e "${GRAY}INFO: $1${NC}"; }
echo_success() { echo -e "${GREEN}PASS: $1${NC}"; }
echo_warning() { echo -e "${YELLOW}WARN: $1${NC}"; }
echo_error() { echo -e "${RED}FAIL: $1${NC}"; }
echo_header() { echo -e "${CYAN}=== $1 ===${NC}"; }

# Defaults
BASE_URL="http://127.0.0.1:8000"
MODE="auto"
QUIET=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
    --playwright)
        MODE="playwright"
        shift
        ;;
    --static)
        MODE="static"
        shift
        ;;
    --url)
        BASE_URL="$2"
        shift 2
        ;;
    --quiet)
        QUIET=1
        shift
        ;;
    --help | -h)
        echo "Usage: $0 [--playwright|--static] [--url URL] [--quiet]"
        echo ""
        echo "Options:"
        echo "  --playwright  Force Playwright-based checking (requires npx)"
        echo "  --static      Force static CSS analysis (no server needed)"
        echo "  --url URL     Base URL (default: http://127.0.0.1:8000)"
        echo "  --quiet       Exit code only (0=pass, 1=violations found)"
        exit 0
        ;;
    *)
        echo_error "Unknown option: $1"
        exit 1
        ;;
    esac
done

WORKER_JS="$SCRIPT_DIR/_check_contrast_worker.js"
FALLBACK_PY="$SCRIPT_DIR/_check_contrast_static.py"

# ------------------------------------------------------------------
# Method selection
# ------------------------------------------------------------------
run_playwright() {
    echo_header "WCAG AA Contrast Check (Playwright)"
    echo_info "Base URL: $BASE_URL"
    echo ""

    if ! command -v npx &>/dev/null; then
        echo_error "npx not found. Install Node.js or use --static mode."
        return 1
    fi

    # Install playwright if needed (first run)
    if ! npx playwright --version &>/dev/null 2>&1; then
        echo_info "Installing Playwright (first run)..."
        npx playwright install chromium --with-deps 2>/dev/null || {
            echo_warning "Playwright install failed. Falling back to static analysis."
            return 1
        }
    fi

    if [ ! -f "$WORKER_JS" ]; then
        echo_error "Worker script not found: $WORKER_JS"
        return 1
    fi

    node "$WORKER_JS" "$BASE_URL"
    return $?
}

run_static() {
    echo_header "WCAG AA Contrast Check (Static CSS Analysis)"
    echo_info "Analyzing CSS files in: $PROJECT_ROOT"
    echo ""

    if ! command -v python3 &>/dev/null; then
        echo_error "python3 not found."
        return 1
    fi

    if [ ! -f "$FALLBACK_PY" ]; then
        echo_error "Static analysis script not found: $FALLBACK_PY"
        return 1
    fi

    python3 "$FALLBACK_PY" "$PROJECT_ROOT"
    return $?
}

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
EXIT_CODE=0

case "$MODE" in
playwright)
    run_playwright || EXIT_CODE=$?
    ;;
static)
    run_static || EXIT_CODE=$?
    ;;
auto)
    if command -v npx &>/dev/null; then
        # Check if server is reachable
        if curl -s --connect-timeout 2 "$BASE_URL" >/dev/null 2>&1; then
            run_playwright || {
                echo ""
                echo_warning "Playwright failed. Falling back to static analysis."
                echo ""
                run_static || EXIT_CODE=$?
            }
        else
            echo_info "Server not reachable at $BASE_URL. Using static analysis."
            echo ""
            run_static || EXIT_CODE=$?
        fi
    else
        echo_info "npx not available. Using static CSS analysis."
        echo ""
        run_static || EXIT_CODE=$?
    fi
    ;;
esac

if [ $QUIET -eq 1 ]; then
    exit $EXIT_CODE
fi

exit $EXIT_CODE
