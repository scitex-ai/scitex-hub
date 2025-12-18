#!/bin/bash
# ==============================================================================
# Run Tests - Unified Test Runner
# ==============================================================================
# Location: scripts/testing/run_tests.sh
# Purpose: Execute tests with proper setup verification and clear feedback
# Usage: ./scripts/testing/run_tests.sh <category> [options]
#
# Categories:
#   unit      - Python unit tests (no DB, no network)
#   db        - Python database tests (Django ORM)
#   api       - Python API endpoint tests
#   ui        - Browser-based UI tests (Playwright)
#   python    - All Python tests (unit + db + api)
#   ts        - TypeScript tests (Vitest)
#   all       - All tests (Python + TypeScript)
#
# Options:
#   --headed  - Run UI tests with visible browser
#   --verbose - Verbose output
#   --check   - Only check if dependencies are installed
# ==============================================================================

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# =============================================================================
# Dependency Checks
# =============================================================================

check_pytest() {
    if ! pip3 show pytest &> /dev/null; then
        echo -e "${RED}❌ Pytest not installed${NC}"
        echo -e "${YELLOW}   Run: make setup-pytest${NC}"
        return 1
    fi
    return 0
}

check_playwright() {
    if ! pip3 show pytest-playwright &> /dev/null; then
        echo -e "${RED}❌ Pytest-playwright not installed${NC}"
        echo -e "${YELLOW}   Run: make setup-pytest${NC}"
        return 1
    fi
    if [ ! -d "$HOME/.cache/ms-playwright" ]; then
        echo -e "${RED}❌ Playwright browsers not installed${NC}"
        echo -e "${YELLOW}   Run: make setup-pytest${NC}"
        return 1
    fi
    return 0
}

check_vitest() {
    cd "$PROJECT_ROOT"
    if ! npm list vitest --depth=0 &> /dev/null; then
        echo -e "${RED}❌ Vitest not installed${NC}"
        echo -e "${YELLOW}   Run: make setup-vitest${NC}"
        return 1
    fi
    return 0
}

# =============================================================================
# Test Runners - Explicit paths, no fallbacks
# =============================================================================

run_unit_tests() {
    local verbose="$1"

    echo -e "${CYAN}🧪 Running Python unit tests...${NC}"
    echo ""

    if ! check_pytest; then
        return 1
    fi

    local pytest_args="-v --tb=short"
    [ "$verbose" = "true" ] && pytest_args="-vv --tb=long"

    cd "$PROJECT_ROOT"

    local test_dir="tests/unit"
    local test_count=$(find "$test_dir" -name "test_*.py" 2>/dev/null | wc -l)

    if [ "$test_count" -eq 0 ]; then
        echo -e "${YELLOW}⚠️  No unit tests found in ${test_dir}/${NC}"
        echo -e "${YELLOW}   Create test files as ${test_dir}/test_*.py${NC}"
        return 0
    fi

    echo -e "${CYAN}   Found ${test_count} test file(s) in ${test_dir}/${NC}"
    pytest "$test_dir/" $pytest_args
}

run_db_tests() {
    local verbose="$1"

    echo -e "${CYAN}🧪 Running Python database tests...${NC}"
    echo ""

    if ! check_pytest; then
        return 1
    fi

    local pytest_args="-v --tb=short"
    [ "$verbose" = "true" ] && pytest_args="-vv --tb=long"

    cd "$PROJECT_ROOT"

    local test_dir="tests/db"
    local test_count=$(find "$test_dir" -name "test_*.py" 2>/dev/null | wc -l)

    if [ "$test_count" -eq 0 ]; then
        echo -e "${YELLOW}⚠️  No database tests found in ${test_dir}/${NC}"
        echo -e "${YELLOW}   Create tests with @pytest.mark.django_db decorator${NC}"
        return 0
    fi

    echo -e "${CYAN}   Found ${test_count} test file(s) in ${test_dir}/${NC}"
    pytest "$test_dir/" $pytest_args
}

run_api_tests() {
    local verbose="$1"

    echo -e "${CYAN}🧪 Running Python API tests...${NC}"
    echo ""

    if ! check_pytest; then
        return 1
    fi

    local pytest_args="-v --tb=short"
    [ "$verbose" = "true" ] && pytest_args="-vv --tb=long"

    cd "$PROJECT_ROOT"

    local test_dir="tests/api"
    local test_count=$(find "$test_dir" -name "test_*.py" 2>/dev/null | wc -l)

    if [ "$test_count" -eq 0 ]; then
        echo -e "${YELLOW}⚠️  No API tests found in ${test_dir}/${NC}"
        return 0
    fi

    echo -e "${CYAN}   Found ${test_count} test file(s) in ${test_dir}/${NC}"
    pytest "$test_dir/" $pytest_args
}

