#!/bin/bash
# ==============================================================================
# Setup Pytest Testing Infrastructure
# ==============================================================================
# Location: scripts/testing/setup_pytest.sh
# Purpose: Install pytest, playwright, and configure Python testing
# Usage: ./scripts/testing/setup_pytest.sh [--check]
# ==============================================================================

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Required packages
PYTEST_PACKAGES=(
    "pytest"
    "pytest-playwright"
    "pytest-xdist"           # Parallel execution
    "pytest-cov"             # Coverage
    "pytest-html"            # HTML reports
    "pytest-testmon"         # Skip unchanged tests
    "pytest-timeout"         # Test timeouts
)

check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ python3 not found${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Python: $(python3 --version)${NC}"
}

check_pip() {
    if ! command -v pip3 &> /dev/null; then
        echo -e "${RED}❌ pip3 not found${NC}"
        exit 1
    fi
}

check_packages_installed() {
    local missing=()
    for pkg in "${PYTEST_PACKAGES[@]}"; do
        if ! pip3 show "$pkg" &> /dev/null; then
            missing+=("$pkg")
        fi
    done

    if [ ${#missing[@]} -eq 0 ]; then
        return 0
    else
        echo "${missing[@]}"
        return 1
    fi
}

install_packages() {
    echo -e "${CYAN}Installing pytest packages...${NC}"
    pip3 install "${PYTEST_PACKAGES[@]}"
    echo -e "${GREEN}✅ Pytest packages installed${NC}"
}

check_playwright_browsers() {
    if playwright install --dry-run chromium &> /dev/null 2>&1; then
        # Check if browsers are installed
        if [ -d "$HOME/.cache/ms-playwright" ]; then
            return 0
        fi
    fi
    return 1
}

install_playwright_browsers() {
    echo -e "${CYAN}Installing Playwright browsers...${NC}"
    playwright install chromium
    playwright install-deps chromium 2>/dev/null || true
    echo -e "${GREEN}✅ Playwright browsers installed${NC}"
}

check_scitex_browser() {
    local scitex_path="$HOME/proj/scitex-code/src/scitex/browser"
    if [ -d "$scitex_path" ]; then
        return 0
    fi
    return 1
}

show_status() {
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║         Pytest Testing Infrastructure Status          ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Python
    if command -v python3 &> /dev/null; then
        echo -e "  Python:             ${GREEN}✅ $(python3 --version | cut -d' ' -f2)${NC}"
    else
        echo -e "  Python:             ${RED}❌ Not found${NC}"
    fi

    # Pytest packages
    if check_packages_installed > /dev/null 2>&1; then
        echo -e "  Pytest packages:    ${GREEN}✅ Installed${NC}"
    else
        local missing
        missing=$(check_packages_installed 2>/dev/null || true)
        echo -e "  Pytest packages:    ${RED}❌ Missing: $missing${NC}"
    fi

    # Playwright browsers
    if check_playwright_browsers; then
        echo -e "  Playwright:         ${GREEN}✅ Browsers installed${NC}"
    else
        echo -e "  Playwright:         ${RED}❌ Browsers not installed${NC}"
    fi

    # scitex.browser module
    if check_scitex_browser; then
        echo -e "  scitex.browser:     ${GREEN}✅ Available${NC}"
    else
        echo -e "  scitex.browser:     ${YELLOW}⚠️  Not found (visual effects disabled)${NC}"
    fi

    # pytest.ini
    if [ -f "$PROJECT_ROOT/pytest.ini" ]; then
        echo -e "  pytest.ini:         ${GREEN}✅ Present${NC}"
    else
        echo -e "  pytest.ini:         ${RED}❌ Missing${NC}"
    fi

    # Test counts
    local unit_count e2e_count
    unit_count=$(find "$PROJECT_ROOT/tests/custom/apps" -name "test_*.py" 2>/dev/null | wc -l)
    e2e_count=$(find "$PROJECT_ROOT/tests/e2e" -name "test_*.py" 2>/dev/null | wc -l)
    echo ""
    echo -e "  Unit test files:    ${CYAN}$unit_count${NC}"
    echo -e "  E2E test files:     ${CYAN}$e2e_count${NC}"
    echo ""
}

main() {
    local check_only=false

    for arg in "$@"; do
        case $arg in
            --check)
                check_only=true
                ;;
        esac
    done

    if [ "$check_only" = true ]; then
        show_status
        exit 0
    fi

    echo -e "${CYAN}Setting up Pytest testing infrastructure...${NC}"
    echo ""

    # Step 1: Check Python
    check_python
    check_pip

    # Step 2: Install packages
    if ! check_packages_installed > /dev/null 2>&1; then
        install_packages
    else
        echo -e "${GREEN}✅ Pytest packages already installed${NC}"
    fi

    # Step 3: Install Playwright browsers
    if ! check_playwright_browsers; then
        install_playwright_browsers
    else
        echo -e "${GREEN}✅ Playwright browsers already installed${NC}"
    fi

    # Step 4: Check scitex.browser
    if ! check_scitex_browser; then
        echo -e "${YELLOW}⚠️  scitex.browser not found at ~/proj/scitex-code/src/scitex/browser${NC}"
        echo -e "${YELLOW}   Visual effects for E2E tests will be disabled${NC}"
    fi

    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║         Pytest Setup Complete!                        ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}Available commands:${NC}"
    echo -e "  pytest tests/custom/apps/                 # Unit tests"
    echo -e "  pytest tests/e2e/                  # E2E tests"
    echo -e "  pytest tests/e2e/ --headed         # E2E with visible browser"
    echo -e "  pytest -n 4                        # Parallel execution"
    echo ""
    echo -e "${CYAN}Makefile commands:${NC}"
    echo -e "  make test-unit                     # Run unit tests"
    echo -e "  make test-e2e                      # Run E2E tests"
    echo -e "  make test-e2e-headed               # E2E with browser"
    echo ""
}

main "$@"
