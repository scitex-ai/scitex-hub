#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: 2025-12-07
# File: scripts/maintenance/ensure_executable.sh
# Ensure all scripts have proper executable permissions

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo -e "${CYAN}🔧 Ensuring executable permissions for scripts...${NC}"
echo ""

# Counters
TOTAL=0
FIXED=0

# Function to check and fix permissions
fix_permissions() {
    local pattern="$1"
    local description="$2"

    echo -e "${CYAN}Checking ${description}...${NC}"

    while IFS= read -r -d '' file; do
        TOTAL=$((TOTAL + 1))
        if [[ ! -x "$file" ]]; then
            if chmod +x "$file" 2>/dev/null; then
                FIXED=$((FIXED + 1))
                echo -e "  ${GREEN}+x${NC} ${file#$PROJECT_ROOT/}"
            fi
        fi
    done < <(find "$PROJECT_ROOT" -type f -name "$pattern" \
        ! -path "*/node_modules/*" \
        ! -path "*/.venv/*" \
        ! -path "*/externals/*" \
        ! -path "*/__pycache__/*" \
        ! -path "*/.git/*" \
        ! -path "*/data/*" \
        ! -path "*/.archive/*" \
        ! -path "*/.old/*" \
        -print0 2>/dev/null)
}

# Check shell scripts
fix_permissions "*.sh" "shell scripts (*.sh)"

# Check Python scripts that should be executable (those with shebang)
echo -e "${CYAN}Checking Python scripts with shebang...${NC}"
while IFS= read -r -d '' file; do
    TOTAL=$((TOTAL + 1))
    # Check if file has a shebang
    if head -1 "$file" 2>/dev/null | grep -q "^#!.*python"; then
        if [[ ! -x "$file" ]]; then
            if chmod +x "$file" 2>/dev/null; then
                FIXED=$((FIXED + 1))
                echo -e "  ${GREEN}+x${NC} ${file#$PROJECT_ROOT/}"
            fi
        fi
    fi
done < <(find "$PROJECT_ROOT" -type f -name "*.py" \
    ! -path "*/node_modules/*" \
    ! -path "*/.venv/*" \
    ! -path "*/externals/*" \
    ! -path "*/__pycache__/*" \
    ! -path "*/.git/*" \
    ! -path "*/migrations/*" \
    ! -path "*/data/*" \
    ! -path "*/.archive/*" \
    ! -path "*/.old/*" \
    -print0 2>/dev/null)

# Summary
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    Summary                            ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
echo -e "  Total scripts checked: ${TOTAL}"
if [[ $FIXED -gt 0 ]]; then
    echo -e "  ${YELLOW}Fixed permissions:${NC} ${FIXED}"
else
    echo -e "  ${GREEN}All scripts already executable!${NC}"
fi
echo ""

# EOF