run_ui_tests() {
    local verbose="$1"
    local headed="$2"

    echo -e "${CYAN}🎭 Running UI tests...${NC}"
    echo ""

    if ! check_playwright; then
        return 1
    fi

    local pytest_args="-v --tb=short"
    [ "$verbose" = "true" ] && pytest_args="-vv --tb=long"
    [ "$headed" = "true" ] && pytest_args="$pytest_args --headed"

    cd "$PROJECT_ROOT"

    local test_dir="tests/ui"
    local test_count=$(find "$test_dir" -name "test_*.py" 2>/dev/null | wc -l)

    if [ "$test_count" -eq 0 ]; then
        echo -e "${RED}❌ No UI tests found in ${test_dir}/${NC}"
        echo -e "${YELLOW}   Expected test files at ${test_dir}/test_*.py${NC}"
        return 1
    fi

    echo -e "${CYAN}   Found ${test_count} test file(s) in ${test_dir}/${NC}"
    pytest "$test_dir/" $pytest_args
}

run_python_tests() {
    local verbose="$1"

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║         Running All Python Tests                      ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════╝${NC}"
    echo ""

    local failed=0

    run_unit_tests "$verbose" || failed=1
    echo ""
    run_db_tests "$verbose" || failed=1
    echo ""
    run_api_tests "$verbose" || failed=1

    if [ $failed -eq 0 ]; then
        echo -e "${GREEN}✅ All Python tests passed${NC}"
    else
        echo -e "${RED}❌ Some Python tests failed${NC}"
        return 1
    fi
}

run_ts_tests() {
    local verbose="$1"

    echo -e "${CYAN}🧪 Running TypeScript tests...${NC}"
    echo ""

    if ! check_vitest; then
        return 1
    fi

    cd "$PROJECT_ROOT"

    local test_dir="tests/ts"
    local test_count=$(find "$test_dir" -name "*.test.ts" 2>/dev/null | wc -l)

    if [ "$test_count" -eq 0 ]; then
        echo -e "${YELLOW}⚠️  No TypeScript tests found in ${test_dir}/${NC}"
        return 0
    fi

    echo -e "${CYAN}   Found ${test_count} test file(s) in ${test_dir}/${NC}"
    npm run test:run
}

run_all_tests() {
    local verbose="$1"

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║         Running All Tests (Python + TypeScript)       ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════╝${NC}"
    echo ""

    local failed=0

    run_python_tests "$verbose" || failed=1
    echo ""
    run_ts_tests "$verbose" || failed=1

    if [ $failed -eq 0 ]; then
        echo ""
        echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║         ✅ All Tests Passed!                          ║${NC}"
        echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
    else
        echo ""
        echo -e "${RED}╔═══════════════════════════════════════════════════════╗${NC}"
        echo -e "${RED}║         ❌ Some Tests Failed                          ║${NC}"
        echo -e "${RED}╚═══════════════════════════════════════════════════════╝${NC}"
        return 1
    fi
}

# =============================================================================
# Status Check
# =============================================================================

