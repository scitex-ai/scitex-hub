#!/bin/bash
# Build Sphinx documentation for all SciTeX Python packages
# Usage: ./build_all_docs.sh [--clean]

set -e

CLEAN="${1:-}"
PROJ_ROOT="$HOME/proj"

# Package name → Sphinx source directory
declare -A PACKAGES=(
    ["scitex-python"]="$PROJ_ROOT/scitex-python/docs/sphinx"
    ["figrecipe"]="$PROJ_ROOT/figrecipe/docs/sphinx"
    ["scitex-writer"]="$PROJ_ROOT/scitex-writer/docs/sphinx"
    ["scitex-io"]="$PROJ_ROOT/scitex-io/docs/sphinx"
    ["scitex-stats"]="$PROJ_ROOT/scitex-stats/docs/sphinx"
    ["scitex-clew"]="$PROJ_ROOT/scitex-clew/docs/sphinx"
    ["scitex-dataset"]="$PROJ_ROOT/scitex-dataset/docs/sphinx"
    ["scitex-linter"]="$PROJ_ROOT/scitex-linter/docs/sphinx"
    ["scitex-container"]="$PROJ_ROOT/scitex-container/docs/sphinx"
)

echo "========================================"
echo "Building SciTeX Python Package Docs"
echo "========================================"

BUILT=0
FAILED=0

for pkg in "${!PACKAGES[@]}"; do
    src="${PACKAGES[$pkg]}"
    build="$src/_build/html"

    if [ ! -f "$src/conf.py" ]; then
        echo "  SKIP  $pkg (no conf.py at $src)"
        ((FAILED++))
        continue
    fi

    if [ "$CLEAN" = "--clean" ] && [ -d "$build" ]; then
        rm -rf "$build"
    fi

    echo -n "  BUILD $pkg ... "
    if sphinx-build -b html -q "$src" "$build" 2>/dev/null; then
        echo "OK"
        ((BUILT++))
    else
        echo "FAIL"
        ((FAILED++))
    fi
done

echo ""
echo "========================================"
echo "Done: $BUILT built, $FAILED skipped/failed"
echo "========================================"
