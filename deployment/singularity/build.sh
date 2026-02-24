#!/bin/bash
# shellcheck disable=SC1091  # Sourced files use runtime paths; see shellcheck source= hints
# File: ./deployment/singularity/build.sh
# ============================================
# Build SciTeX Apptainer Container (Two-Stage Versioned Build)
# ============================================
# Stage 1 (--base):   scitex-base.def  -> scitex-base-v{N}.sif   (~25 min, rare)
# Stage 2 (default):  scitex-final.def -> scitex-v{VER}.sif      (~3 min, frequent)
# Legacy  (--legacy): monolithic .def  -> .sif                    (migration)
#
# Uses SHA256 hash of .def + versions to skip rebuilds when unchanged.
# Pass --force to rebuild regardless.

# NOTE: Canonical way: scitex container build
# This script remains for Makefile compatibility.

set -e

# ============================================
# Source modular components
# ============================================
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=build-scripts/common.sh
source "$SELF_DIR/build-scripts/common.sh"
# shellcheck source=build-scripts/hash_check.sh
source "$SELF_DIR/build-scripts/hash_check.sh"
# shellcheck source=build-scripts/pypi_versions.sh
source "$SELF_DIR/build-scripts/pypi_versions.sh"
# shellcheck source=build-scripts/versions_json.sh
source "$SELF_DIR/build-scripts/versions_json.sh"
# shellcheck source=build-scripts/build_base.sh
source "$SELF_DIR/build-scripts/build_base.sh"
# shellcheck source=build-scripts/build_final.sh
source "$SELF_DIR/build-scripts/build_final.sh"
# shellcheck source=build-scripts/build_legacy.sh
source "$SELF_DIR/build-scripts/build_legacy.sh"

# ============================================
# Parse arguments
# ============================================
FORCE=false
BUILD_BASE=false
BUILD_LEGACY=false

for arg in "$@"; do
    case "$arg" in
    --force | -f) FORCE=true ;;
    --base) BUILD_BASE=true ;;
    --legacy) BUILD_LEGACY=true ;;
    --help | -h)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  (default)   Build final container from scitex-final.def"
        echo "  --base      Build base container from scitex-base.def"
        echo "  --legacy    Build legacy monolithic container"
        echo "  --force,-f  Force rebuild even if hash unchanged"
        echo "  --help,-h   Show this help"
        exit 0
        ;;
    *)
        echo -e "${RED}Unknown option: $arg${NC}"
        echo "Run $0 --help for usage."
        exit 1
        ;;
    esac
done

# ============================================
# Preflight and dispatch
# ============================================
run_preflight

if [ "$BUILD_LEGACY" = true ]; then
    run_legacy_build "$FORCE"
elif [ "$BUILD_BASE" = true ]; then
    run_base_build "$FORCE"
else
    run_final_build "$FORCE"
fi

# EOF
