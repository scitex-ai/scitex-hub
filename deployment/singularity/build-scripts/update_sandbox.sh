#!/bin/bash
# File: ./deployment/singularity/build-scripts/update_sandbox.sh
# ============================================
# Incremental sandbox update: pip install ecosystem packages from local repos
# ============================================
# Fast alternative to full sandbox rebuild during active development.
# Installs latest local code into existing sandbox without rebuilding.
#
# Usage:
#   ./update_sandbox.sh               # Update all packages (no-deps)
#   ./update_sandbox.sh --deps        # Update all packages with deps
#   ./update_sandbox.sh --pkg scitex  # Update specific package
#   ./update_sandbox.sh --help

set -euo pipefail

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

# Override SCRIPT_DIR: common.sh uses BASH_SOURCE[1] which points to
# build-scripts/ when sourced directly. Sandbox lives in the parent dir.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ============================================
# Package name -> directory name mapping
# (only needed when pip package name != repo directory)
# ============================================
declare -A PKG_DIR_MAP=(
    [scitex]="scitex-python"
)

# Fallback directory names (tried if primary not found)
declare -A PKG_DIR_FALLBACK=(
    [scitex]="scitex-code"
)

# ============================================
# Parse arguments
# ============================================
INSTALL_DEPS=false
SPECIFIC_PKG=""

while [[ $# -gt 0 ]]; do
    case "$1" in
    --deps)
        INSTALL_DEPS=true
        shift
        ;;
    --pkg | -p)
        SPECIFIC_PKG="$2"
        shift 2
        ;;
    --help | -h)
        echo "Usage: $(basename "$0") [--deps] [--pkg PACKAGE]"
        echo ""
        echo "Incrementally update packages in the active sandbox."
        echo "Much faster than a full rebuild (~seconds vs ~minutes)."
        echo ""
        echo "Options:"
        echo "  --deps        Install dependencies too (slower, use after adding new deps)"
        echo "  --pkg NAME    Update only this package"
        echo ""
        echo "Packages: $ECOSYSTEM_PKGS scitex-container"
        echo ""
        echo "Environment variables:"
        echo "  SCITEX_PROJ_ROOT   Project root (default: ~/proj)"
        exit 0
        ;;
    *)
        echo -e "${RED}Unknown option: $1${NC}"
        exit 1
        ;;
    esac
done

# ============================================
# Setup
# ============================================
# Only need container detection (not build mode — we use --fakeroot directly)
setup_tmp
detect_container_cmd
FAKEROOT_FLAG="--fakeroot"

SANDBOX_DIR="$SCRIPT_DIR/current-sandbox"
PROJ_ROOT="${SCITEX_PROJ_ROOT:-$HOME/proj}"

if [ ! -d "$SANDBOX_DIR" ] && [ ! -L "$SANDBOX_DIR" ]; then
    echo -e "${RED}Error: No sandbox found at $SANDBOX_DIR${NC}"
    echo -e "Build one first: ./build.sh --sandbox"
    exit 1
fi

# Resolve symlink for display
if [ -L "$SANDBOX_DIR" ]; then
    SANDBOX_REAL=$(readlink "$SANDBOX_DIR")
    echo -e "${CYAN}Sandbox:${NC} ${GREEN}${SANDBOX_REAL}${NC} (via current-sandbox)"
else
    echo -e "${CYAN}Sandbox:${NC} ${GREEN}$SANDBOX_DIR${NC}"
fi

echo -e "${CYAN}Project root:${NC} ${GREEN}$PROJ_ROOT${NC}"

# Ensure bind mount destination exists inside sandbox
# (--writable mode can't auto-create it)
SANDBOX_REAL="$SANDBOX_DIR"
[ -L "$SANDBOX_DIR" ] && SANDBOX_REAL=$(readlink -f "$SANDBOX_DIR")
mkdir -p "${SANDBOX_REAL}${PROJ_ROOT}"

echo ""

# ============================================
# Build package list
# ============================================
if [ -n "$SPECIFIC_PKG" ]; then
    PKGS="$SPECIFIC_PKG"
else
    PKGS="$ECOSYSTEM_PKGS scitex-container scitex-cloud"
fi

# pip flags
PIP_FLAGS=""
if [ "$INSTALL_DEPS" = false ]; then
    PIP_FLAGS="--no-deps"
fi

# ============================================
# Resolve package directory
# ============================================
resolve_pkg_dir() {
    local pkg="$1"
    local dir_name="${PKG_DIR_MAP[$pkg]:-$pkg}"
    local pkg_path="$PROJ_ROOT/$dir_name"

    if [ -d "$pkg_path" ]; then
        echo "$pkg_path"
        return 0
    fi

    # Try fallback
    local fallback="${PKG_DIR_FALLBACK[$pkg]:-}"
    if [ -n "$fallback" ]; then
        local fallback_path="$PROJ_ROOT/$fallback"
        if [ -d "$fallback_path" ]; then
            echo "$fallback_path"
            return 0
        fi
    fi

    return 1
}

# ============================================
# Install packages
# ============================================
SUCCESS=0
FAILED=0
SKIPPED=0
START_TIME=$(date +%s)

for pkg in $PKGS; do
    pkg_path=$(resolve_pkg_dir "$pkg") || true

    if [ -z "$pkg_path" ]; then
        echo -e "  ${YELLOW}SKIP${NC} $pkg (directory not found in $PROJ_ROOT)"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    echo -ne "  ${CYAN}Installing${NC} $pkg from $(basename "$pkg_path")... "

    # shellcheck disable=SC2086  # PIP_FLAGS intentionally unquoted
    if $CONTAINER_CMD exec --writable $FAKEROOT_FLAG \
        --bind "$PROJ_ROOT:$PROJ_ROOT" \
        "$SANDBOX_DIR" \
        pip install $PIP_FLAGS "$pkg_path" >/dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
        SUCCESS=$((SUCCESS + 1))
    else
        echo -e "${RED}FAILED${NC}"
        FAILED=$((FAILED + 1))
    fi
done

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

# ============================================
# Summary
# ============================================
echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}Update Summary  (${ELAPSED}s)${NC}"
echo -e "${CYAN}============================================${NC}"
echo -e "  ${GREEN}Success: $SUCCESS${NC}"
[ "$FAILED" -gt 0 ] && echo -e "  ${RED}Failed:  $FAILED${NC}"
[ "$SKIPPED" -gt 0 ] && echo -e "  ${YELLOW}Skipped: $SKIPPED${NC}"
echo ""

if [ "$FAILED" -gt 0 ]; then
    echo -e "${YELLOW}Tip: Run with --deps if packages have new dependencies${NC}"
    exit 1
fi

# EOF
