#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: 2025-12-18
# File: ./scripts/testing/sync_ts_tests_with_source.sh

# =============================================================================
# TypeScript Test Synchronization Script for Django Project
# =============================================================================
#
# PURPOSE:
#   Synchronizes TypeScript test file structure with source, ensuring every
#   TypeScript file has a corresponding test file with embedded source code
#   for reference.
#
# BEHAVIOR:
#   1. Mirrors apps/<app>/static/<app>/ts/ → tests/custom/ts/<app>/
#   2. Mirrors static/shared/ts/ → tests/custom/ts/shared/
#   3. For each source file (e.g., apps/code_app/static/code_app/ts/workspace.ts):
#      - Creates/updates tests/custom/ts/code_app/workspace.test.ts
#      - Preserves existing test code (before source block)
#      - Updates commented source code block at file end
#   4. Identifies "stale" tests (tests without matching source files)
#   5. With -m flag: moves stale tests to .old-{timestamp}/ directories
#
# EXCLUSIONS:
#   - index.ts (barrel exports)
#   - *.d.ts (type definitions)
#   - types.ts, types/*.ts (type-only files)
#
# USAGE:
#   ./sync_ts_tests_with_source.sh          # Dry run
#   ./sync_ts_tests_with_source.sh -m       # Move stale files to .old/
#   ./sync_ts_tests_with_source.sh -j 16    # Use 16 parallel jobs
#
# =============================================================================

ORIG_DIR="$(pwd)"
THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GIT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
LOG_PATH="$THIS_DIR/.$(basename "$0").log"
echo "" > "$LOG_PATH"

# Color scheme
GRAY='\033[0;90m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo_info() { echo -e "${GRAY}INFO: $1${NC}"; }
echo_success() { echo -e "${GREEN}SUCC: $1${NC}"; }
echo_warning() { echo -e "${YELLOW}WARN: $1${NC}"; }
echo_error() { echo -e "${RED}ERRO: $1${NC}"; }
echo_header() { echo -e "${BLUE}=== $1 ===${NC}"; }

# Change to project root
cd "$GIT_ROOT"

########################################
# Usage & Argument Parser
########################################
DO_MOVE=false
TESTS_DIR="$GIT_ROOT/tests/custom/ts"

# Use half of available CPU cores by default (minimum 1)
CPU_COUNT=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
PARALLEL_JOBS=$(( CPU_COUNT / 2 > 0 ? CPU_COUNT / 2 : 1 ))

# Files to skip
SKIP_FILES=(
    "index.ts"
    "types.ts"
)

# Patterns to skip
SKIP_PATTERNS=(
    "*.d.ts"
    "*/types/*"
    "*/__tests__/*"
    "*.test.ts"
    "*.spec.ts"
)

usage() {
    cat << EOF
Usage: $0 [options]

Synchronizes TypeScript test files with source files, maintaining test code
while updating source references. Reports stale tests and placeholder-only
tests by default.

Options:
  -m, --move         Move stale test files to .old directory (default: $DO_MOVE)
  -t, --tests DIR    Specify custom tests directory (default: $TESTS_DIR)
  -j, --jobs N       Number of parallel jobs (default: $PARALLEL_JOBS)
  -h, --help         Display this help message

Examples:
  $0                 # Dry run - report stale & placeholder files
  $0 --move          # Move stale files to .old/
  $0 -j 16           # Use 16 parallel jobs
EOF
    exit 1
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--move)
            DO_MOVE=true
            shift
            ;;
        -t|--tests)
            TESTS_DIR="$2"
            shift 2
            ;;
        -j|--jobs)
            PARALLEL_JOBS="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

########################################
# Helper Functions
########################################

# Check if filename should be skipped
should_skip_file() {
    local filepath="$1"
    local filename
    filename=$(basename "$filepath")

    # Skip specific files
    for skip in "${SKIP_FILES[@]}"; do
        [[ "$filename" == "$skip" ]] && return 0
    done

    # Skip patterns
    for pattern in "${SKIP_PATTERNS[@]}"; do
        case "$filepath" in
            $pattern) return 0 ;;
        esac
    done

    # Skip .d.ts files
    [[ "$filename" == *.d.ts ]] && return 0

    # Skip test files
    [[ "$filename" == *.test.ts ]] && return 0
    [[ "$filename" == *.spec.ts ]] && return 0

    return 1
}

