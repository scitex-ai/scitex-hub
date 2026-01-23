#!/bin/bash
# ==============================================================================
# Setup Vitest Testing Infrastructure
# ==============================================================================
# Location: scripts/testing/setup_vitest.sh
# Purpose: Install and configure vitest for TypeScript testing
# Usage: ./scripts/testing/setup_vitest.sh [--check]
#
# Options:
#   --check    Only check if vitest is installed, don't install
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

# Required packages for vitest
VITEST_PACKAGES=(
    "vitest"
    "@vitest/ui"
    "jsdom"
    "@testing-library/dom"
)

check_npm() {
    if ! command -v npm &> /dev/null; then
        echo -e "${RED}❌ npm not found. Please install Node.js first.${NC}"
        echo -e "${YELLOW}   Install: https://nodejs.org/${NC}"
        exit 1
    fi
}

check_vitest_installed() {
    cd "$PROJECT_ROOT"

    local missing=()
    for pkg in "${VITEST_PACKAGES[@]}"; do
        if ! npm list "$pkg" --depth=0 &> /dev/null; then
            missing+=("$pkg")
        fi
    done

    if [ ${#missing[@]} -eq 0 ]; then
        return 0
    else
        return 1
    fi
}

install_vitest() {
    cd "$PROJECT_ROOT"

    echo -e "${CYAN}Installing vitest and testing dependencies...${NC}"
    npm install -D "${VITEST_PACKAGES[@]}"

    echo -e "${GREEN}✅ Vitest packages installed${NC}"
}

check_vitest_config() {
    if [ -f "$PROJECT_ROOT/vitest.config.ts" ]; then
        return 0
    else
        return 1
    fi
}

create_vitest_config() {
    local config_file="$PROJECT_ROOT/vitest.config.ts"

    if [ -f "$config_file" ]; then
        echo -e "${YELLOW}⚠️  vitest.config.ts already exists, skipping${NC}"
        return 0
    fi

    echo -e "${CYAN}Creating vitest.config.ts...${NC}"

    cat > "$config_file" << 'EOF'
import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    include: ['tests/ts/**/*.test.ts'],
    exclude: ['node_modules', 'GITIGNORED/**'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      reportsDirectory: './coverage/ts',
    },
  },
  resolve: {
    alias: {
      // App aliases for imports
      '@vis_app': path.resolve(__dirname, 'apps/vis_app/static/vis_app/ts'),
      '@code_app': path.resolve(__dirname, 'apps/code_app/static/code_app/ts'),
      '@project_app': path.resolve(__dirname, 'apps/project_app/static/project_app/ts'),
      '@scholar_app': path.resolve(__dirname, 'apps/scholar_app/static/scholar_app/ts'),
      '@writer_app': path.resolve(__dirname, 'apps/writer_app/static/writer_app/ts'),
      '@public_app': path.resolve(__dirname, 'apps/public_app/static/public_app/ts'),
      '@shared': path.resolve(__dirname, 'static/shared/ts'),
    },
  },
});
EOF

    echo -e "${GREEN}✅ vitest.config.ts created${NC}"
}

check_package_json_scripts() {
    cd "$PROJECT_ROOT"
    if grep -q '"test":' package.json 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

update_package_json_scripts() {
    cd "$PROJECT_ROOT"

    if check_package_json_scripts; then
        echo -e "${YELLOW}⚠️  Test scripts already in package.json, skipping${NC}"
        return 0
    fi

    echo -e "${CYAN}Adding test scripts to package.json...${NC}"

    # Use node to safely update package.json
    node -e "
const fs = require('fs');
const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
pkg.scripts = pkg.scripts || {};
pkg.scripts.test = 'vitest';
pkg.scripts['test:run'] = 'vitest run';
pkg.scripts['test:ui'] = 'vitest --ui';
pkg.scripts['test:coverage'] = 'vitest run --coverage';
fs.writeFileSync('package.json', JSON.stringify(pkg, null, 2) + '\n');
"

    echo -e "${GREEN}✅ Test scripts added to package.json${NC}"
}

show_status() {
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║         Vitest Testing Infrastructure Status          ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Check npm
    if command -v npm &> /dev/null; then
        echo -e "  npm:              ${GREEN}✅ $(npm --version)${NC}"
    else
        echo -e "  npm:              ${RED}❌ Not installed${NC}"
    fi

    # Check vitest packages
    if check_vitest_installed; then
        echo -e "  vitest packages:  ${GREEN}✅ Installed${NC}"
    else
        echo -e "  vitest packages:  ${RED}❌ Missing${NC}"
    fi

    # Check config
    if check_vitest_config; then
        echo -e "  vitest.config.ts: ${GREEN}✅ Present${NC}"
    else
        echo -e "  vitest.config.ts: ${RED}❌ Missing${NC}"
    fi

    # Check package.json scripts
    if check_package_json_scripts; then
        echo -e "  package.json:     ${GREEN}✅ Test scripts present${NC}"
    else
        echo -e "  package.json:     ${RED}❌ Test scripts missing${NC}"
    fi

    # Check test files
    local test_count
    test_count=$(find "$PROJECT_ROOT/tests/ts" -name "*.test.ts" 2>/dev/null | wc -l)
    echo -e "  Test files:       ${CYAN}$test_count files in tests/ts/${NC}"

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

    echo -e "${CYAN}Setting up Vitest testing infrastructure...${NC}"
    echo ""

    # Step 1: Check npm
    check_npm

    # Step 2: Install packages if needed
    if ! check_vitest_installed; then
        install_vitest
    else
        echo -e "${GREEN}✅ Vitest packages already installed${NC}"
    fi

    # Step 3: Create config if needed
    create_vitest_config

    # Step 4: Update package.json if needed
    update_package_json_scripts

    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║         Vitest Setup Complete!                        ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}Available commands:${NC}"
    echo -e "  npm run test           # Watch mode"
    echo -e "  npm run test:run       # Single run"
    echo -e "  npm run test:ui        # Visual UI"
    echo -e "  npm run test:coverage  # With coverage"
    echo ""
    echo -e "${CYAN}Makefile commands:${NC}"
    echo -e "  make test-ts           # Run TypeScript tests"
    echo -e "  make test-ts-watch     # Watch mode"
    echo -e "  make test-ts-ui        # Visual UI"
    echo ""
}

main "$@"
