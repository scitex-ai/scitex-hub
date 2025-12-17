#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-12-01 (ywatanabe)"
# File: ./scripts/ts_maintenance.sh
# Description: TypeScript maintenance - cleanup orphan JS files and rebuild

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
GRAY='\033[0;90m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo_info() { echo -e "${GRAY}INFO: $1${NC}"; }
echo_success() { echo -e "${GREEN}SUCC: $1${NC}"; }
echo_warning() { echo -e "${YELLOW}WARN: $1${NC}"; }
echo_error() { echo -e "${RED}ERRO: $1${NC}"; }
echo_header() { echo -e "${CYAN}=== $1 ===${NC}"; }

# Default values
DRY_RUN=true
CLEANUP_ONLY=false
BUILD_ONLY=false
CLEANUP_LEGACY=false
USE_SUDO=false
VERBOSE=false

show_usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "TypeScript maintenance script - cleanup orphan JS and rebuild"
    echo ""
    echo "Options:"
    echo "  -x, --execute     Actually perform cleanup (default: dry-run)"
    echo "  -c, --cleanup     Cleanup orphan files only (no rebuild)"
    echo "  -b, --build       Build only (no cleanup)"
    echo "  -l, --legacy      Cleanup ALL legacy js/ directories (migrate to .jsbuild)"
    echo "  -s, --sudo        Use sudo for file operations (for Docker-owned files)"
    echo "  -v, --verbose     Verbose output"
    echo "  -h, --help        Show this help"
    echo ""
    echo "Examples:"
    echo "  $0                    # Dry-run: show what would be cleaned"
    echo "  $0 -x                 # Execute cleanup and rebuild"
    echo "  $0 -x -c              # Execute orphan cleanup only"
    echo "  $0 -x -l -s           # Cleanup legacy JS dirs with sudo (one-time migration)"
    echo ""
    echo "What it does:"
    echo "  1. Scans for .js files without corresponding .ts source"
    echo "  2. Removes orphan .js, .js.map, .d.ts, .d.ts.map files"
    echo "  3. Rebuilds TypeScript (unless --cleanup-only)"
    echo ""
    echo "Migration to Docker-only .jsbuild:"
    echo "  Use -l/--legacy to remove all js/ directories from host."
    echo "  After migration, TypeScript output goes to .jsbuild/ (Docker-internal)."
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -x|--execute)
            DRY_RUN=false
            shift
            ;;
        -c|--cleanup)
            CLEANUP_ONLY=true
            shift
            ;;
        -b|--build)
            BUILD_ONLY=true
            shift
            ;;
        -l|--legacy)
            CLEANUP_LEGACY=true
            shift
            ;;
        -s|--sudo)
            USE_SUDO=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# App directories to process (ts source -> js output)
# Format: "ts_dir:js_dir"
# Note: With Docker-only .jsbuild output, these paths are for cleaning up legacy files on host
# New builds go to .jsbuild/ (Docker-internal only)
APP_DIRS=(
    "apps/vis_app/static/vis_app/ts:apps/vis_app/static/vis_app/js"
    "apps/writer_app/static/writer_app/ts:apps/writer_app/static/writer_app/js"
    "apps/code_app/static/code_app/ts:apps/code_app/static/code_app/js"
    "apps/scholar_app/static/scholar_app/ts:apps/scholar_app/static/scholar_app/js"
    "apps/project_app/static/project_app/ts:apps/project_app/static/project_app/js"
    "apps/public_app/static/public_app/ts:apps/public_app/static/public_app/js"
    "static/shared/ts:static/shared/js"
)

# Legacy js directories on host (for cleanup only)
LEGACY_JS_DIRS=(
    "apps/vis_app/static/vis_app/js"
    "apps/writer_app/static/writer_app/js"
    "apps/code_app/static/code_app/js"
    "apps/scholar_app/static/scholar_app/js"
    "apps/project_app/static/project_app/js"
    "apps/public_app/static/public_app/js"
    "static/shared/js"
)

# Remove command (with or without sudo)
remove_file() {
    local file="$1"
    if $USE_SUDO; then
        sudo rm -f "$file"
    else
        rm -f "$file"
    fi
}

remove_dir() {
    local dir="$1"
    if $USE_SUDO; then
        sudo rm -rf "$dir"
    else
        rm -rf "$dir"
    fi
}

# Find orphan JS files (no corresponding TS source)
find_orphans() {
    local ts_dir="$1"
    local js_dir="$2"
    local orphans=()

    # Skip if js_dir doesn't exist
    [[ ! -d "$PROJECT_ROOT/$js_dir" ]] && return

    # Find all .js files in js_dir
    while IFS= read -r js_file; do
        # Get relative path from js_dir
        local rel_path="${js_file#$PROJECT_ROOT/$js_dir/}"

        # Skip if it's a library/vendor file (no ts source expected)
        [[ "$rel_path" == *"node_modules"* ]] && continue
        [[ "$rel_path" == *"vendor"* ]] && continue
        [[ "$rel_path" == *".min.js" ]] && continue

        # Construct expected ts path
        local ts_file="$PROJECT_ROOT/$ts_dir/${rel_path%.js}.ts"

        # Check if ts source exists
        if [[ ! -f "$ts_file" ]]; then
            orphans+=("$js_file")
        fi
    done < <(find "$PROJECT_ROOT/$js_dir" -name "*.js" -type f 2>/dev/null)

    # Print orphans
    for orphan in "${orphans[@]}"; do
        echo "$orphan"
    done
}

