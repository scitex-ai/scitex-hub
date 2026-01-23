#!/bin/bash
# Timestamp: "2025-11-18 11:07:00 (ywatanabe)"
# File: ./tests/sync_tests_with_scripts.sh

ORIG_DIR="$(pwd)"
THIS_DIR="$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)"
LOG_PATH="$THIS_DIR/.$(basename $0).log"
echo > "$LOG_PATH"

GIT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"

GRAY='\033[0;90m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo_info() { echo -e "${GRAY}INFO: $1${NC}"; }
echo_success() { echo -e "${GREEN}SUCC: $1${NC}"; }
echo_warning() { echo -e "${YELLOW}WARN: $1${NC}"; }
echo_error() { echo -e "${RED}ERRO: $1${NC}"; }
echo_header() { echo_info "=== $1 ==="; }

ROOT_DIR="$(realpath $THIS_DIR/..)"

DO_MOVE=false
SRC_DIR="$(realpath "${ROOT_DIR}/scripts")"
TESTS_DIR="$(realpath "${ROOT_DIR}/tests")"

usage() {
    echo "Usage: $0 [options]"
    echo
    echo "Synchronizes test files with script files, maintaining test code structure."
    echo
    echo "Options:"
    echo "  -m, --move         Move stale test files to .old directory instead of just reporting (default: $DO_MOVE)"
    echo "  -s, --source DIR   Specify custom source directory (default: $SRC_DIR)"
    echo "  -t, --tests DIR    Specify custom tests directory (default: $TESTS_DIR)"
    echo "  -h, --help         Display this help message"
    echo
    echo "Example:"
    echo "  $0 --move"
    echo "  $0 --source /path/to/scripts --tests /path/to/tests"
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
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

prepare_tests_structure_as_source() {
    [ ! -d "$SRC_DIR" ] && echo_error "Source directory not found: $SRC_DIR" && exit 1
    construct_blacklist_patterns
    find "$SRC_DIR" -type d "${FIND_EXCLUDES[@]}" | while read -r dir; do
        tests_dir="${dir/$SRC_DIR/$TESTS_DIR}"
        mkdir -p "$tests_dir"
    done
}

extract_test_code() {
    local test_file=$1
    local temp_file=$(mktemp)

    sed -n '/if __name__ == "__main__":/q;p' "$test_file" > "$temp_file"

    if [ -s "$temp_file" ]; then
        sed -i -e :a -e '/^\n*$/{$d;N;ba' -e '}' "$temp_file"
        cat "$temp_file"
    fi
    rm "$temp_file"
}

get_pytest_guard() {
    echo ''
    echo 'if __name__ == "__main__":'
    echo '    import os'
    echo ''
    echo '    import pytest'
    echo ''
    echo '    pytest.main([os.path.abspath(__file__)])'
}

update_test_file() {
    local test_file=$1
    local src_file=$2

    if [ ! -f "$test_file" ]; then
        echo_info "Creating test file: $test_file"
        mkdir -p "$(dirname "$test_file")"

        cat > "$test_file" << EOL
# Add your tests here

$(get_pytest_guard)
EOL
    else
        local temp_file=$(mktemp)
        local test_code=$(extract_test_code "$test_file")

        if [ -n "$test_code" ]; then
            echo "$test_code" > "$temp_file"
            [[ "$(tail -c 1 "$temp_file")" != "" ]] && echo "" >> "$temp_file"
        else
            echo "# Add your tests here" > "$temp_file"
            echo "" >> "$temp_file"
        fi

        get_pytest_guard >> "$temp_file"

        mv "$temp_file" "$test_file"
    fi
}

construct_blacklist_patterns() {
    local EXCLUDE_PATHS=(
        "*/.*"
        "*/.*/*"
        "*/deprecated*"
        "*/archive*"
        "*/backup*"
        "*/tmp*"
        "*/temp*"
        "*_out"
        "*_out/*"
        "*/RUNNING"
        "*/RUNNING/*"
        "*/FINISHED"
        "*/FINISHED/*"
        "*/FINISHED_SUCCESS"
        "*/FINISHED_SUCCESS/*"
        "*/FINISHED_FAILED"
        "*/FINISHED_FAILED/*"
        "*/2025Y*"
        "*/2024Y*"
        "*/__pycache__"
        "*/__pycache__/*"
        "*/template.py"
    )

    FIND_EXCLUDES=()
    PRUNE_ARGS=()
    for path in "${EXCLUDE_PATHS[@]}"; do
        FIND_EXCLUDES+=( -not -path "$path" )
        PRUNE_ARGS+=( -path "$path" -o )
    done
    unset 'PRUNE_ARGS[${#PRUNE_ARGS[@]}-1]'
}

find_files() {
    local search_path=$1
    local type=$2
    local name_pattern=$3

    construct_blacklist_patterns
    find "$search_path" \
        \( "${PRUNE_ARGS[@]}" \) -prune -o -type "$type" -name "$name_pattern" -print
}

move_stale_test_files_to_old() {
    local timestamp="$(date +%Y%m%d_%H%M%S)"

    find "$TESTS_DIR" -name "test_*.py" -not -path "*.old*" | while read -r test_path; do

        [[ "$test_path" =~ ^${TESTS_DIR}/custom ]] && continue

        test_rel_path="${test_path#$TESTS_DIR/}"
        test_rel_dir="$(dirname $test_rel_path)"
        test_filename="$(basename $test_rel_path)"

        src_filename="${test_filename#test_}"
        src_rel_dir="$test_rel_dir"
        src_rel_path="$src_rel_dir/$src_filename"
        src_path="$SRC_DIR/$src_rel_path"

        if [ ! -f "$src_path" ] && [ -f "$test_path" ]; then

            stale_test_path=$test_path
            stale_test_filename="$(basename $stale_test_path)"
            stale_test_path_dir="$(dirname $stale_test_path)"
            old_dir_with_timestamp="$stale_test_path_dir/.old-$timestamp"
            tgt_path="$old_dir_with_timestamp/$stale_test_filename"

            echo_warning "Stale Test: $stale_test_path"
            echo_warning "To remove: $0 -m"

            if [ "$DO_MOVE" = "true" ]; then
                mkdir -p "$old_dir_with_timestamp"
                mv "$stale_test_path" "$tgt_path"
                echo_success "Moved: $stale_test_path -> $tgt_path"
            fi

        fi

    done
}

remove_hidden_test_files_and_dirs() {
    find "$TESTS_DIR" -type f -name ".*" -delete 2>/dev/null
    find "$TESTS_DIR" -type d -name ".*" -not -path "$TESTS_DIR/.old" -not -path "$TESTS_DIR/.old/*" -exec rm -rf {} \; 2>/dev/null
}

cleanup_unnecessary_test_files() {
    find "$TESTS_DIR" -type d -name "*RUNNING*" -exec rm -rf {} \; 2>/dev/null
    find "$TESTS_DIR" -type d -name "*FINISHED*" -exec rm -rf {} \; 2>/dev/null
    find "$TESTS_DIR" -type d -name "*FINISHED_SUCCESS*" -exec rm -rf {} \; 2>/dev/null
    find "$TESTS_DIR" -type d -name "*FINISHED_FAILED*" -exec rm -rf {} \; 2>/dev/null
    find "$TESTS_DIR" -type d -name "*2024Y*" -exec rm -rf {} \; 2>/dev/null
    find "$TESTS_DIR" -type d -name "*2025Y*" -exec rm -rf {} \; 2>/dev/null
    find "$TESTS_DIR" -type d -name "*_out" -exec rm -rf {} \; 2>/dev/null
    find "$TESTS_DIR" -type d -name "*__pycache__*" -exec rm -rf {} \; 2>/dev/null
    find "$TESTS_DIR" -type f -name "*.pyc" -delete 2>/dev/null
}

chmod_python_scripts_as_executable() {
    construct_blacklist_patterns
    find "$SRC_DIR" -type f -name "*.py" "${FIND_EXCLUDES[@]}" -exec chmod +x {} \;
}

main() {
    echo_header "Sync Tests with Source"
    echo_info "SRC_DIR: $SRC_DIR"
    echo_info "TESTS_DIR: $TESTS_DIR"
    echo ""

    remove_hidden_test_files_and_dirs
    prepare_tests_structure_as_source
    chmod_python_scripts_as_executable
    cleanup_unnecessary_test_files

    find_files "$SRC_DIR" f "*.py" | while read -r src_file; do
        rel="${src_file#$SRC_DIR/}"
        rel_dir=$(dirname "$rel")
        src_base=$(basename "$rel")

        tests_dir="$TESTS_DIR/$rel_dir"
        mkdir -p "$tests_dir"

        test_file="$tests_dir/test_$src_base"

        update_test_file "$test_file" "$src_file"
    done

    remove_hidden_test_files_and_dirs
    move_stale_test_files_to_old

    echo ""
    echo_header "Test Directory Structure"
    tree "$TESTS_DIR" 2>&1 | tee -a "$LOG_PATH"

    echo ""
    echo_success "Synchronization complete!"
}

main "$@"
cd $ORIG_DIR

# EOF
