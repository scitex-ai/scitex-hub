#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-12-18 20:19:35 (ywatanabe)"
# File: ./scripts/maintenance/check_file_sizes.sh

ORIG_DIR="$(pwd)"
THIS_DIR="$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)"
LOG_PATH="$THIS_DIR/.$(basename $0).log"
echo > "$LOG_PATH"

GIT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"

GRAY='\033[0;90m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo_info() { echo -e "${GRAY}INFO: $1${NC}"; }
echo_success() { echo -e "${GREEN}SUCC: $1${NC}"; }
echo_warning() { echo -e "${YELLOW}WARN: $1${NC}"; }
echo_error() { echo -e "${RED}ERRO: $1${NC}"; }
echo_header() { echo_info "=== $1 ==="; }
# ---------------------------------------

# ============================================
# Check File Sizes - Detect files >300 lines
# ============================================
# Location: /scripts/maintenance/check_file_sizes.sh
#
# Purpose: Warn about files exceeding the 300-line threshold
# See: GITIGNORED/RULES/06_FILE_SIZE_LIMITS.md
#
# Usage:
#   ./scripts/maintenance/check_file_sizes.sh           # Show warnings
#   ./scripts/maintenance/check_file_sizes.sh --quiet   # Exit code only
#   ./scripts/maintenance/check_file_sizes.sh --verbose # Detailed report

# Colors
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration - Powers of 2 thresholds
THRESHOLD_TS=512
THRESHOLD_PY=512
THRESHOLD_CSS=512
THRESHOLD_HTML=1024
MODE="${1:-normal}"

# Count files exceeding threshold
count_large_files() {
    local extension="$1"
    local threshold="$2"
    local exclude_pattern="$3"

    if [ -n "$exclude_pattern" ]; then
        find apps/ static/ templates/ -name "*.$extension" \
            ! -path "*/node_modules/*" \
            ! -path "*/.tsbuild/*" \
            ! -path "*/.old/*" \
            ! -path "*/legacy/*" \
            ! -path "*/.legacy/*" \
            ! -path "*/migrations/*" \
            ! -name "*.d.ts" \
            $exclude_pattern \
            -exec wc -l {} + 2>/dev/null | \
            awk -v threshold=$threshold '$1 > threshold && $2 != "total"' | \
            wc -l
    else
        find apps/ static/ templates/ -name "*.$extension" \
            ! -path "*/node_modules/*" \
            ! -path "*/.tsbuild/*" \
            ! -path "*/.old/*" \
            ! -path "*/legacy/*" \
            ! -path "*/.legacy/*" \
            ! -path "*/migrations/*" \
            ! -name "*.d.ts" \
            -exec wc -l {} + 2>/dev/null | \
            awk -v threshold=$threshold '$1 > threshold && $2 != "total"' | \
            wc -l
    fi
}

# Get worst offender for a file type
get_worst_offender() {
    local extension="$1"

    find apps/ static/ templates/ -name "*.$extension" \
        ! -path "*/node_modules/*" \
        ! -path "*/.tsbuild/*" \
        ! -path "*/.old/*" \
        ! -path "*/legacy/*" \
        ! -path "*/.legacy/*" \
        ! -path "*/migrations/*" \
        ! -name "*.d.ts" \
        -exec wc -l {} + 2>/dev/null | \
        grep -v "total" | \
        sort -rn | \
        head -1
}

# Count files by severity
count_by_severity() {
    local extension="$1"
    local min_lines="$2"

    find apps/ static/ templates/ -name "*.$extension" \
        ! -path "*/node_modules/*" \
        ! -path "*/.tsbuild/*" \
        ! -path "*/.old/*" \
        ! -path "*/legacy/*" \
        ! -path "*/.legacy/*" \
        ! -path "*/migrations/*" \
        ! -name "*.d.ts" \
        -exec wc -l {} + 2>/dev/null | \
        awk -v min=$min_lines '$1 > min && $2 != "total"' | \
        wc -l
}

