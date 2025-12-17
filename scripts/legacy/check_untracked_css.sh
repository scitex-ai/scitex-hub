#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: 2025-12-07
# Author: ywatanabe (with Claude Code)
# File: /home/ywatanabe/proj/scitex-cloud/scripts/check_untracked_css.sh
# Description: Check for untracked or unstaged CSS files in the repository

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the repository root
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$REPO_ROOT" ]; then
    echo -e "${RED}Error: Not in a git repository${NC}"
    exit 1
fi

cd "$REPO_ROOT"

echo "=== Checking for untracked/unstaged CSS files ==="
echo ""

# Find untracked CSS files
UNTRACKED_CSS=$(git ls-files --others --exclude-standard "*.css" 2>/dev/null || true)

# Find modified but unstaged CSS files
UNSTAGED_CSS=$(git diff --name-only -- "*.css" 2>/dev/null || true)

# Find staged but uncommitted CSS files
STAGED_CSS=$(git diff --cached --name-only -- "*.css" 2>/dev/null || true)

HAS_ISSUES=0

# Report untracked CSS files
if [ -n "$UNTRACKED_CSS" ]; then
    echo -e "${RED}Untracked CSS files (not added to git):${NC}"
    echo "$UNTRACKED_CSS" | while read -r file; do
        echo "  - $file"
    done
    echo ""
    HAS_ISSUES=1
fi

# Report unstaged CSS files
if [ -n "$UNSTAGED_CSS" ]; then
    echo -e "${YELLOW}Modified but unstaged CSS files:${NC}"
    echo "$UNSTAGED_CSS" | while read -r file; do
        echo "  - $file"
    done
    echo ""
    HAS_ISSUES=1
fi

# Report staged CSS files (informational)
if [ -n "$STAGED_CSS" ]; then
    echo -e "${GREEN}Staged CSS files (ready to commit):${NC}"
    echo "$STAGED_CSS" | while read -r file; do
        echo "  - $file"
    done
    echo ""
fi

# Summary
if [ $HAS_ISSUES -eq 0 ]; then
    echo -e "${GREEN}✓ All CSS files are tracked and staged${NC}"
    exit 0
else
    echo -e "${RED}✗ Found untracked or unstaged CSS files${NC}"
    echo ""
    echo "To add all CSS files:"
    echo "  git add '*.css'"
    echo ""
    echo "To add specific files:"
    echo "  git add <file-path>"
    exit 1
fi