# Find orphan directories (no corresponding TS directory)
find_orphan_dirs() {
    local ts_dir="$1"
    local js_dir="$2"
    local orphan_dirs=()

    [[ ! -d "$PROJECT_ROOT/$js_dir" ]] && return

    while IFS= read -r js_subdir; do
        local rel_path="${js_subdir#$PROJECT_ROOT/$js_dir/}"
        local ts_subdir="$PROJECT_ROOT/$ts_dir/$rel_path"

        # Skip special directories
        [[ "$rel_path" == *"node_modules"* ]] && continue
        [[ "$rel_path" == *"vendor"* ]] && continue

        if [[ ! -d "$ts_subdir" ]]; then
            orphan_dirs+=("$js_subdir")
        fi
    done < <(find "$PROJECT_ROOT/$js_dir" -type d -mindepth 1 2>/dev/null | sort -r)

    for dir in "${orphan_dirs[@]}"; do
        echo "$dir"
    done
}

# Cleanup orphan files
cleanup_orphans() {
    echo_header "Cleanup Orphan JS Files"

    local total_orphans=0
    local total_removed=0
    local total_dirs=0

    for app_dir in "${APP_DIRS[@]}"; do
        IFS=':' read -r ts_dir js_dir <<< "$app_dir"

        [[ ! -d "$PROJECT_ROOT/$js_dir" ]] && continue

        echo_info "Checking: $js_dir"

        # Find and process orphan files
        while IFS= read -r orphan; do
            [[ -z "$orphan" ]] && continue
            total_orphans=$((total_orphans + 1))

            # Related files to remove
            local base="${orphan%.js}"
            local files_to_remove=(
                "$orphan"
                "${base}.js.map"
                "${base}.d.ts"
                "${base}.d.ts.map"
            )

            for file in "${files_to_remove[@]}"; do
                if [[ -f "$file" ]]; then
                    if $DRY_RUN; then
                        echo_warning "[DRY-RUN] Would remove: $file"
                    else
                        if $VERBOSE; then
                            echo_info "Removing: $file"
                        fi
                        remove_file "$file"
                        total_removed=$((total_removed + 1))
                    fi
                fi
            done
        done < <(find_orphans "$ts_dir" "$js_dir")

        # Find and process orphan directories
        while IFS= read -r orphan_dir; do
            [[ -z "$orphan_dir" ]] && continue

            if $DRY_RUN; then
                echo_warning "[DRY-RUN] Would remove dir: $orphan_dir"
            else
                if $VERBOSE; then
                    echo_info "Removing dir: $orphan_dir"
                fi
                remove_dir "$orphan_dir"
            fi
        done < <(find_orphan_dirs "$ts_dir" "$js_dir")
    done

    if $DRY_RUN; then
        echo_info "Found $total_orphans orphan JS files (dry-run, nothing removed)"
    else
        echo_success "Removed $total_removed orphan files"
    fi
}

# Cleanup all legacy JS directories (for migrating to Docker-only .jsbuild)
cleanup_legacy_js_dirs() {
    echo_header "Cleanup Legacy JS Directories"
    echo_info "Note: New builds go to .jsbuild/ (Docker-internal only)"

    for js_dir in "${LEGACY_JS_DIRS[@]}"; do
        local full_path="$PROJECT_ROOT/$js_dir"

        if [[ -d "$full_path" ]]; then
            if $DRY_RUN; then
                local count=$(find "$full_path" -type f 2>/dev/null | wc -l)
                echo_warning "[DRY-RUN] Would remove: $js_dir ($count files)"
            else
                echo_info "Removing: $js_dir"
                remove_dir "$full_path"
            fi
        else
            $VERBOSE && echo_info "Skipping (not found): $js_dir"
        fi
    done
}

# Build TypeScript
build_typescript() {
    echo_header "Build TypeScript"

    if $DRY_RUN; then
        echo_warning "[DRY-RUN] Would run: make ENV=dev build-ts"
        return
    fi

    cd "$PROJECT_ROOT"

    echo_info "Running TypeScript compilation..."
    if make ENV=dev build-ts; then
        echo_success "TypeScript build complete"
    else
        echo_error "TypeScript build failed"
        exit 1
    fi
}

# Main
echo_header "TypeScript Maintenance"

if $DRY_RUN; then
    echo_warning "DRY-RUN MODE (use -x to execute)"
fi

if $USE_SUDO; then
    echo_info "Using sudo for file operations"
fi

# Legacy cleanup takes precedence - removes ALL js/ directories
if $CLEANUP_LEGACY; then
    cleanup_legacy_js_dirs
    echo ""
    echo_success "Done! (legacy cleanup)"
    exit 0
fi

if ! $BUILD_ONLY; then
    cleanup_orphans
fi

if ! $CLEANUP_ONLY; then
    build_typescript
fi

echo ""
echo_success "Done!"
