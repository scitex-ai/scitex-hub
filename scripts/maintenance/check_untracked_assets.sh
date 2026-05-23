#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: 2025-12-07
# Author: ywatanabe (with Claude Code)
# File: /home/ywatanabe/proj/scitex-hub/scripts/check_untracked_assets.sh
# Description: Check for untracked or unstaged CSS and TypeScript files

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the repository root
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$REPO_ROOT" ]; then
    echo -e "${RED}Error: Not in a git repository${NC}"
    exit 1
fi

cd "$REPO_ROOT"

echo "=== Checking for untracked/unstaged CSS and TypeScript files ==="
echo ""

HAS_ISSUES=0

check_file_type() {
    local extension="$1"
    local label="$2"

    # Find untracked files
    local untracked=$(git ls-files --others --exclude-standard "*.$extension" 2>/dev/null || true)

    # Find modified but unstaged files
    local unstaged=$(git diff --name-only -- "*.$extension" 2>/dev/null || true)

    # Find staged but uncommitted files
    local staged=$(git diff --cached --name-only -- "*.$extension" 2>/dev/null || true)

    local has_type_issues=0

    # Report untracked files
    if [ -n "$untracked" ]; then
        echo -e "${RED}Untracked $label files (not added to git):${NC}"
        echo "$untracked" | while read -r file; do
            [ -n "$file" ] && echo "  - $file"
        done
        echo ""
        has_type_issues=1
    fi

    # Report unstaged files
    if [ -n "$unstaged" ]; then
        echo -e "${YELLOW}Modified but unstaged $label files:${NC}"
        echo "$unstaged" | while read -r file; do
            [ -n "$file" ] && echo "  - $file"
        done
        echo ""
        has_type_issues=1
    fi

    # Report staged files (informational)
    if [ -n "$staged" ]; then
        echo -e "${GREEN}Staged $label files (ready to commit):${NC}"
        echo "$staged" | while read -r file; do
            [ -n "$file" ] && echo "  - $file"
        done
        echo ""
    fi

    return $has_type_issues
}

echo -e "${BLUE}--- CSS Files ---${NC}"
if ! check_file_type "css" "CSS"; then
    HAS_ISSUES=1
fi

echo -e "${BLUE}--- TypeScript Files ---${NC}"
if ! check_file_type "ts" "TypeScript"; then
    HAS_ISSUES=1
fi

echo -e "${BLUE}--- TSX Files ---${NC}"
if ! check_file_type "tsx" "TSX"; then
    HAS_ISSUES=1
fi

# Summary
echo "=== Summary ==="
if [ $HAS_ISSUES -eq 0 ]; then
    echo -e "${GREEN}✓ All CSS and TypeScript files are tracked and staged${NC}"
    exit 0
else
    echo -e "${RED}✗ Found untracked or unstaged files${NC}"
    echo ""
    echo "To add all CSS files:        git add '*.css'"
    echo "To add all TypeScript files: git add '*.ts' '*.tsx'"
    echo "To add all at once:          git add '*.css' '*.ts' '*.tsx'"
    echo ""
    echo "To add specific files:       git add <file-path>"
    exit 1
fi
