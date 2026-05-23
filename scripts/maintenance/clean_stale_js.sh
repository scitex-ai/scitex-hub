#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-12-05 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-hub/scripts/maintenance/clean_stale_js.sh
# ----------------------------------------
# Clean stale compiled JavaScript files and obsolete TypeScript build artifacts
# These files are no longer needed with Vite handling TypeScript directly
# ----------------------------------------

set -e

PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "=== Cleaning stale JS files and obsolete TS build artifacts ==="
echo "Project root: $PROJ_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root or with sudo
needs_sudo=false
if [[ $EUID -ne 0 ]]; then
    # Check if any js files/dirs in static are owned by root
    root_files=$(find "$PROJ_ROOT" -path "*/static/*/js" -user root 2>/dev/null | head -1)
    if [[ -n "$root_files" ]]; then
        needs_sudo=true
        echo -e "${YELLOW}Some files are owned by root. Will use sudo...${NC}"
    fi
fi

# Define rm command (with or without sudo)
if $needs_sudo; then
    RM_CMD="sudo rm -rf"
else
    RM_CMD="rm -rf"
fi

# Function to delete files (with sudo if needed)
delete_files() {
    local pattern="$1"
    local desc="$2"

    local count=$(find "$PROJ_ROOT" -path "$pattern" -type f 2>/dev/null | wc -l)
    if [[ $count -gt 0 ]]; then
        echo -e "Deleting $count $desc files..."
        if $needs_sudo; then
            sudo find "$PROJ_ROOT" -path "$pattern" -type f -delete 2>/dev/null || true
        else
            find "$PROJ_ROOT" -path "$pattern" -type f -delete 2>/dev/null || true
        fi
        echo -e "${GREEN}✓ Deleted $count $desc files${NC}"
    else
        echo -e "No $desc files found"
    fi
}

# Delete stale compiled files in apps/*/ts directories
echo ""
echo "--- Cleaning apps/ TypeScript directories ---"
delete_files "*/apps/*/static/*/ts/*.js" ".js"
delete_files "*/apps/*/static/*/ts/*.js.map" ".js.map"
delete_files "*/apps/*/static/*/ts/*.d.ts" ".d.ts"
delete_files "*/apps/*/static/*/ts/*.d.ts.map" ".d.ts.map"

# Delete stale compiled files in static/*/ts directories
echo ""
echo "--- Cleaning static/ TypeScript directories ---"
delete_files "*/static/*/ts/*.js" ".js"
delete_files "*/static/*/ts/*.js.map" ".js.map"
delete_files "*/static/*/ts/*.d.ts" ".d.ts"
delete_files "*/static/*/ts/*.d.ts.map" ".d.ts.map"

# Delete stale compiled files in shared components
echo ""
echo "--- Cleaning shared components ---"
delete_files "*/static/shared/ts/components/*/*.js" ".js"
delete_files "*/static/shared/ts/components/*/*.d.ts" ".d.ts"
delete_files "*/static/shared/ts/components/*/*/*.js" ".js (nested)"
delete_files "*/static/shared/ts/components/*/*/*.d.ts" ".d.ts (nested)"

# Delete ALL js/ directories in static/ (we use Vite, never need compiled JS)
echo ""
echo "--- Cleaning ALL js/ directories in static/ (Vite handles TS directly) ---"

# Find all js/ directories in static/ - we never need them with Vite
while IFS= read -r js_dir; do
    echo "Deleting $js_dir..."
    $RM_CMD "$js_dir"
    echo -e "${GREEN}✓ Deleted $js_dir${NC}"
done < <(find "$PROJ_ROOT" -type d -name "js" -path "*/static/*" 2>/dev/null | grep -v node_modules | grep -v GITIGNORED | grep -v media)

# Delete obsolete build directories (project root level)
echo ""
echo "--- Cleaning obsolete build directories ---"

# Only clean .jsbuild (not .cache - contains Docker data)
if [[ -d "$PROJ_ROOT/.jsbuild" ]]; then
    echo "Deleting .jsbuild..."
    $RM_CMD "$PROJ_ROOT/.jsbuild"
    echo -e "${GREEN}✓ Deleted .jsbuild${NC}"
else
    echo ".jsbuild not found (already clean)"
fi

# Delete .tsbuild directories anywhere in the project
echo ""
echo "--- Cleaning ALL .tsbuild directories (obsolete tsc output) ---"
while IFS= read -r tsbuild_dir; do
    echo "Deleting $tsbuild_dir..."
    sudo rm -rf "$tsbuild_dir"
    echo -e "${GREEN}✓ Deleted $tsbuild_dir${NC}"
done < <(find "$PROJ_ROOT" -type d -name ".tsbuild" 2>/dev/null | grep -v node_modules | grep -v GITIGNORED)

# Delete obsolete tsconfig/ directory (old tsc-based build system, replaced by Vite)
echo ""
echo "--- Cleaning obsolete tsconfig/ directory (old tsc build system) ---"
if [[ -d "$PROJ_ROOT/tsconfig" ]]; then
    echo "Deleting tsconfig/ directory..."
    sudo rm -rf "$PROJ_ROOT/tsconfig"
    echo -e "${GREEN}✓ Deleted tsconfig/ directory${NC}"
else
    echo "tsconfig/ not found (already clean)"
fi

# Delete obsolete TYPESCRIPT_ERRORS.log
echo ""
echo "--- Cleaning obsolete error log ---"
if [[ -f "$PROJ_ROOT/TYPESCRIPT_ERRORS.log" ]]; then
    echo "Deleting TYPESCRIPT_ERRORS.log..."
    rm -f "$PROJ_ROOT/TYPESCRIPT_ERRORS.log"
    echo -e "${GREEN}✓ Deleted TYPESCRIPT_ERRORS.log${NC}"
else
    echo "TYPESCRIPT_ERRORS.log not found (already clean)"
fi

echo ""
echo -e "${GREEN}=== Cleanup complete ===${NC}"
echo ""
echo "Next steps:"
echo "  1. Restart Docker: make env=dev restart"
echo "  2. Vite will transpile TypeScript files directly (no pre-compilation)"
