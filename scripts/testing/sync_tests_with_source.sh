#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: 2025-12-18
# File: ./scripts/testing/sync_tests_with_source.sh

# =============================================================================
# Test Synchronization Script for Django Project
# =============================================================================
#
# PURPOSE:
#   Synchronizes test file structure with Django apps structure, ensuring
#   every source file has a corresponding test file with embedded source
#   code for reference.
#
# BEHAVIOR:
#   1. Mirrors apps/ directory structure to tests/apps/
#   2. For each source file (e.g., apps/auth_app/views/login.py):
#      - Creates/updates tests/apps/auth_app/views/test_login.py
#      - Preserves existing test code (before source block)
#      - Updates commented source code block at file end
#   3. Identifies "stale" tests (tests without matching source files)
#   4. With -m flag: moves stale tests to .old-{timestamp}/ directories
#
# EXCLUSIONS:
#   - __init__.py, apps.py, admin.py, urls.py (configuration files)
#   - migrations/ (auto-generated)
#   - static/, templates/ (non-Python assets)
#
# USAGE:
#   ./sync_tests_with_source.sh          # Dry run - report stale & placeholder files
#   ./sync_tests_with_source.sh -m       # Move stale files to .old/
#   ./sync_tests_with_source.sh -j 16    # Use 16 parallel jobs
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
SRC_DIR="$GIT_ROOT/apps"
TESTS_DIR="$GIT_ROOT/tests/apps"

# Use half of available CPU cores by default (minimum 1)
CPU_COUNT=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
PARALLEL_JOBS=$(( CPU_COUNT / 2 > 0 ? CPU_COUNT / 2 : 1 ))

# Files to skip (Django configuration files)
SKIP_FILES=(
    "__init__.py"
    "apps.py"
    "admin.py"
    "urls.py"
    "conftest.py"
)

# Directories to skip
SKIP_DIRS=(
    "migrations"
    "static"
    "templates"
    "management"
    "__pycache__"
    ".old"
    ".dev"
    "node_modules"
)

usage() {
    cat << EOF
Usage: $0 [options]

Synchronizes test files with Django app source files, maintaining test code
while updating source references. Reports stale tests and placeholder-only
tests by default.

Options:
  -m, --move         Move stale test files to .old directory (default: $DO_MOVE)
  -s, --source DIR   Specify custom source directory (default: $SRC_DIR)
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
        -s|--source)
            SRC_DIR="$2"
            shift 2
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
    local filename="$1"
    for skip in "${SKIP_FILES[@]}"; do
        [[ "$filename" == "$skip" ]] && return 0
    done
    return 1
}

########################################
# Test Structure
########################################
prepare_tests_structure() {
    [ ! -d "$SRC_DIR" ] && echo_error "Source directory not found: $SRC_DIR" && exit 1

    # Create tests/apps directory if it doesn't exist
    mkdir -p "$TESTS_DIR"

    # Mirror directory structure (excluding specified directories)
    find "$SRC_DIR" -type d \
        -not -path "*/migrations/*" \
        -not -path "*/migrations" \
        -not -path "*/static/*" \
        -not -path "*/static" \
        -not -path "*/templates/*" \
        -not -path "*/templates" \
        -not -path "*/management/*" \
        -not -path "*/management" \
        -not -path "*/__pycache__/*" \
        -not -path "*/__pycache__" \
        -not -path "*/.old/*" \
        -not -path "*/.old" \
        -not -path "*/.dev/*" \
        -not -path "*/.dev" \
        -not -path "*/node_modules/*" \
        -not -path "*/node_modules" \
        2>/dev/null | while read -r dir; do
        local tests_dir="${dir/$SRC_DIR/$TESTS_DIR}"
        mkdir -p "$tests_dir"
    done
}

########################################
# Source as Comment Block
########################################
get_source_code_block() {
    local src_file=$1
    local rel_path="${src_file#$GIT_ROOT/}"

    cat << EOF

# --------------------------------------------------------------------------------
# Start of Source Code from: $rel_path
# --------------------------------------------------------------------------------
$(sed 's/^/# /' "$src_file")

# --------------------------------------------------------------------------------
# End of Source Code from: $rel_path
# --------------------------------------------------------------------------------
EOF
}

get_pytest_guard() {
    cat << 'EOF'

if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])
EOF
}