show_status() {
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║         Test Infrastructure Status                    ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Python testing
    echo -e "${CYAN}Python Testing:${NC}"
    if check_pytest 2>/dev/null; then
        echo -e "  pytest:           ${GREEN}✅ Installed${NC}"
    else
        echo -e "  pytest:           ${RED}❌ Not installed${NC}"
    fi

    if pip3 show pytest-playwright &> /dev/null; then
        echo -e "  pytest-playwright:${GREEN}✅ Installed${NC}"
    else
        echo -e "  pytest-playwright:${RED}❌ Not installed${NC}"
    fi

    if [ -d "$HOME/.cache/ms-playwright" ]; then
        echo -e "  Playwright browsers:${GREEN}✅ Installed${NC}"
    else
        echo -e "  Playwright browsers:${RED}❌ Not installed${NC}"
    fi

    echo ""

    # TypeScript testing
    echo -e "${CYAN}TypeScript Testing:${NC}"
    cd "$PROJECT_ROOT"
    if npm list vitest --depth=0 &> /dev/null; then
        echo -e "  vitest:           ${GREEN}✅ Installed${NC}"
    else
        echo -e "  vitest:           ${RED}❌ Not installed${NC}"
    fi

    echo ""

    # Test counts - explicit paths only
    echo -e "${CYAN}Test Files (explicit paths):${NC}"
    local unit_count=$(find "$PROJECT_ROOT/tests/unit" -name "test_*.py" 2>/dev/null | wc -l)
    local db_count=$(find "$PROJECT_ROOT/tests/db" -name "test_*.py" 2>/dev/null | wc -l)
    local api_count=$(find "$PROJECT_ROOT/tests/api" -name "test_*.py" 2>/dev/null | wc -l)
    local ui_count=$(find "$PROJECT_ROOT/tests/ui" -name "test_*.py" 2>/dev/null | wc -l)
    local ts_count=$(find "$PROJECT_ROOT/tests/ts" -name "*.test.ts" 2>/dev/null | wc -l)

    echo -e "  tests/unit/:      ${CYAN}$unit_count${NC} files"
    echo -e "  tests/db/:        ${CYAN}$db_count${NC} files"
    echo -e "  tests/api/:       ${CYAN}$api_count${NC} files"
    echo -e "  tests/ui/:        ${CYAN}$ui_count${NC} files"
    echo -e "  tests/ts/:        ${CYAN}$ts_count${NC} files"

    # Legacy locations warning
    local apps_count=$(find "$PROJECT_ROOT/tests/apps" -name "test_*.py" 2>/dev/null | wc -l)
    if [ "$apps_count" -gt 0 ]; then
        echo ""
        echo -e "${YELLOW}⚠️  Legacy tests found:${NC}"
        echo -e "  tests/apps/:      ${YELLOW}$apps_count${NC} files (not run by default)"
        echo -e "  ${YELLOW}Consider migrating to tests/{unit,db,api,ui}/${NC}"
    fi

    echo ""
    echo -e "${CYAN}Setup Commands:${NC}"
    echo "  make setup-testing    # Install all dependencies"
    echo "  make setup-pytest     # Python testing only"
    echo "  make setup-vitest     # TypeScript testing only"
    echo ""
}

# =============================================================================
# Main
# =============================================================================

usage() {
    echo "Usage: $0 <category> [options]"
    echo ""
    echo "Categories:"
    echo "  unit      Run Python unit tests (tests/unit/)"
    echo "  db        Run Python database tests (tests/db/)"
    echo "  api       Run Python API tests (tests/api/)"
    echo "  ui        Run UI tests - Playwright (tests/ui/)"
    echo "  python    Run all Python tests"
    echo "  ts        Run TypeScript tests (tests/ts/)"
    echo "  all       Run all tests"
    echo ""
    echo "Options:"
    echo "  --headed  Run UI tests with visible browser"
    echo "  --verbose Verbose output"
    echo "  --check   Show status only"
    echo ""
}

main() {
    local category=""
    local verbose="false"
    local headed="false"
    local check_only="false"

    # Parse all arguments
    for arg in "$@"; do
        case $arg in
            --verbose|-v)
                verbose="true"
                ;;
            --headed)
                headed="true"
                ;;
            --check|status)
                check_only="true"
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            -*)
                echo -e "${RED}❌ Unknown option: $arg${NC}"
                usage
                exit 1
                ;;
            *)
                # First non-option argument is the category
                if [ -z "$category" ]; then
                    category="$arg"
                fi
                ;;
        esac
    done

    # Check only mode
    if [ "$check_only" = "true" ]; then
        show_status
        exit 0
    fi

    # Run tests
    case "$category" in
        unit)
            run_unit_tests "$verbose"
            ;;
        db)
            run_db_tests "$verbose"
            ;;
        api)
            run_api_tests "$verbose"
            ;;
        ui)
            run_ui_tests "$verbose" "$headed"
            ;;
        python)
            run_python_tests "$verbose"
            ;;
        ts|typescript)
            run_ts_tests "$verbose"
            ;;
        all)
            run_all_tests "$verbose"
            ;;
        "")
            echo -e "${RED}❌ No test category specified${NC}"
            echo ""
            usage
            exit 1
            ;;
        *)
            echo -e "${RED}❌ Unknown category: $category${NC}"
            echo ""
            usage
            exit 1
            ;;
    esac
}

main "$@"