########################################
# Source Discovery
########################################
# Find all TypeScript source locations
# Returns: app_name:source_dir pairs
get_ts_source_locations() {
    local locations=()

    # App-specific TypeScript: apps/<app>/static/<app>/ts/
    for app_dir in "$GIT_ROOT"/apps/*_app; do
        if [ -d "$app_dir" ]; then
            local app_name
            app_name=$(basename "$app_dir")
            local ts_dir="$app_dir/static/$app_name/ts"
            if [ -d "$ts_dir" ]; then
                locations+=("$app_name:$ts_dir")
            fi
        fi
    done

    # Shared TypeScript: static/shared/ts/
    if [ -d "$GIT_ROOT/static/shared/ts" ]; then
        locations+=("shared:$GIT_ROOT/static/shared/ts")
    fi

    printf '%s\n' "${locations[@]}"
}

########################################
# Test Structure
########################################
prepare_tests_structure() {
    mkdir -p "$TESTS_DIR"

    # Create directory structure for each source location
    while IFS=: read -r app_name src_dir; do
        [ -z "$app_name" ] && continue

        # Find all directories and mirror them
        find "$src_dir" -type d \
            -not -path "*/__pycache__/*" \
            -not -path "*/.old/*" \
            -not -path "*/node_modules/*" \
            -not -path "*/__tests__/*" \
            2>/dev/null | while read -r dir; do
            local rel_dir="${dir#$src_dir}"
            local test_dir="$TESTS_DIR/$app_name$rel_dir"
            mkdir -p "$test_dir"
        done
    done < <(get_ts_source_locations)
}

########################################
# Find source files
########################################
find_ts_source_files() {
    while IFS=: read -r app_name src_dir; do
        [ -z "$app_name" ] && continue

        find "$src_dir" -type f -name "*.ts" \
            -not -name "*.d.ts" \
            -not -name "*.test.ts" \
            -not -name "*.spec.ts" \
            -not -name "index.ts" \
            -not -name "types.ts" \
            -not -path "*/types/*" \
            -not -path "*/__pycache__/*" \
            -not -path "*/.old/*" \
            -not -path "*/node_modules/*" \
            -not -path "*/__tests__/*" \
            2>/dev/null | while read -r file; do
            echo "$app_name:$src_dir:$file"
        done
    done < <(get_ts_source_locations)
}

########################################
# Process single file (for parallel execution)
########################################
process_single_ts_file() {
    local entry="$1"
    local TESTS_DIR="$2"
    local GIT_ROOT="$3"

    # Parse entry: app_name:src_dir:file_path
    local app_name src_dir src_file
    IFS=: read -r app_name src_dir src_file <<< "$entry"

    [ -z "$src_file" ] && return

    local filename
    filename=$(basename "$src_file")

    # Skip certain files
    [[ "$filename" == "index.ts" ]] && return
    [[ "$filename" == "types.ts" ]] && return
    [[ "$filename" == *.d.ts ]] && return

    # Derive paths
    local rel_path="${src_file#$src_dir/}"
    local rel_dir
    rel_dir=$(dirname "$rel_path")
    local base_name="${filename%.ts}"

    # Build test file path
    local test_dir="$TESTS_DIR/$app_name"
    [ "$rel_dir" != "." ] && test_dir="$test_dir/$rel_dir"
    mkdir -p "$test_dir"
    local test_file="$test_dir/${base_name}.test.ts"

    # Get relative path for display
    local display_path
    if [ "$app_name" = "shared" ]; then
        display_path="static/shared/ts/$rel_path"
    else
        display_path="apps/$app_name/static/$app_name/ts/$rel_path"
    fi

    # Generate import path (relative from test to source)
    local import_path
    if [ "$app_name" = "shared" ]; then
        import_path="@/static/shared/ts/${rel_path%.ts}"
    else
        import_path="@/apps/$app_name/static/$app_name/ts/${rel_path%.ts}"
    fi

    if [ ! -f "$test_file" ]; then
        # Create new test file
        cat > "$test_file" << TEMPLATE
/**
 * Tests for $display_path
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// TODO: Update import path based on your tsconfig paths
// import { } from '$import_path';

describe('$base_name', () => {
    beforeEach(() => {
        // Setup before each test
    });

    afterEach(() => {
        // Cleanup after each test
    });

    it.todo('should be implemented');
});

// =============================================================================
// Source Code Reference (auto-generated, do not edit below this line)
// =============================================================================
// Source: $display_path
// =============================================================================
TEMPLATE

        # Add source code as comments
        {
            echo ""
            sed 's/^/\/\/ /' "$src_file"
            echo ""
            echo "// ============================================================================="
            echo "// End of Source Code"
            echo "// ============================================================================="
        } >> "$test_file"

    else
        # Update existing test file - preserve test code, update source reference
        local temp_file
        temp_file=$(mktemp)

        # Extract existing test code (before source reference block)
        if grep -q "// Source Code Reference" "$test_file" 2>/dev/null; then
            sed -n '/\/\/ =*$/,/Source Code Reference/{ /Source Code Reference/q; }; p' "$test_file" | \
                sed '/^\/\/ =*$/d' > "$temp_file"
        elif grep -q "// Source:" "$test_file" 2>/dev/null; then
            sed -n '/\/\/ Source:/q;p' "$test_file" > "$temp_file"
        else
            cat "$test_file" > "$temp_file"
        fi

        # Remove trailing empty lines
        sed -i -e :a -e '/^\s*$/{ $d; N; ba' -e '}' "$temp_file" 2>/dev/null || true

        # Add source reference block
        {
            echo ""
            echo "// ============================================================================="
            echo "// Source Code Reference (auto-generated, do not edit below this line)"
            echo "// ============================================================================="
            echo "// Source: $display_path"
            echo "// ============================================================================="
            echo ""
            sed 's/^/\/\/ /' "$src_file"
            echo ""
            echo "// ============================================================================="
            echo "// End of Source Code"
            echo "// ============================================================================="
        } >> "$temp_file"

        mv "$temp_file" "$test_file"
    fi
}
export -f process_single_ts_file

########################################
# Stale file detection
########################################
move_stale_test_files() {
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local stale_count=0
    local moved_count=0
    local stale_files=()

    # Build a list of valid source files for lookup
    local valid_sources
    valid_sources=$(mktemp)
    find_ts_source_files | while IFS=: read -r app_name src_dir src_file; do
        local rel_path="${src_file#$src_dir/}"
        local base_name
        base_name=$(basename "${rel_path%.ts}")
        local rel_dir
        rel_dir=$(dirname "$rel_path")
        if [ "$rel_dir" = "." ]; then
            echo "$app_name/$base_name"
        else
            echo "$app_name/$rel_dir/$base_name"
        fi
    done > "$valid_sources"

    # Find all test files
    while IFS= read -r test_path; do
        # Skip files in .old directories
        [[ "$test_path" =~ \.old ]] && continue

        # Derive what source file this test corresponds to
        local test_rel_path="${test_path#$TESTS_DIR/}"
        local test_base
        test_base=$(basename "$test_rel_path" .test.ts)
        local test_dir
        test_dir=$(dirname "$test_rel_path")

        local lookup_key="$test_dir/$test_base"

        if ! grep -qx "$lookup_key" "$valid_sources" 2>/dev/null; then
            stale_files+=("$test_path")
            ((stale_count++))
        fi
    done < <(find "$TESTS_DIR" -name "*.test.ts" -not -path "*.old*" 2>/dev/null)

    rm -f "$valid_sources"

    # Report stale files
    if [ $stale_count -gt 0 ]; then
        echo ""
        echo_header "Stale Test Files ($stale_count found)"
        echo ""
        for stale_path in "${stale_files[@]}"; do
            local rel_path="${stale_path#$TESTS_DIR/}"
            if [ "$DO_MOVE" = "true" ]; then
                local stale_filename
                stale_filename=$(basename "$stale_path")
                local stale_path_dir
                stale_path_dir=$(dirname "$stale_path")
                local old_dir="$stale_path_dir/.old-$timestamp"
                local tgt_path="$old_dir/$stale_filename"

                mkdir -p "$old_dir"
                mv "$stale_path" "$tgt_path"
                echo_success "  [MOVED] $rel_path"
                ((moved_count++))
            else
                echo_warning "  [STALE] $rel_path"
            fi
        done
        echo ""
        if [ "$DO_MOVE" = "false" ]; then
            echo_info "To move stale files, run: $0 -m"
        else
            echo_success "Moved $moved_count stale test files"
        fi
        echo ""
    fi
}

########################################
# Placeholder detection
########################################
is_placeholder_only() {
    local test_file="$1"
    local test_content

    # Extract content before source reference
    if grep -q "// Source Code Reference" "$test_file" 2>/dev/null; then
        test_content=$(sed -n '/\/\/ =*$/,/Source Code Reference/{ /Source Code Reference/q; }; p' "$test_file")
    elif grep -q "// Source:" "$test_file" 2>/dev/null; then
        test_content=$(sed -n '/\/\/ Source:/q;p' "$test_file")
    else
        test_content=$(cat "$test_file")
    fi

    # Check for actual test implementations (not just .todo)
    # Look for it() or test() calls that are NOT .todo
    if echo "$test_content" | grep -E "^\s*(it|test)\s*\(" | grep -qv "\.todo" 2>/dev/null; then
        return 1  # Has actual tests
    fi

    # Check for describe blocks with implementations
    if echo "$test_content" | grep -qE "^\s*describe\s*\(" 2>/dev/null; then
        # Has describe, but check if it has real tests inside
        if echo "$test_content" | grep -E "^\s*(it|test)\s*\(" | grep -qv "\.todo" 2>/dev/null; then
            return 1
        fi
    fi

    return 0  # Is placeholder only
}

report_placeholder_files() {
    local placeholder_count=0
    local placeholder_files=()

    while IFS= read -r test_path; do
        [[ "$test_path" =~ \.old ]] && continue

        if is_placeholder_only "$test_path"; then
            placeholder_files+=("$test_path")
            ((placeholder_count++))
        fi
    done < <(find "$TESTS_DIR" -name "*.test.ts" -not -path "*.old*" 2>/dev/null)

    if [ $placeholder_count -gt 0 ]; then
        echo ""
        echo_header "Placeholder Test Files ($placeholder_count found)"
        echo ""
        for placeholder_path in "${placeholder_files[@]}"; do
            local rel_path="${placeholder_path#$TESTS_DIR/}"
            echo_warning "  [PLACEHOLDER] $rel_path"
        done
        echo ""
        echo_info "These test files only have .todo tests or no actual test implementations."
        echo ""
    else
        echo ""
        echo_success "No placeholder-only test files found"
        echo ""
    fi
}

########################################
# Cleanup
########################################
cleanup_unnecessary_files() {
    find "$TESTS_DIR" -type d -name "node_modules" -exec rm -rf {} \; 2>/dev/null || true
    find "$TESTS_DIR" -type f -name "*.js" -delete 2>/dev/null || true
    find "$TESTS_DIR" -type f -name "*.js.map" -delete 2>/dev/null || true
}

########################################
# Main
########################################
main() {
    local start_time
    start_time=$(date +%s)

    echo ""
    echo_header "TypeScript Test Synchronization"
    echo ""
    echo_info "Tests dir: $TESTS_DIR"
    echo_info "Jobs:      $PARALLEL_JOBS"
    echo ""

    # Show source locations
    echo_info "Source locations:"
    while IFS=: read -r app_name src_dir; do
        [ -z "$app_name" ] && continue
        local file_count
        file_count=$(find "$src_dir" -name "*.ts" -not -name "*.d.ts" -not -name "index.ts" -not -name "*.test.ts" 2>/dev/null | wc -l)
        echo_info "  $app_name: $file_count files"
    done < <(get_ts_source_locations)
    echo ""

    # Prepare directory structure
    echo_info "Preparing test structure..."
    prepare_tests_structure

    # Count and process source files
    local entries
    entries=$(mktemp)
    find_ts_source_files > "$entries"
    local file_count
    file_count=$(wc -l < "$entries")
    echo_info "Found $file_count TypeScript source files"

    # Process files in parallel
    echo_info "Synchronizing test files (parallel)..."
    cat "$entries" | \
        xargs -P "$PARALLEL_JOBS" -I {} bash -c \
        'process_single_ts_file "$@"' _ {} "$TESTS_DIR" "$GIT_ROOT"
    rm -f "$entries"
    echo_success "Processed $file_count source files"

    # Cleanup
    cleanup_unnecessary_files

    # Report stale files
    move_stale_test_files

    # Report placeholders
    report_placeholder_files

    # Summary
    local end_time
    end_time=$(date +%s)
    local elapsed=$((end_time - start_time))

    local test_count
    test_count=$(find "$TESTS_DIR" -name "*.test.ts" -not -path "*.old*" 2>/dev/null | wc -l)

    echo_header "Summary"
    echo_info "Test files: $test_count"
    echo_success "Completed in ${elapsed}s"
    echo ""

    # Log tree structure
    tree "$TESTS_DIR" -I "node_modules" >> "$LOG_PATH" 2>&1 || true
}

main "$@"
cd "$ORIG_DIR"

# EOF