get_test_template() {
    local src_file=$1
    local rel_path="${src_file#$GIT_ROOT/}"
    local module_path="${rel_path%.py}"
    module_path="${module_path//\//.}"

    cat << EOF
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for $rel_path"""

import pytest

# from $module_path import ...


class TestPlaceholder:
    """Placeholder test class - replace with actual tests."""

    def test_placeholder(self):
        """Placeholder test - implement actual tests."""
        pytest.skip("Not implemented yet")
EOF
}

########################################
# Extract existing test code
########################################
extract_test_code() {
    local test_file=$1
    local temp_file
    temp_file=$(mktemp)

    if grep -q "# Start of Source Code from:" "$test_file"; then
        # Extract content before the source comment block
        sed -n '/# Start of Source Code from:/q;p' "$test_file" | \
            sed -n '/if __name__ == "__main__":/q;p' > "$temp_file"
    else
        # No source block, copy everything before pytest guard
        sed -n '/if __name__ == "__main__":/q;p' "$test_file" > "$temp_file"
    fi

    # Remove trailing blank lines
    if [ -s "$temp_file" ]; then
        sed -i -e :a -e '/^\n*$/{$d;N;ba' -e '}' "$temp_file" 2>/dev/null || true
        cat "$temp_file"
    fi
    rm -f "$temp_file"
}

########################################
# Process single file (for parallel execution)
########################################
process_single_file() {
    local src_file="$1"
    local SRC_DIR="$2"
    local TESTS_DIR="$3"
    local GIT_ROOT="$4"

    local filename
    filename=$(basename "$src_file")

    # Skip configuration files
    case "$filename" in
        __init__.py|apps.py|admin.py|urls.py|conftest.py)
            return 0
            ;;
    esac

    # Derive paths
    local rel="${src_file#$SRC_DIR/}"
    local rel_dir
    rel_dir=$(dirname "$rel")
    local src_base
    src_base=$(basename "$rel")

    # Build test file path
    local tests_dir="$TESTS_DIR/$rel_dir"
    mkdir -p "$tests_dir"
    local test_file="$tests_dir/test_$src_base"

    # Get relative path for display
    local rel_path="${src_file#$GIT_ROOT/}"
    local module_path="${rel_path%.py}"
    module_path="${module_path//\//.}"

    if [ ! -f "$test_file" ]; then
        # Create new test file
        cat > "$test_file" << TEMPLATE
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for $rel_path"""

import pytest

# from $module_path import ...


class TestPlaceholder:
    """Placeholder test class - replace with actual tests."""

    def test_placeholder(self):
        """Placeholder test - implement actual tests."""
        pytest.skip("Not implemented yet")

if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])
TEMPLATE

        # Add source code block
        {
            echo ""
            echo "# --------------------------------------------------------------------------------"
            echo "# Start of Source Code from: $rel_path"
            echo "# --------------------------------------------------------------------------------"
            sed 's/^/# /' "$src_file"
            echo ""
            echo "# --------------------------------------------------------------------------------"
            echo "# End of Source Code from: $rel_path"
            echo "# --------------------------------------------------------------------------------"
        } >> "$test_file"

    else
        # Update existing test file
        local temp_file
        temp_file=$(mktemp)

        # Extract existing test code
        local test_code=""
        if grep -q "# Start of Source Code from:" "$test_file"; then
            test_code=$(sed -n '/# Start of Source Code from:/q;/if __name__ == "__main__":/q;p' "$test_file")
        else
            test_code=$(sed -n '/if __name__ == "__main__":/q;p' "$test_file")
        fi

        # Write test code or default template
        if [ -n "$test_code" ]; then
            echo "$test_code" > "$temp_file"
            # Ensure newline at end
            [[ "$(tail -c 1 "$temp_file" 2>/dev/null)" != "" ]] && echo "" >> "$temp_file"
        else
            cat > "$temp_file" << TEMPLATE
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for $rel_path"""

import pytest

# from $module_path import ...


class TestPlaceholder:
    """Placeholder test class - replace with actual tests."""

    def test_placeholder(self):
        """Placeholder test - implement actual tests."""
        pytest.skip("Not implemented yet")

TEMPLATE
        fi

        # Add pytest guard
        cat >> "$temp_file" << 'GUARD'

if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])
GUARD

        # Add source code block
        {
            echo ""
            echo "# --------------------------------------------------------------------------------"
            echo "# Start of Source Code from: $rel_path"
            echo "# --------------------------------------------------------------------------------"
            sed 's/^/# /' "$src_file"
            echo ""
            echo "# --------------------------------------------------------------------------------"
            echo "# End of Source Code from: $rel_path"
            echo "# --------------------------------------------------------------------------------"
        } >> "$temp_file"

        mv "$temp_file" "$test_file"
    fi
}
export -f process_single_file

########################################
# Find source files
########################################
find_source_files() {
    local search_path=$1

    find "$search_path" -type f -name "*.py" \
        -not -path "*/migrations/*" \
        -not -path "*/static/*" \
        -not -path "*/templates/*" \
        -not -path "*/management/*" \
        -not -path "*/__pycache__/*" \
        -not -path "*/.old/*" \
        -not -path "*/.dev/*" \
        -not -path "*/node_modules/*" \
        2>/dev/null
}

########################################
# Stale file detection
########################################
move_stale_test_files() {
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local stale_count=0
    local moved_count=0
    local stale_files=()

    # Find all test files
    while IFS= read -r test_path; do
        # Skip files in .old directories
        [[ "$test_path" =~ \.old ]] && continue

        # Derive corresponding source file
        local test_rel_path="${test_path#$TESTS_DIR/}"
        local test_rel_dir
        test_rel_dir=$(dirname "$test_rel_path")
        local test_filename
        test_filename=$(basename "$test_rel_path")

        # Remove test_ prefix to get source filename
        local src_filename="${test_filename#test_}"
        local src_path="$SRC_DIR/$test_rel_dir/$src_filename"

        if [ ! -f "$src_path" ] && [ -f "$test_path" ]; then
            stale_files+=("$test_path")
            ((stale_count++))
        fi
    done < <(find "$TESTS_DIR" -name "test_*.py" -not -path "*.old*" 2>/dev/null)

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

    if grep -q "# Start of Source Code from:" "$test_file" 2>/dev/null; then
        test_content=$(sed -n '/# Start of Source Code from:/q;p' "$test_file")
    else
        test_content=$(cat "$test_file")
    fi

    # Check for actual test functions (excluding placeholder)
    # Look for "def test_" that is NOT "def test_placeholder"
    if echo "$test_content" | grep -E "^\s*def test_" | grep -qv "test_placeholder" 2>/dev/null; then
        return 1  # Has actual tests
    fi

    # Check for test classes (excluding TestPlaceholder)
    if echo "$test_content" | grep -E "^\s*class Test" | grep -qv "TestPlaceholder" 2>/dev/null; then
        return 1  # Has actual test classes
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
    done < <(find "$TESTS_DIR" -name "test_*.py" -not -path "*.old*" 2>/dev/null)

    if [ $placeholder_count -gt 0 ]; then
        echo ""
        echo_header "Placeholder Test Files ($placeholder_count found)"
        echo ""
        for placeholder_path in "${placeholder_files[@]}"; do
            local rel_path="${placeholder_path#$TESTS_DIR/}"
            echo_warning "  [PLACEHOLDER] $rel_path"
        done
        echo ""
        echo_info "These test files have no actual test functions."
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
    find "$TESTS_DIR" -type d -name "__pycache__" -exec rm -rf {} \; 2>/dev/null || true
    find "$TESTS_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
}

########################################
# Main
########################################
main() {
    local start_time
    start_time=$(date +%s)

    echo ""
    echo_header "Django Test Synchronization"
    echo ""
    echo_info "Source:    $SRC_DIR"
    echo_info "Tests:     $TESTS_DIR"
    echo_info "Jobs:      $PARALLEL_JOBS"
    echo ""

    # Prepare directory structure
    echo_info "Preparing test structure..."
    prepare_tests_structure

    # Count source files
    local file_count
    file_count=$(find_source_files "$SRC_DIR" | wc -l)
    echo_info "Found $file_count source files"

    # Process files in parallel
    echo_info "Synchronizing test files (parallel)..."
    find_source_files "$SRC_DIR" | \
        xargs -P "$PARALLEL_JOBS" -I {} bash -c \
        'process_single_file "$@"' _ {} "$SRC_DIR" "$TESTS_DIR" "$GIT_ROOT"
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

    echo_header "Summary"
    echo_success "Completed in ${elapsed}s"
    echo ""

    # Log tree structure
    tree "$TESTS_DIR" -I "__pycache__|*.pyc" >> "$LOG_PATH" 2>&1 || true
}

main "$@"
cd "$ORIG_DIR"

# EOF
