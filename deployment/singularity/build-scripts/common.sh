#!/bin/bash
# File: ./deployment/singularity/build/common.sh
# ============================================
# Shared variables, colors, and preflight checks
# ============================================
# Sourced by build.sh and build/*.sh -- do not run directly.
# shellcheck disable=SC2034  # Variables are used by sourcing scripts

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"

# Ecosystem packages used across build types
ECOSYSTEM_PKGS="scitex figrecipe scitex-writer scitex-dataset crossref-local openalex-local socialia scitex-linter"

# Base version (read from file, default 1)
BASE_VERSION_FILE="$SCRIPT_DIR/base-version"
if [ -f "$BASE_VERSION_FILE" ]; then
    BASE_VERSION=$(tr -d '[:space:]' <"$BASE_VERSION_FILE")
else
    BASE_VERSION="1"
fi

# File paths
BASE_DEF="$SCRIPT_DIR/scitex-base.def"
BASE_SIF="$SCRIPT_DIR/scitex-base-v${BASE_VERSION}.sif"
BASE_HASH_FILE="$SCRIPT_DIR/.def-hash-base"

FINAL_DEF="$SCRIPT_DIR/scitex-final.def"
FINAL_HASH_FILE="$SCRIPT_DIR/.def-hash-final"

VERSIONS_JSON="$SCRIPT_DIR/versions.json"
VERSIONS_FILE="$SCRIPT_DIR/.pypi-versions"

LEGACY_DEF="$SCRIPT_DIR/scitex-hub-shared-v0.1.0.def"
LEGACY_SIF="$SCRIPT_DIR/scitex-hub-shared-v0.1.0.sif"
LEGACY_HASH_FILE="$SCRIPT_DIR/.def-hash-legacy"

# ============================================
# Preflight: detect container command
# ============================================
detect_container_cmd() {
    if command -v apptainer &>/dev/null; then
        CONTAINER_CMD="apptainer"
    elif command -v singularity &>/dev/null; then
        CONTAINER_CMD="singularity"
    else
        echo -e "${RED}Error: Neither apptainer nor singularity is installed${NC}"
        echo -e "Install: sudo apt-get install apptainer"
        exit 1
    fi

    local ver
    ver=$($CONTAINER_CMD --version 2>&1 | head -1)
    echo -e "${CYAN}Container tool:${NC} $CONTAINER_CMD ($ver)"
}

# ============================================
# Preflight: detect fakeroot or root
# ============================================
detect_build_mode() {
    BUILD_MODE=""
    if [ "$EUID" -eq 0 ]; then
        BUILD_MODE="root"
    elif command -v apptainer &>/dev/null && apptainer build --help 2>&1 | grep -q fakeroot; then
        BUILD_MODE="fakeroot"
    else
        echo -e "${RED}Error: Must run as root or have fakeroot support${NC}"
        echo -e "Usage: build.sh [--base] [--force]  (with fakeroot)"
        echo -e "   or: sudo build.sh [--base] [--force]"
        exit 1
    fi

    FAKEROOT_FLAG=""
    [ "$BUILD_MODE" = "fakeroot" ] && FAKEROOT_FLAG="--fakeroot"
}

# ============================================
# Preflight: set tmp dirs
# ============================================
setup_tmp() {
    export APPTAINER_TMPDIR="${APPTAINER_TMPDIR:-/tmp}"
    export SINGULARITY_TMPDIR="${SINGULARITY_TMPDIR:-/tmp}"
}

# ============================================
# Disk space check
# ============================================
check_disk_space() {
    local min_gb="${1:-6}"
    local free_space
    free_space=$(df -BG "$SCRIPT_DIR" | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$free_space" -lt "$min_gb" ]; then
        echo -e "${RED}Warning: Low disk space (${free_space}GB free, recommend ${min_gb}GB+)${NC}"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# ============================================
# Backup existing SIF
# ============================================
backup_sif() {
    local sif_file="$1"
    if [ -f "$sif_file" ]; then
        local backup_file
        backup_file="$sif_file.backup.$(date +%Y%m%d_%H%M%S)"
        echo -e "${YELLOW}Backing up existing image to: $(basename "$backup_file")${NC}"
        cp "$sif_file" "$backup_file"
    fi
}

# ============================================
# Run all preflight checks
# ============================================
run_preflight() {
    setup_tmp
    detect_container_cmd
    detect_build_mode
}

# EOF