# Main check
check_files() {
    # Count large files by type
    ts_count=$(count_large_files "ts" $THRESHOLD_TS)
    py_count=$(count_large_files "py" $THRESHOLD_PY)
    css_count=$(count_large_files "css" $THRESHOLD_CSS)
    html_count=$(count_large_files "html" $THRESHOLD_HTML)

    total=$((ts_count + py_count + css_count + html_count))

    if [ "$MODE" = "--quiet" ]; then
        [ $total -eq 0 ] && exit 0 || exit 1
    fi

    # Always show if there are violations
    if [ $total -gt 0 ]; then
        echo ""
        echo -e "${YELLOW}⚠️  File Size Warning: $total files exceed thresholds${NC}"
        echo -e "${CYAN}   Thresholds: TS=${THRESHOLD_TS}, PY=${THRESHOLD_PY}, CSS=${THRESHOLD_CSS}, HTML=${THRESHOLD_HTML}${NC}"
        echo -e "${CYAN}   See: GITIGNORED/RULES/06_FILE_SIZE_LIMITS.md${NC}"
        echo ""

        # Show counts by type
        [ $ts_count -gt 0 ] && {
            worst_ts=$(get_worst_offender "ts")
            ts_lines=$(echo "$worst_ts" | awk '{print $1}')
            ts_file=$(echo "$worst_ts" | awk '{print $2}')
            ts_multiplier=$((ts_lines / THRESHOLD_TS))

            # Count critical files (>2048 lines = 8x threshold for TS)
            ts_critical=$(count_by_severity "ts" 2048)

            echo -e "${YELLOW}   TypeScript: $ts_count files (>${THRESHOLD_TS} lines)${NC}"
            if [ $ts_critical -gt 0 ]; then
                echo -e "${RED}     🔥 $ts_critical CRITICAL (>2048 lines)${NC}"
            fi
            echo -e "${CYAN}     Worst: ${ts_file##*/} (${ts_lines} lines, ${ts_multiplier}x threshold)${NC}"
        }

        [ $py_count -gt 0 ] && {
            worst_py=$(get_worst_offender "py")
            py_lines=$(echo "$worst_py" | awk '{print $1}')
            py_file=$(echo "$worst_py" | awk '{print $2}')
            py_multiplier=$((py_lines / THRESHOLD_PY))

            # Count critical files (>2048 lines = 8x threshold for PY)
            py_critical=$(count_by_severity "py" 2048)

            echo -e "${YELLOW}   Python: $py_count files (>${THRESHOLD_PY} lines)${NC}"
            if [ $py_critical -gt 0 ]; then
                echo -e "${RED}     🔥 $py_critical CRITICAL (>2048 lines)${NC}"
            fi
            echo -e "${CYAN}     Worst: ${py_file##*/} (${py_lines} lines, ${py_multiplier}x threshold)${NC}"
        }

        [ $css_count -gt 0 ] && {
            worst_css=$(get_worst_offender "css")
            css_lines=$(echo "$worst_css" | awk '{print $1}')
            css_file=$(echo "$worst_css" | awk '{print $2}')
            css_multiplier=$((css_lines / THRESHOLD_CSS))
            echo -e "${YELLOW}   CSS: $css_count files (>${THRESHOLD_CSS} lines)${NC}"
            echo -e "${CYAN}     Worst: ${css_file##*/} (${css_lines} lines, ${css_multiplier}x threshold)${NC}"
        }

        [ $html_count -gt 0 ] && {
            worst_html=$(get_worst_offender "html")
            html_lines=$(echo "$worst_html" | awk '{print $1}')
            html_file=$(echo "$worst_html" | awk '{print $2}')
            html_multiplier=$((html_lines / THRESHOLD_HTML))
            echo -e "${YELLOW}   HTML: $html_count files (>${THRESHOLD_HTML} lines)${NC}"
            echo -e "${CYAN}     Worst: ${html_file##*/} (${html_lines} lines, ${html_multiplier}x threshold)${NC}"
        }

        echo ""
        echo -e "${CYAN}💡 To see full list: ./scripts/maintenance/check_file_sizes.sh --verbose${NC}"
        echo ""
    else
        if [ "$MODE" = "--verbose" ]; then
            echo ""
            echo -e "${GREEN}✅ All files within thresholds!${NC}"
            echo ""
        fi
    fi

    # Verbose mode - show all violations
    if [ "$MODE" = "--verbose" ] && [ $total -gt 0 ]; then
        echo -e "${CYAN}=== Detailed Report ===${NC}"
        echo ""

        if [ $ts_count -gt 0 ]; then
            echo -e "${YELLOW}TypeScript files (>$THRESHOLD_TS lines):${NC}"
            find apps/ static/ -name "*.ts" \
                ! -path "*/node_modules/*" \
                ! -path "*/.tsbuild/*" \
                ! -path "*/.old/*" \
                ! -path "*/legacy/*" \
                ! -path "*/.legacy/*" \
                ! -name "*.d.ts" \
                -exec wc -l {} + 2>/dev/null | \
                awk -v threshold=$THRESHOLD_TS '$1 > threshold && $2 != "total"' | \
                sort -rn | \
                head -20 | \
                awk '{printf "  %5d lines: %s\n", $1, $2}'
            echo ""
        fi

        if [ $py_count -gt 0 ]; then
            echo -e "${YELLOW}Python files (>$THRESHOLD_PY lines):${NC}"
            find apps/ -name "*.py" \
                ! -path "*/node_modules/*" \
                ! -path "*/.old/*" \
                ! -path "*/legacy/*" \
                ! -path "*/.legacy/*" \
                ! -path "*/migrations/*" \
                -exec wc -l {} + 2>/dev/null | \
                awk -v threshold=$THRESHOLD_PY '$1 > threshold && $2 != "total"' | \
                sort -rn | \
                head -20 | \
                awk '{printf "  %5d lines: %s\n", $1, $2}'
            echo ""
        fi

        if [ $css_count -gt 0 ]; then
            echo -e "${YELLOW}CSS files (>$THRESHOLD_CSS lines):${NC}"
            find apps/ static/ -name "*.css" \
                ! -path "*/node_modules/*" \
                ! -path "*/.old/*" \
                ! -path "*/legacy/*" \
                ! -path "*/.legacy/*" \
                -exec wc -l {} + 2>/dev/null | \
                awk -v threshold=$THRESHOLD_CSS '$1 > threshold && $2 != "total"' | \
                sort -rn | \
                head -20 | \
                awk '{printf "  %5d lines: %s\n", $1, $2}'
            echo ""
        fi

        if [ $html_count -gt 0 ]; then
            echo -e "${YELLOW}HTML files (>$THRESHOLD_HTML lines):${NC}"
            find apps/ templates/ -name "*.html" \
                ! -path "*/.old/*" \
                ! -path "*/legacy/*" \
                ! -path "*/.legacy/*" \
                -exec wc -l {} + 2>/dev/null | \
                awk -v threshold=$THRESHOLD_HTML '$1 > threshold && $2 != "total"' | \
                sort -rn | \
                head -20 | \
                awk '{printf "  %5d lines: %s\n", $1, $2}'
            echo ""
        fi
    fi

    return 0
}

# Run check
check_files

# EOF